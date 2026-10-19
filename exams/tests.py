from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from careers.choices import EXPERIENCE_CHOICES, EXPERIENCE_3_5, LEVEL_BEGINNER
from careers.models import (
    CareerRole, DayAnswer, DayAttempt, LearningDay, MilestoneExam,
    ScenarioQuestion, Skill,
)
from .models import Category, Exam, ExamAttempt
from .forms import CareerLearningPreferencesForm


User = get_user_model()


class CareerLearningPreferencesFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='learner', password='pass12345')
        cls.role = CareerRole.objects.create(
            title='Backend Developer', summary='Build backend services.', is_published=True)

    def test_all_experience_bands_are_available(self):
        values = {value for value, _label in EXPERIENCE_CHOICES}
        self.assertEqual(values, {'fresher', 'under_1', '1_2', '3_5', 'over_5'})

    def test_three_to_five_experience_and_explicit_fresher_path_persist(self):
        form = CareerLearningPreferencesForm(data={
            'career_role': self.role.pk,
            'experience_band': EXPERIENCE_3_5,
            'learning_path': LEVEL_BEGINNER,
        }, instance=self.user.profile)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.experience_band, EXPERIENCE_3_5)
        self.assertEqual(self.user.profile.learning_path, LEVEL_BEGINNER)
        self.assertEqual(self.user.profile.career_role_id, self.role.pk)

    def test_optional_preferences_keep_existing_profiles_valid(self):
        profile = self.user.profile
        self.assertEqual(profile.experience_band, '')
        self.assertEqual(profile.learning_path, '')
        form = CareerLearningPreferencesForm(data={
            'career_role': '', 'experience_band': '', 'learning_path': '',
        }, instance=profile)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        profile.refresh_from_db()
        self.assertIsNone(profile.career_role_id)
        self.assertEqual(profile.experience_band, '')
        self.assertEqual(profile.learning_path, '')

    def test_invalid_experience_and_path_values_are_rejected(self):
        form = CareerLearningPreferencesForm(data={
            'career_role': self.role.pk,
            'experience_band': 'ten_years',
            'learning_path': 'advanced',
        }, instance=self.user.profile)
        self.assertFalse(form.is_valid())
        self.assertIn('experience_band', form.errors)
        self.assertIn('learning_path', form.errors)

    def test_unpublished_or_unknown_role_is_rejected(self):
        unpublished = CareerRole.objects.create(
            title='Unpublished Track', summary='Not selectable.', is_published=False)
        form = CareerLearningPreferencesForm(data={
            'career_role': unpublished.pk,
            'experience_band': EXPERIENCE_3_5,
            'learning_path': LEVEL_BEGINNER,
        }, instance=self.user.profile)
        self.assertFalse(form.is_valid())
        self.assertIn('career_role', form.errors)


class StudentDashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='dashboard-learner', password='pass12345')
        self.client.force_login(self.user)

    def test_exam_dashboard_is_separate_from_career_dashboard(self):
        response = self.client.get(reverse('exams:student_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Exam performance')
        self.assertContains(response, reverse('careers:dashboard'))
        self.assertNotContains(response, 'Career learning roadmap')
        self.assertNotContains(response, 'Mock Interview')

    def test_exam_dashboard_charts_real_completed_scores(self):
        category = Category.objects.create(name='Analytics', slug='analytics')
        exam = Exam.objects.create(
            title='Analytics foundations', slug='analytics-foundations',
            category=category, description='Test exam')
        ExamAttempt.objects.create(
            user=self.user, exam=exam, completed_at=timezone.now(), score=78)

        response = self.client.get(reverse('exams:student_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Recent exam scores')
        self.assertContains(response, 'Analytics foundations')
        self.assertContains(response, '78.0%')


class CareerDashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='career-dashboard-learner', password='pass12345')
        self.client.force_login(self.user)

    def test_dashboard_without_saved_role_offers_path_selection(self):
        response = self.client.get(reverse('careers:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Choose a career path')
        self.assertContains(response, reverse('exams:profile_settings'))

    def test_dashboard_uses_saved_path_and_actual_lesson_scores(self):
        role = CareerRole.objects.create(
            title='Dashboard Analytics', slug='dashboard-analytics',
            summary='A real published learning path.', is_published=True)
        day = LearningDay.objects.create(
            role=role, day_number=1, title='Start with the data', is_published=True)
        ScenarioQuestion.objects.create(day=day, text='Which metric answers the question?')
        DayAttempt.objects.create(
            user=self.user, day=day, correct_marks=4, total_marks=5, score_percent=80)
        profile = self.user.profile
        profile.career_role = role
        profile.save(update_fields=['career_role'])

        response = self.client.get(reverse('careers:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard Analytics')
        self.assertContains(response, 'Day 1')
        self.assertContains(response, '80%')
        self.assertContains(response, reverse('careers:level_day_detail', args=[role.slug, 'beginner', 1]))

    def test_dashboard_shows_supported_skill_insights_and_milestone_state(self):
        role = CareerRole.objects.create(
            title='Dashboard Quality', slug='dashboard-quality',
            summary='A published quality learning path.', is_published=True)
        day = LearningDay.objects.create(
            role=role, day_number=1, title='Testing basics', is_published=True)
        skill = Skill.objects.create(name='Test design')
        questions = [ScenarioQuestion.objects.create(
            day=day, skill=skill, text=f'Question {index}') for index in range(3)]
        attempt = DayAttempt.objects.create(
            user=self.user, day=day, correct_marks=3, total_marks=3, score_percent=100)
        DayAnswer.objects.bulk_create([
            DayAnswer(attempt=attempt, question=question, is_correct=True)
            for question in questions
        ])
        MilestoneExam.objects.create(
            role=role, number=1, start_day=1, end_day=5, is_published=True)
        profile = self.user.profile
        profile.career_role = role
        profile.save(update_fields=['career_role'])

        response = self.client.get(reverse('careers:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Continue learning')
        self.assertContains(response, 'Skill performance overview')
        self.assertContains(response, 'Test design')
        self.assertContains(response, '3/3 correct')
        self.assertContains(response, 'Milestone assessments')
        self.assertContains(response, 'Upcoming')

    def test_dashboard_hides_skill_insight_with_too_few_answers(self):
        role = CareerRole.objects.create(
            title='Dashboard Practice', slug='dashboard-practice',
            summary='A published practice path.', is_published=True)
        day = LearningDay.objects.create(
            role=role, day_number=1, title='Practice sample size', is_published=True)
        skill = Skill.objects.create(name='Small sample')
        questions = [ScenarioQuestion.objects.create(
            day=day, skill=skill, text=f'Sample question {index}') for index in range(2)]
        attempt = DayAttempt.objects.create(
            user=self.user, day=day, correct_marks=2, total_marks=2, score_percent=100)
        DayAnswer.objects.bulk_create([
            DayAnswer(attempt=attempt, question=question, is_correct=True)
            for question in questions
        ])
        profile = self.user.profile
        profile.career_role = role
        profile.save(update_fields=['career_role'])

        response = self.client.get(reverse('careers:dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Small sample')
        self.assertContains(response, 'at least three questions')
