from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from .choices import (
    EXPERIENCE_1_2, EXPERIENCE_3_5, EXPERIENCE_FRESHER, EXPERIENCE_GENERAL,
    EXPERIENCE_OVER_5, EXPERIENCE_UNDER_1, LEVEL_BEGINNER, LEVEL_EXPERIENCED,
)
from .models import (
    CareerRole, DayAttempt, DayProgress, LearningDay, MilestoneExam,
    ScenarioQuestion, Skill,
)
from .selection import (
    effective_learning_path, questions_for_day, recommend_learning_path, resolve_learning_plan,
)


User = get_user_model()


class CareerLearningSelectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.role = CareerRole.objects.create(title='Python Developer', summary='Build Python software.', is_published=True)
        cls.other_role = CareerRole.objects.create(title='Data Analyst', summary='Analyze data.', is_published=True)
        cls.skill = Skill.objects.create(name='Selection tests')

        cls.general_day1 = LearningDay.objects.create(
            role=cls.role, day_number=1, level=LEVEL_BEGINNER,
            experience_band=EXPERIENCE_GENERAL, title='General fundamentals', is_published=True)
        cls.exact_day1 = LearningDay.objects.create(
            role=cls.role, day_number=1, level=LEVEL_BEGINNER,
            experience_band=EXPERIENCE_3_5, title='Production Python', is_published=True)
        cls.general_day2 = LearningDay.objects.create(
            role=cls.role, day_number=2, level=LEVEL_BEGINNER,
            experience_band=EXPERIENCE_GENERAL, title='General APIs', is_published=True)
        cls.exact_day3 = LearningDay.objects.create(
            role=cls.role, day_number=3, level=LEVEL_BEGINNER,
            experience_band=EXPERIENCE_3_5, title='Architecture decisions', is_published=True)
        cls.experienced_day1 = LearningDay.objects.create(
            role=cls.role, day_number=1, level=LEVEL_EXPERIENCED,
            experience_band=EXPERIENCE_3_5, title='Experienced Python', is_published=True)
        cls.other_role_day = LearningDay.objects.create(
            role=cls.other_role, day_number=1, level=LEVEL_BEGINNER,
            experience_band=EXPERIENCE_3_5, title='Data analysis', is_published=True)
        ScenarioQuestion.objects.create(day=cls.general_day1, text='General Python question')
        ScenarioQuestion.objects.create(day=cls.exact_day1, text='Production Python question')
        ScenarioQuestion.objects.create(day=cls.other_role_day, text='Data analyst question')
        cls.wrong_band_day = LearningDay.objects.create(
            role=cls.role, day_number=4, level=LEVEL_BEGINNER,
            experience_band=EXPERIENCE_1_2, title='Intermediate architecture', is_published=True)

        cls.general_milestone = MilestoneExam.objects.create(
            role=cls.role, number=1, level=LEVEL_BEGINNER, experience_band=EXPERIENCE_GENERAL,
            start_day=1, end_day=2, is_published=True)
        cls.exact_milestone = MilestoneExam.objects.create(
            role=cls.role, number=1, level=LEVEL_BEGINNER, experience_band=EXPERIENCE_3_5,
            start_day=1, end_day=3, is_published=True)

    def test_experience_recommendations_and_explicit_path_override(self):
        expected = {
            EXPERIENCE_FRESHER: LEVEL_BEGINNER,
            EXPERIENCE_UNDER_1: LEVEL_BEGINNER,
            EXPERIENCE_1_2: LEVEL_EXPERIENCED,
            EXPERIENCE_3_5: LEVEL_EXPERIENCED,
            EXPERIENCE_OVER_5: LEVEL_EXPERIENCED,
        }
        for band, path in expected.items():
            with self.subTest(band=band):
                self.assertEqual(recommend_learning_path(band), path)
        self.assertEqual(effective_learning_path(EXPERIENCE_3_5, LEVEL_BEGINNER), LEVEL_BEGINNER)

    def test_exact_band_days_precede_general_without_duplicate_sequence_numbers(self):
        plan = resolve_learning_plan(self.role, EXPERIENCE_3_5, LEVEL_BEGINNER)
        self.assertEqual(
            [(day.day_number, day.title) for day in plan.days],
            [(1, 'Production Python'), (2, 'General APIs'), (3, 'Architecture decisions')],
        )
        self.assertEqual(len({day.day_number for day in plan.days}), len(plan.days))
        self.assertEqual([q.text for q in questions_for_day(plan.days[0])], ['Production Python question'])

    def test_general_only_fallback_is_same_role_and_same_path(self):
        plan = resolve_learning_plan(self.role, EXPERIENCE_OVER_5, LEVEL_BEGINNER)
        self.assertEqual([day.title for day in plan.days], ['General fundamentals', 'General APIs'])
        self.assertNotIn(self.other_role_day, plan.days)
        self.assertNotIn(self.experienced_day1, plan.days)
        self.assertEqual([q.text for q in questions_for_day(plan.days[0])], ['General Python question'])

    def test_existing_day_records_default_to_general_content(self):
        day = LearningDay.objects.create(
            role=self.role, level=LEVEL_EXPERIENCED, day_number=8, title='Legacy-shaped day')
        self.assertEqual(day.experience_band, EXPERIENCE_GENERAL)

    def test_learning_path_and_experience_target_are_independent(self):
        plan = resolve_learning_plan(self.role, EXPERIENCE_3_5, LEVEL_EXPERIENCED)
        self.assertEqual([day.title for day in plan.days], ['Experienced Python'])
        self.assertEqual(plan.recommended_path, LEVEL_EXPERIENCED)
        self.assertEqual(plan.learning_path, LEVEL_EXPERIENCED)

    def test_milestone_selection_prefers_exact_band_and_has_general_fallback(self):
        exact_plan = resolve_learning_plan(self.role, EXPERIENCE_3_5, LEVEL_BEGINNER)
        self.assertEqual(exact_plan.milestones, [self.exact_milestone])
        fallback_plan = resolve_learning_plan(self.role, EXPERIENCE_1_2, LEVEL_BEGINNER)
        self.assertEqual(fallback_plan.milestones, [self.general_milestone])

    def test_day_and_attempt_history_remain_attached_when_selection_changes(self):
        user = User.objects.create_user(username='history-student', password='pass12345')
        progress = DayProgress.objects.create(user=user, day=self.general_day1)
        attempt = DayAttempt.objects.create(user=user, day=self.general_day1, score_percent=80)
        resolve_learning_plan(self.role, EXPERIENCE_3_5, LEVEL_EXPERIENCED)
        progress.refresh_from_db()
        attempt.refresh_from_db()
        self.assertEqual(progress.day_id, self.general_day1.pk)
        self.assertEqual(attempt.day_id, self.general_day1.pk)

    def test_invalid_experience_and_path_are_rejected(self):
        with self.assertRaises(ValueError):
            resolve_learning_plan(self.role, '10_years', LEVEL_BEGINNER)
        with self.assertRaises(ValueError):
            resolve_learning_plan(self.role, EXPERIENCE_3_5, 'advanced')

    def test_milestone_assignment_rejects_unrelated_role_or_experience(self):
        question = ScenarioQuestion.objects.create(day=self.other_role_day, text='Data question')
        with self.assertRaises(ValidationError):
            from .models import MilestoneQuestion
            MilestoneQuestion(milestone=self.exact_milestone, question=question).full_clean()
        wrong_band_question = ScenarioQuestion.objects.create(day=self.wrong_band_day, text='Other band question')
        with self.assertRaises(ValidationError):
            MilestoneQuestion(milestone=self.exact_milestone, question=wrong_band_question).full_clean()
