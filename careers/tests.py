from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import resolve, reverse

from .models import (
    CareerRole, DayAttempt, DayProgress, LearningDay, MilestoneAttempt, MilestoneExam,
    MilestoneQuestion, QuestionOption, ScenarioQuestion, Skill,
    LEVEL_BEGINNER, LEVEL_EXPERIENCED,
)
from . import services

User = get_user_model()
PLAIN_STATIC = override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')


def make_question(day, text, skill, correct_index=0, difficulty='fresher', order=1, published=True):
    """Create a question with three options; ``correct_index`` is the right one."""
    question = ScenarioQuestion.objects.create(
        day=day, text=text, skill=skill, difficulty=difficulty, order=order,
        explanation=f'Explanation for {text}', is_published=published)
    options = [
        QuestionOption.objects.create(question=question, text=f'{text} option {i}',
                                      is_correct=(i == correct_index), order=i)
        for i in range(3)
    ]
    return question, options


@PLAIN_STATIC
class CareersBase(TestCase):
    """Shared fixtures: one published role with ten days and two skills."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('student', 'student@example.com', 'pass12345')
        cls.other = User.objects.create_user('other', 'other@example.com', 'pass12345')
        cls.staff = User.objects.create_user('staff', 's@example.com', 'pass12345', is_staff=True, is_superuser=True)
        cls.sql = Skill.objects.create(name='SQL')
        cls.metrics = Skill.objects.create(name='Metrics')
        cls.role = CareerRole.objects.create(
            title='Test Analytics', summary='Analyse things.', duration_days=10, is_published=True,
            unlock_policy=CareerRole.UNLOCK_SEQUENTIAL, pass_percent=60)
        cls.days = {}
        cls.questions = {}
        for n in range(1, 11):
            day = LearningDay.objects.create(role=cls.role, day_number=n, title=f'Day title {n}')
            cls.days[n] = day
            q1, o1 = make_question(day, f'D{n} first', cls.sql, correct_index=0, order=1)
            q2, o2 = make_question(day, f'D{n} second', cls.metrics, correct_index=1, order=2)
            cls.questions[n] = [(q1, o1), (q2, o2)]

    def answers(self, day_number, correct=(True, True)):
        """Build POST data answering a day's questions correctly or not."""
        data = {}
        for (question, options), ok in zip(self.questions[day_number], correct):
            right = next(o for o in options if o.is_correct)
            wrong = next(o for o in options if not o.is_correct)
            data[f'q_{question.pk}'] = (right if ok else wrong).pk
        return data

    def login(self, user=None):
        self.client.force_login(user or self.user)

    def complete_day_notes(self, day_number, user=None):
        client = self.client
        if user:
            client.force_login(user)
        return client.post(reverse('careers:complete_notes', args=[self.role.slug, day_number]))

    def submit(self, day_number, correct=(True, True), mark_notes=True):
        if mark_notes:
            self.complete_day_notes(day_number)
        return self.client.post(self.days[day_number].get_absolute_url(), self.answers(day_number, correct))


class RoleListAndDetailTests(CareersBase):
    def test_login_required(self):
        response = self.client.get(reverse('careers:role_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_only_published_roles_are_listed(self):
        CareerRole.objects.create(title='Hidden Role', summary='x', is_published=False)
        self.login()
        response = self.client.get(reverse('careers:role_list'))
        self.assertContains(response, 'Test Analytics')
        self.assertNotContains(response, 'Hidden Role')

    def test_unpublished_role_detail_is_404(self):
        hidden = CareerRole.objects.create(title='Hidden Role', summary='x', is_published=False)
        self.login()
        self.assertEqual(self.client.get(hidden.get_absolute_url()).status_code, 404)

    def test_role_detail_lists_days_in_order_and_hides_unpublished(self):
        self.days[3].is_published = False
        self.days[3].save()
        self.login()
        response = self.client.get(self.role.get_absolute_url())
        numbers = [row['day'].day_number for row in response.context['rows']]
        self.assertEqual(numbers, [1, 2, 4, 5, 6, 7, 8, 9, 10])
        self.assertNotContains(response, 'Day title 3')

    def test_milestone_row_shown_even_if_its_end_day_is_unpublished(self):
        MilestoneExam.objects.create(role=self.role, number=1, start_day=1, end_day=5, is_published=True)
        self.days[5].is_published = False
        self.days[5].save()
        self.login()
        response = self.client.get(self.role.get_absolute_url())
        anchored = [r['day'].day_number for r in response.context['rows'] if r['milestones']]
        self.assertEqual(anchored, [4])
        self.assertContains(response, 'Milestone Exam 1')

    def test_role_detail_shows_real_progress_not_hardcoded(self):
        self.login()
        response = self.client.get(self.role.get_absolute_url())
        self.assertEqual(response.context['summary']['submitted_days'], 0)
        self.assertIsNone(response.context['summary']['average_score'])
        self.submit(1)
        response = self.client.get(self.role.get_absolute_url())
        self.assertEqual(response.context['summary']['submitted_days'], 1)
        self.assertEqual(response.context['summary']['average_score'], 100.0)


class DayWorkflowTests(CareersBase):
    def setUp(self):
        self.login()

    def test_day_shows_only_its_own_questions_without_answers_or_explanations(self):
        response = self.client.get(self.days[1].get_absolute_url())
        self.assertContains(response, 'D1 first')
        self.assertNotContains(response, 'D2 first')
        self.assertNotContains(response, 'Explanation for D1 first')
        self.assertNotContains(response, 'is_correct')

    def test_unpublished_day_and_question_not_available(self):
        make_question(self.days[1], 'Hidden question', self.sql, order=3, published=False)
        response = self.client.get(self.days[1].get_absolute_url())
        self.assertNotContains(response, 'Hidden question')
        self.days[1].is_published = False
        self.days[1].save()
        self.assertEqual(self.client.get(self.days[1].get_absolute_url()).status_code, 404)

    def test_opening_a_day_does_not_complete_it(self):
        self.client.get(self.days[1].get_absolute_url())
        progress = DayProgress.objects.get(user=self.user, day=self.days[1])
        self.assertEqual(progress.status, DayProgress.IN_PROGRESS)
        self.assertEqual(DayAttempt.objects.count(), 0)

    def test_submission_is_scored_on_the_server(self):
        self.complete_day_notes(1)
        data = self.answers(1, correct=(True, False))
        data['score'] = '100'
        data['status'] = 'completed'
        response = self.client.post(self.days[1].get_absolute_url(), data)
        attempt = DayAttempt.objects.get(user=self.user, day=self.days[1])
        self.assertRedirects(response, reverse('careers:level_day_result', args=[
            self.role.slug, LEVEL_BEGINNER, 1, attempt.pk]))
        self.assertEqual(attempt.score_percent, 50.0)
        self.assertEqual(attempt.answers.filter(is_correct=True).count(), 1)

    def test_all_questions_must_be_answered(self):
        self.complete_day_notes(1)
        data = self.answers(1)
        data.pop(next(iter(data)))
        response = self.client.post(self.days[1].get_absolute_url(), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'unanswered')
        self.assertEqual(DayAttempt.objects.count(), 0)

    def test_option_from_another_question_is_rejected(self):
        self.complete_day_notes(1)
        data = self.answers(1)
        foreign = self.questions[2][0][1][0]
        first_key = next(iter(data))
        data[first_key] = foreign.pk
        response = self.client.post(self.days[1].get_absolute_url(), data)
        self.assertContains(response, 'not valid')
        self.assertEqual(DayAttempt.objects.count(), 0)

    def test_progress_status_follows_score_and_persists(self):
        self.submit(1, correct=(False, False))
        progress = DayProgress.objects.get(user=self.user, day=self.days[1])
        self.assertEqual(progress.status, DayProgress.REVISION)
        self.client.logout()
        self.login()
        rows = services.plan_overview(self.user, self.role)
        self.assertEqual(rows[0]['status'], DayProgress.REVISION)
        # Retaking with a better score completes the day and keeps history.
        DayAttempt.objects.update(submitted_at=DayAttempt.objects.first().submitted_at.replace(year=2000))
        self.submit(1, correct=(True, True))
        progress.refresh_from_db()
        self.assertEqual(progress.status, DayProgress.COMPLETED)
        self.assertEqual(progress.best_score, 100.0)
        self.assertEqual(progress.attempts_count, 2)
        self.assertEqual(DayAttempt.objects.filter(user=self.user, day=self.days[1]).count(), 2)

    def test_double_submit_creates_single_attempt(self):
        self.submit(1)
        self.submit(1)
        self.assertEqual(DayAttempt.objects.filter(user=self.user, day=self.days[1]).count(), 1)
        self.assertEqual(DayProgress.objects.get(user=self.user, day=self.days[1]).attempts_count, 1)

    def test_get_does_not_submit(self):
        self.client.get(self.days[1].get_absolute_url())
        self.assertEqual(DayAttempt.objects.count(), 0)

    def test_result_page_shows_explanations_and_skills(self):
        self.submit(1, correct=(True, False))
        attempt = DayAttempt.objects.get()
        response = self.client.get(reverse('careers:day_result', args=[self.role.slug, 1, attempt.pk]))
        self.assertContains(response, 'Explanation for D1 first')
        self.assertEqual([s['skill'] for s in response.context['weak']], ['Metrics'])
        self.assertEqual([s['skill'] for s in response.context['strengths']], ['SQL'])


class UnlockPolicyTests(CareersBase):
    def setUp(self):
        self.login()

    def test_sequential_blocks_later_days_until_previous_submitted(self):
        response = self.client.get(self.days[2].get_absolute_url())
        self.assertRedirects(response, reverse('careers:level_role_detail', args=[
            self.role.slug, LEVEL_BEGINNER]), fetch_redirect_response=False)
        self.submit(1)
        self.assertEqual(self.client.get(self.days[2].get_absolute_url()).status_code, 200)

    def test_locked_day_cannot_be_submitted(self):
        self.client.post(self.days[2].get_absolute_url(), self.answers(2))
        self.assertEqual(DayAttempt.objects.count(), 0)

    def test_open_policy_allows_any_day(self):
        self.role.unlock_policy = CareerRole.UNLOCK_OPEN
        self.role.save()
        self.assertEqual(self.client.get(self.days[5].get_absolute_url()).status_code, 200)

    def test_min_score_policy_requires_passing_score(self):
        self.role.unlock_policy = CareerRole.UNLOCK_MIN_SCORE
        self.role.save()
        self.submit(1, correct=(False, False))
        self.assertEqual(self.client.get(self.days[2].get_absolute_url()).status_code, 302)
        DayAttempt.objects.update(submitted_at=DayAttempt.objects.first().submitted_at.replace(year=2000))
        self.submit(1, correct=(True, True))
        self.assertEqual(self.client.get(self.days[2].get_absolute_url()).status_code, 200)


class RecommendationTests(CareersBase):
    def setUp(self):
        self.login()

    def test_next_day_is_first_unsubmitted_day(self):
        self.assertEqual(services.recommend(self.user, self.role)['next_day'], self.days[1])
        self.submit(1)
        self.assertEqual(services.recommend(self.user, self.role)['next_day'], self.days[2])

    def test_revision_and_weak_skill_recommended(self):
        self.submit(1, correct=(True, False))
        self.submit(2, correct=(True, False))
        self.submit(3, correct=(True, False))
        rec = services.recommend(self.user, self.role)
        self.assertEqual([d.day_number for d in rec['revision_days']], [1, 2, 3])
        self.assertEqual(rec['weak_skills'][0]['skill'], 'Metrics')
        self.assertEqual({d.day_number for d in rec['weak_skills'][0]['days']}, {1, 2, 3})

    def test_milestone_due_after_block_is_submitted(self):
        MilestoneExam.objects.create(role=self.role, number=1, start_day=1, end_day=5, is_published=True)
        for n in range(1, 5):
            self.submit(n)
        self.assertIsNone(services.recommend(self.user, self.role)['milestone_due'])
        self.submit(5)
        due = services.recommend(self.user, self.role)['milestone_due']
        self.assertEqual(due['milestone'].number, 1)

    def test_no_recommendation_data_is_invented_for_new_students(self):
        rec = services.recommend(self.other, self.role)
        self.assertEqual(rec['weak_skills'], [])
        self.assertEqual(rec['revision_days'], [])


class MilestoneTests(CareersBase):
    def setUp(self):
        self.login()
        self.m1 = MilestoneExam.objects.create(role=self.role, number=1, start_day=1, end_day=5, is_published=True)
        self.m2 = MilestoneExam.objects.create(role=self.role, number=2, start_day=6, end_day=10, is_published=True)

    def test_pool_is_limited_to_the_five_day_block(self):
        texts = {q.text for q in self.m1.get_questions()}
        self.assertIn('D1 first', texts)
        self.assertIn('D5 second', texts)
        self.assertNotIn('D6 first', texts)
        texts2 = {q.text for q in self.m2.get_questions()}
        self.assertIn('D6 first', texts2)
        self.assertNotIn('D5 first', texts2)

    def test_explicit_assignment_overrides_pool(self):
        MilestoneQuestion.objects.create(milestone=self.m1, question=self.questions[2][0][0])
        self.assertEqual([q.text for q in self.m1.get_questions()], ['D2 first'])

    def test_question_count_limits_pool(self):
        self.m1.question_count = 3
        self.m1.save()
        self.assertEqual(len(self.m1.get_questions()), 3)

    def test_block_numbers_follow_five_day_pattern(self):
        self.assertEqual([self.days[n].milestone_number for n in (1, 5, 6, 10)], [1, 1, 2, 2])

    def test_milestone_locked_until_block_submitted(self):
        response = self.client.get(self.m1.get_absolute_url())
        self.assertRedirects(response, reverse('careers:level_role_detail', args=[
            self.role.slug, LEVEL_BEGINNER]), fetch_redirect_response=False)
        for n in range(1, 6):
            self.submit(n)
        self.assertEqual(self.client.get(self.m1.get_absolute_url()).status_code, 200)

    def test_milestone_scoring_and_persistence(self):
        for n in range(1, 6):
            self.submit(n)
        data = {}
        for i, question in enumerate(self.m1.get_questions()):
            options = list(question.options.all())
            pick = next(o for o in options if o.is_correct) if i < 8 else next(o for o in options if not o.is_correct)
            data[f'q_{question.pk}'] = pick.pk
        response = self.client.post(self.m1.get_absolute_url(), data)
        attempt = MilestoneAttempt.objects.get(user=self.user, milestone=self.m1)
        self.assertRedirects(response, reverse('careers:level_milestone_result', args=[
            self.role.slug, LEVEL_BEGINNER, 1, attempt.pk]))
        self.assertEqual(attempt.total_marks, 10)
        self.assertEqual(attempt.correct_marks, 8)
        self.assertEqual(attempt.score_percent, 80.0)
        self.assertEqual(attempt.answers.count(), 10)
        result = self.client.get(response.url)
        self.assertContains(result, 'Milestone passed')

    def test_milestone_result_not_visible_to_other_students(self):
        attempt = MilestoneAttempt.objects.create(user=self.user, milestone=self.m1, total_marks=1)
        self.client.force_login(self.other)
        url = reverse('careers:milestone_result', args=[self.role.slug, 1, attempt.pk])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_unpublished_milestone_is_404(self):
        self.m1.is_published = False
        self.m1.save()
        self.assertEqual(self.client.get(self.m1.get_absolute_url()).status_code, 404)

    def test_milestone_is_separate_from_regular_exam_tables(self):
        from exams.models import ExamAttempt
        before = ExamAttempt.objects.count()
        for n in range(1, 6):
            self.submit(n)
        self.assertEqual(ExamAttempt.objects.count(), before)


class OwnershipAndAdminTests(CareersBase):
    def test_other_student_cannot_view_my_day_result(self):
        self.login()
        self.submit(1)
        attempt = DayAttempt.objects.get()
        url = reverse('careers:day_result', args=[self.role.slug, 1, attempt.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_progress_is_per_student(self):
        self.login()
        self.submit(1)
        rows = services.plan_overview(self.other, self.role)
        self.assertEqual(rows[0]['status'], 'not_started')

    def test_anonymous_cannot_submit(self):
        response = self.client.post(self.days[1].get_absolute_url(), self.answers(1))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(DayAttempt.objects.count(), 0)

    def test_csrf_is_enforced_on_submission(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        response = client.post(self.days[1].get_absolute_url(), self.answers(1))
        self.assertEqual(response.status_code, 403)

    def test_admin_requires_staff(self):
        url = reverse('admin:careers_careerrole_changelist')
        self.login()
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_admin_can_open_content_forms(self):
        self.client.force_login(self.staff)
        for name in ('careers_scenarioquestion_add', 'careers_milestoneexam_add', 'careers_learningday_add'):
            self.assertEqual(self.client.get(reverse(f'admin:{name}')).status_code, 200, name)

    def test_student_progress_is_read_only_in_admin(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse('admin:careers_dayprogress_add')).status_code, 403)


@PLAIN_STATIC
class NavigationVisibilityTests(TestCase):
    """Mock interview UI stays hidden while backend routes remain available."""

    def test_entry_points_hidden_by_default(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse('home_page_coding'))
        self.assertNotContains(response, reverse('exams:mock_interview_form'))
        self.assertContains(response, reverse('careers:role_list'))

    @override_settings(FEATURE_FLAGS={'coding': True, 'mock_interviews': True})
    def test_coding_entry_point_returns_but_interview_ui_stays_hidden(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, reverse('home_page_coding'))
        self.assertNotContains(response, reverse('exams:mock_interview_form'))

    @override_settings(FEATURE_FLAGS={'coding': True, 'mock_interviews': True})
    def test_public_learning_pages_render_without_interview_promotions(self):
        for name in ('home', 'about', 'services', 'exams:study_guide'):
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, 'Mock Interview')
                self.assertNotContains(response, reverse('exams:mock_interview_form'))

    def test_hidden_features_remain_routable(self):
        self.assertEqual(resolve(reverse('home_page_coding')).view_name, 'home_page_coding')
        self.assertEqual(resolve(reverse('problem_list')).view_name, 'problem_list')
        self.assertEqual(resolve(reverse('exams:mock_interview_form')).view_name, 'exams:mock_interview_form')
        self.assertNotEqual(self.client.get(reverse('problem_list')).status_code, 404)


@PLAIN_STATIC
class RegressionTests(TestCase):
    """Existing pages still render after adding the careers app."""

    def test_login_and_signup_pages_render(self):
        self.assertEqual(self.client.get(reverse('login')).status_code, 200)
        self.assertEqual(self.client.get(reverse('signup')).status_code, 200)

    def test_home_page_renders_for_anonymous_and_logged_in_users(self):
        self.assertEqual(self.client.get(reverse('home')).status_code, 200)
        user = User.objects.create_user('reg', 'reg@example.com', 'pass12345')
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse('home')).status_code, 200)

    def test_regular_mock_exam_list_unchanged(self):
        from exams.models import Category, Exam
        category = Category.objects.create(name='Python', slug='python')
        Exam.objects.create(title='Python Basics', slug='python-basics', category=category, description='d')
        response = self.client.get(reverse('exams:exam_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Python Basics')

    def test_regular_exam_urls_still_resolve(self):
        for name in ('exams:exam_list', 'exams:student_dashboard', 'exams:study_guide'):
            self.assertTrue(reverse(name))


class SeedCommandTests(TestCase):
    def test_seed_is_idempotent_and_valid(self):
        call_command('seed_careers', verbosity=0)
        roles = CareerRole.objects.count()
        questions = ScenarioQuestion.objects.count()
        self.assertEqual(roles, 7)
        self.assertEqual(MilestoneExam.objects.count(), 7)
        for question in ScenarioQuestion.objects.prefetch_related('options'):
            options = list(question.options.all())
            self.assertGreaterEqual(len(options), 2, question)
            self.assertEqual(sum(o.is_correct for o in options), 1, question)
        call_command('seed_careers', verbosity=0)
        self.assertEqual(CareerRole.objects.count(), roles)
        self.assertEqual(ScenarioQuestion.objects.count(), questions)

    def test_seed_does_not_overwrite_admin_edits(self):
        call_command('seed_careers', verbosity=0)
        role = CareerRole.objects.get(title='Data Analytics')
        role.summary = 'Edited by admin'
        role.is_published = False
        role.save()
        call_command('seed_careers', verbosity=0)
        role.refresh_from_db()
        self.assertEqual(role.summary, 'Edited by admin')
        self.assertFalse(role.is_published)


@PLAIN_STATIC
class RedesignedDayTests(TestCase):
    """Data Analytics Day 1 carries the rich lesson; other days keep the plain layout."""

    @classmethod
    def setUpTestData(cls):
        call_command('seed_careers', verbosity=0)
        cls.user = User.objects.create_user('learner', 'l@example.com', 'pass12345')
        cls.role = CareerRole.objects.get(title='Data Analytics')
        cls.day1 = cls.role.days.get(day_number=1)

    def setUp(self):
        self.client.force_login(self.user)

    def test_lesson_sections_render(self):
        html = self.client.get(self.day1.get_absolute_url()).content.decode()
        for expected in ('What you will learn', 'Real-world scenario', 'The 12% sales drop',
                         'A six-step approach', 'Validate the data', 'Should we react to the drop?',
                         'Reactive versus evidence-based', 'Business situation', 'Common mistake',
                         'Quick revision', 'CHECK YOUR UNDERSTANDING', 'Question 1', 'Question 2'):
            self.assertIn(expected, html)

    def test_answers_and_explanations_hidden_before_submission(self):
        html = self.client.get(self.day1.get_absolute_url()).content.decode()
        self.assertNotIn('Correct. It confirms the number', html)
        self.assertNotIn('Takeaway', html)
        self.assertNotIn('is_correct', html)

    def test_other_days_keep_plain_layout(self):
        response = self.client.get(self.role.days.get(day_number=1).get_absolute_url())
        self.assertTrue(response.context['lesson'])
        # Day 2 is locked under the sequential policy, so open it for this check.
        self.role.unlock_policy = CareerRole.UNLOCK_OPEN
        self.role.save()
        response = self.client.get(self.role.days.get(day_number=2).get_absolute_url())
        self.assertFalse(response.context['lesson'])
        self.assertNotContains(response, 'lx-header')

    def test_feedback_after_submission_teaches_every_option(self):
        self.client.post(reverse('careers:complete_notes', args=[self.role.slug, self.day1.day_number]))
        data = {}
        for question in self.day1.questions.all():
            data[f'q_{question.pk}'] = question.options.filter(is_correct=False).first().pk
        response = self.client.post(self.day1.get_absolute_url(), data)
        result = self.client.get(response.url)
        self.assertContains(result, 'Correct. It confirms the number')
        self.assertContains(result, 'Takeaway')
        self.assertContains(result, 'A discount is a solution')

    def test_navigation_locks_next_day_until_submitted(self):
        response = self.client.get(self.day1.get_absolute_url())
        self.assertIsNone(response.context['previous_day'])
        self.assertEqual(response.context['next_day'].day_number, 2)
        self.assertFalse(response.context['next_unlocked'])
        self.assertContains(response, 'Day 2 locked')
        # Marking notes alone doesn't unlock Day 2
        self.client.post(reverse('careers:complete_notes', args=[self.role.slug, self.day1.day_number]))
        response = self.client.get(self.day1.get_absolute_url())
        self.assertFalse(response.context['next_unlocked'])
        # Submitting questions unlocks Day 2
        data = {f'q_{q.pk}': q.options.get(is_correct=True).pk for q in self.day1.questions.all()}
        self.client.post(self.day1.get_absolute_url(), data)
        response = self.client.get(self.day1.get_absolute_url())
        self.assertTrue(response.context['next_unlocked'])

    def test_lesson_text_is_escaped(self):
        self.day1.lesson_intro = '<script>alert(1)</script> **bold**'
        self.day1.save()
        html = self.client.get(self.day1.get_absolute_url()).content.decode()
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('<strong>bold</strong>', html)

    def test_seed_keeps_admin_edited_lesson(self):
        self.day1.lesson_intro = 'Edited by admin'
        self.day1.save()
        call_command('seed_careers', verbosity=0)
        self.day1.refresh_from_db()
        self.assertEqual(self.day1.lesson_intro, 'Edited by admin')



@PLAIN_STATIC
class NotesCompletionWorkflowTests(CareersBase):
    """Tests for notes completion actions, gating, and isolation."""

    def setUp(self):
        self.login()

    def test_opening_day_does_not_mark_notes_complete(self):
        self.client.get(self.days[1].get_absolute_url())
        progress = DayProgress.objects.filter(user=self.user, day=self.days[1]).first()
        self.assertIsNotNone(progress)
        self.assertFalse(progress.notes_completed)
        self.assertIsNone(progress.notes_completed_at)

    def test_mark_notes_complete_action_saves_against_user_and_day(self):
        url = reverse('careers:complete_notes', args=[self.role.slug, 1])
        response = self.client.post(url)
        self.assertRedirects(response, reverse('careers:level_day_detail', args=[
            self.role.slug, LEVEL_BEGINNER, 1]))
        progress = DayProgress.objects.get(user=self.user, day=self.days[1])
        self.assertTrue(progress.notes_completed)
        self.assertIsNotNone(progress.notes_completed_at)

    def test_cannot_submit_questions_without_completing_notes(self):
        response = self.client.post(self.days[1].get_absolute_url(), self.answers(1))
        # Form shows error and does not create an attempt
        self.assertEqual(DayAttempt.objects.filter(user=self.user, day=self.days[1]).count(), 0)
        # Attempting direct submit_day raises SubmissionError
        with self.assertRaises(services.SubmissionError):
            services.submit_day(self.user, self.days[1], self.answers(1))

    def test_submitting_questions_after_completing_notes_succeeds(self):
        self.complete_day_notes(1)
        response = self.client.post(self.days[1].get_absolute_url(), self.answers(1))
        self.assertEqual(DayAttempt.objects.filter(user=self.user, day=self.days[1]).count(), 1)
        progress = DayProgress.objects.get(user=self.user, day=self.days[1])
        self.assertTrue(progress.notes_completed)
        self.assertTrue(progress.is_submitted)
        self.assertTrue(progress.is_completed)

    def test_next_day_unlocks_only_when_current_day_notes_and_questions_complete(self):
        # Day 2 is locked initially
        days_list = list(self.days.values())
        self.assertFalse(services.is_day_unlocked(self.role, self.days[2], days_list, services.progress_map(self.user, self.role), user=self.user))
        # Marking notes alone keeps Day 2 locked
        self.complete_day_notes(1)
        self.assertFalse(services.is_day_unlocked(self.role, self.days[2], days_list, services.progress_map(self.user, self.role), user=self.user))
        # Submitting questions unlocks Day 2
        self.client.post(self.days[1].get_absolute_url(), self.answers(1))
        self.assertTrue(services.is_day_unlocked(self.role, self.days[2], days_list, services.progress_map(self.user, self.role), user=self.user))

    def test_cannot_complete_notes_on_locked_day(self):
        url = reverse('careers:complete_notes', args=[self.role.slug, 2])
        response = self.client.post(url)
        self.assertRedirects(response, reverse('careers:level_role_detail', args=[
            self.role.slug, LEVEL_BEGINNER]))
        self.assertFalse(DayProgress.objects.filter(user=self.user, day=self.days[2], notes_completed=True).exists())

    def test_notes_completion_is_isolated_between_students(self):
        self.complete_day_notes(1)
        other_prog = DayProgress.objects.filter(user=self.other, day=self.days[1]).first()
        self.assertTrue(other_prog is None or not other_prog.notes_completed)


@PLAIN_STATIC
class FiveDayMilestoneProgressionTests(CareersBase):
    """Tests for the 5-day milestone gating, 75% threshold, retakes, and progression."""

    def setUp(self):
        self.login()
        self.m1 = MilestoneExam.objects.create(role=self.role, number=1, start_day=1, end_day=5, is_published=True)
        self.m2 = MilestoneExam.objects.create(role=self.role, number=2, start_day=6, end_day=10, is_published=True)

    def complete_days(self, start=1, end=5, user=None):
        for n in range(start, end + 1):
            self.submit(n)

    def build_milestone_answers(self, milestone, correct_count=8):
        questions = milestone.get_questions()
        data = {}
        for i, q in enumerate(questions):
            options = list(q.options.all())
            is_ok = i < correct_count
            pick = next(o for o in options if o.is_correct == is_ok)
            data[f'q_{q.pk}'] = pick.pk
        return data

    def test_milestone_1_locked_until_days_1_to_5_notes_and_questions_complete(self):
        # Complete Days 1 to 4
        self.complete_days(1, 4)
        status = services.milestone_status(self.user, self.m1)
        self.assertFalse(status['available'])

        # Day 5 mark notes only
        self.complete_day_notes(5)
        status = services.milestone_status(self.user, self.m1)
        self.assertFalse(status['available'])

        # Day 5 submit questions
        self.client.post(self.days[5].get_absolute_url(), self.answers(5))
        status = services.milestone_status(self.user, self.m1)
        self.assertTrue(status['available'])

    def test_milestone_score_below_75_percent_keeps_block_2_locked(self):
        self.complete_days(1, 5)
        # 6 out of 10 correct = 60% (< 75%)
        data = self.build_milestone_answers(self.m1, correct_count=6)
        response = self.client.post(self.m1.get_absolute_url(), data)
        self.assertEqual(response.status_code, 302)

        # Day 6 must remain locked
        days_list = list(self.days.values())
        prog_map = services.progress_map(self.user, self.role)
        self.assertFalse(services.is_day_unlocked(self.role, self.days[6], days_list, prog_map, user=self.user))

        # Direct access to Day 6 is redirected
        day6_resp = self.client.get(self.days[6].get_absolute_url())
        self.assertRedirects(day6_resp, reverse('careers:level_role_detail', args=[
            self.role.slug, LEVEL_BEGINNER]))

        # Milestone result displays retake option and below pass threshold
        result_resp = self.client.get(response.url)
        self.assertContains(result_resp, 'Below pass threshold')
        self.assertContains(result_resp, 'Retake milestone')

    def test_milestone_score_75_percent_or_above_unlocks_day_6(self):
        self.complete_days(1, 5)
        # 8 out of 10 correct = 80% (>= 75%)
        data = self.build_milestone_answers(self.m1, correct_count=8)
        response = self.client.post(self.m1.get_absolute_url(), data)
        self.assertEqual(response.status_code, 302)

        # Day 6 is now UNLOCKED
        days_list = list(self.days.values())
        prog_map = services.progress_map(self.user, self.role)
        self.assertTrue(services.is_day_unlocked(self.role, self.days[6], days_list, prog_map, user=self.user))

        # Student can open Day 6
        day6_resp = self.client.get(self.days[6].get_absolute_url())
        self.assertEqual(day6_resp.status_code, 200)

        # Result shows congratulations
        result_resp = self.client.get(response.url)
        self.assertContains(result_resp, 'Milestone passed')
        self.assertContains(result_resp, 'Continue to Day 6')

    def test_best_milestone_score_preserved_across_retakes(self):
        self.complete_days(1, 5)
        # First attempt: 80% (passed)
        data1 = self.build_milestone_answers(self.m1, correct_count=8)
        self.client.post(self.m1.get_absolute_url(), data1)

        # Retake attempt: 50% (lower score)
        data2 = self.build_milestone_answers(self.m1, correct_count=5)
        self.client.post(self.m1.get_absolute_url(), data2)

        # Best score is preserved at 80%
        best = services.best_milestone_score(self.user, self.m1)
        self.assertEqual(best, 80.0)

        # Day 6 remains unlocked! Progression is not revoked
        days_list = list(self.days.values())
        prog_map = services.progress_map(self.user, self.role)
        self.assertTrue(services.is_day_unlocked(self.role, self.days[6], days_list, prog_map, user=self.user))

    def test_days_in_block_2_unlock_sequentially_after_milestone_1(self):
        self.complete_days(1, 5)
        data = self.build_milestone_answers(self.m1, correct_count=8)
        self.client.post(self.m1.get_absolute_url(), data)

        # Day 6 is unlocked, Day 7 is still locked until Day 6 is finished
        days_list = list(self.days.values())
        prog_map = services.progress_map(self.user, self.role)
        self.assertTrue(services.is_day_unlocked(self.role, self.days[6], days_list, prog_map, user=self.user))
        self.assertFalse(services.is_day_unlocked(self.role, self.days[7], days_list, prog_map, user=self.user))

        # Finish Day 6
        self.submit(6)
        prog_map = services.progress_map(self.user, self.role)
        self.assertTrue(services.is_day_unlocked(self.role, self.days[7], days_list, prog_map, user=self.user))

    def test_student_isolation_for_milestone_progression(self):
        self.complete_days(1, 5)
        data = self.build_milestone_answers(self.m1, correct_count=8)
        self.client.post(self.m1.get_absolute_url(), data)

        # Other student logs in: Day 6 and Milestone 1 are locked for other student
        self.client.force_login(self.other)
        days_list = list(self.days.values())
        prog_map = services.progress_map(self.other, self.role)
        self.assertFalse(services.is_day_unlocked(self.role, self.days[6], days_list, prog_map, user=self.other))
        status = services.milestone_status(self.other, self.m1)
        self.assertFalse(status['available'])

    def test_open_unlock_policy_bypasses_locks(self):
        self.role.unlock_policy = CareerRole.UNLOCK_OPEN
        self.role.save()
        days_list = list(self.days.values())
        prog_map = services.progress_map(self.user, self.role)
        self.assertTrue(services.is_day_unlocked(self.role, self.days[6], days_list, prog_map, user=self.user))

    def test_direct_url_access_blocked_for_locked_milestone(self):
        response = self.client.get(self.m1.get_absolute_url())
        self.assertRedirects(response, reverse('careers:level_role_detail', args=[
            self.role.slug, LEVEL_BEGINNER]))

    def test_direct_submission_blocked_for_locked_milestone(self):
        data = self.build_milestone_answers(self.m1, correct_count=8)
        with self.assertRaises(services.SubmissionError):
            services.submit_milestone(self.user, self.m1, data)


@PLAIN_STATIC
class RegularMockExamRegressionTests(TestCase):
    """Verify that exams app models, attempts, and functionality are untouched."""

    def test_exams_models_and_tables_operate_normally(self):
        from exams.models import Exam, Question, ExamAttempt, Category
        category = Category.objects.create(name='Test Category')
        exam = Exam.objects.create(
            title='Regular Mock Exam',
            category=category,
            description='Test description',
        )
        self.assertEqual(Exam.objects.filter(title='Regular Mock Exam').count(), 1)
        self.assertEqual(exam.category.name, 'Test Category')


# ---------------------------------------------------------------------------
# Markdown rendering, admin lesson fields, question gating, and migration
# ---------------------------------------------------------------------------

@PLAIN_STATIC
class MarkdownRenderingAndAdminTests(CareersBase):
    """Verify Markdown content is rendered as safe HTML and admin forms expose
    all lesson fields via the new fieldsets."""

    def setUp(self):
        self.login()

    # ---- Markdown rendering ------------------------------------------------

    def test_lesson_body_markdown_renders_headings_and_paragraphs(self):
        day = self.days[1]
        day.lesson_body = '## Hello\n\nA paragraph.'
        day.save()
        html = self.client.get(day.get_absolute_url()).content.decode()
        self.assertIn('<h2>Hello</h2>', html)
        self.assertIn('<p>A paragraph.</p>', html)

    def test_lesson_body_markdown_renders_fenced_code_block(self):
        day = self.days[1]
        day.lesson_body = '```python\nprint("hi")\n```'
        day.save()
        html = self.client.get(day.get_absolute_url()).content.decode()
        self.assertIn('<code', html)
        self.assertIn('print', html)

    def test_lesson_body_markdown_renders_table(self):
        day = self.days[1]
        day.lesson_body = '| A | B |\n|---|---|\n| 1 | 2 |'
        day.save()
        html = self.client.get(day.get_absolute_url()).content.decode()
        self.assertIn('<table', html)
        self.assertIn('<th>', html)

    def test_lesson_scenario_rendered_in_aside(self):
        day = self.days[1]
        day.lesson_scenario = '### Situation\n\nA company lost revenue.'
        day.save()
        html = self.client.get(day.get_absolute_url()).content.decode()
        self.assertIn('lx-scenario', html)
        self.assertIn('Real-world scenario', html)
        self.assertIn('lost revenue', html)

    def test_lesson_revision_rendered_after_body(self):
        day = self.days[1]
        day.lesson_body = '## Body text'
        day.lesson_revision = '## Quick revision\n\n- Point one'
        day.save()
        html = self.client.get(day.get_absolute_url()).content.decode()
        self.assertIn('lx-revision', html)
        self.assertIn('Point one', html)

    def test_xss_in_lesson_body_is_sanitised(self):
        day = self.days[1]
        day.lesson_body = '<script>alert("xss")</script> **safe bold**'
        day.save()
        html = self.client.get(day.get_absolute_url()).content.decode()
        # nh3 strips disallowed <script> tags AND their content from lesson HTML;
        # the injected payload must not appear in the page at all.
        self.assertNotIn('alert("xss")', html)
        # Markdown bold still processed after sanitisation.
        self.assertIn('<strong>safe bold</strong>', html)

    def test_flow_diagram_block_renders(self):
        day = self.days[1]
        day.lesson_body = '```flow\nStep A | hint\nStep B\n```'
        day.save()
        html = self.client.get(day.get_absolute_url()).content.decode()
        self.assertIn('lx-flow', html)
        self.assertIn('Step A', html)

    # ---- Admin lesson field access -----------------------------------------

    def test_admin_change_form_contains_all_lesson_fields(self):
        self.client.force_login(self.staff)
        day = self.days[1]
        url = reverse('admin:careers_learningday_change', args=[day.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        for field in ('lesson_intro', 'lesson_scenario', 'lesson_body', 'lesson_revision',
                      'difficulty_level', 'estimated_minutes', 'objectives', 'topics'):
            self.assertContains(response, field, msg_prefix=f'Missing field: {field}')

    def test_admin_can_save_lesson_body_and_student_sees_rendered_html(self):
        self.client.force_login(self.staff)
        day = self.days[1]
        url = reverse('admin:careers_learningday_change', args=[day.pk])
        post_data = {
            'role': day.role.pk,
            'day_number': day.day_number,
            'title': day.title,
            'is_published': True,
            'objectives': '',
            'topics': '',
            'lesson_intro': '',
            'lesson_scenario': '',
            'lesson_body': '## Admin wrote this\n\nContent from admin.',
            'lesson_revision': '',
            'difficulty_level': 'Beginner',
            'estimated_minutes': 30,
        }
        response = self.client.post(url, post_data)
        # Admin saves successfully (redirect to changelist)
        self.assertIn(response.status_code, (200, 302))
        day.refresh_from_db()
        self.assertEqual(day.lesson_body, '## Admin wrote this\n\nContent from admin.')

        # Student sees it rendered
        self.client.force_login(self.user)
        html = self.client.get(day.get_absolute_url()).content.decode()
        self.assertIn('<h2>Admin wrote this</h2>', html)
        self.assertIn('Content from admin.', html)

    # ---- Question visibility gating ----------------------------------------

    def test_question_text_visible_before_notes_complete(self):
        """Questions appear in the DOM but the submit button is disabled."""
        day = self.days[1]
        html = self.client.get(day.get_absolute_url()).content.decode()
        # Question text visible
        self.assertIn('D1 first', html)
        # Submit button is disabled when notes are not complete
        self.assertIn('Submit answers · Locked', html)

    def test_question_submit_enabled_after_notes_complete(self):
        self.client.post(reverse('careers:complete_notes', args=[self.role.slug, 1]))
        html = self.client.get(self.days[1].get_absolute_url()).content.decode()
        # No disabled submit button when notes are complete
        self.assertNotIn('Submit answers · Locked', html)
        self.assertIn('Submit answers', html)

    def test_post_without_notes_complete_does_not_create_attempt(self):
        # Attempt to submit without completing notes
        self.client.post(self.days[1].get_absolute_url(), self.answers(1))
        self.assertEqual(DayAttempt.objects.filter(user=self.user, day=self.days[1]).count(), 0)


@PLAIN_STATIC
class GrandfatheringMigrationTests(TestCase):
    """Verify that the grandfathering RunPython logic correctly categorises
    existing DayProgress rows without touching the test database."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('gf_student', 'gf@example.com', 'pass12345')
        cls.role = CareerRole.objects.create(
            title='GF Role', summary='Test', duration_days=5, is_published=True,
            unlock_policy=CareerRole.UNLOCK_SEQUENTIAL, pass_percent=60,
        )
        cls.skill = Skill.objects.create(name='GF Skill')
        cls.days = {}
        for n in range(1, 6):
            day = LearningDay.objects.create(role=cls.role, day_number=n, title=f'GF Day {n}')
            cls.days[n] = day

    def _make_progress(self, day, status, attempts_count, last_attempt_at=None):
        from django.utils import timezone
        return DayProgress.objects.create(
            user=self.user,
            day=day,
            status=status,
            attempts_count=attempts_count,
            last_attempt_at=last_attempt_at or (timezone.now() if attempts_count > 0 else None),
        )

    def _run_grandfather(self):
        """Execute the same logic as the migration RunPython function."""
        submitted_statuses = {'completed', 'revision_recommended'}
        to_update = []
        for progress in DayProgress.objects.filter(user=self.user, day__role=self.role):
            if progress.status in submitted_statuses or progress.attempts_count > 0:
                progress.notes_completed = True
                progress.notes_completed_at = progress.last_attempt_at
                to_update.append(progress)
        if to_update:
            DayProgress.objects.bulk_update(to_update, ['notes_completed', 'notes_completed_at'])

    def test_completed_status_is_grandfathered(self):
        from django.utils import timezone
        ts = timezone.now()
        prog = self._make_progress(self.days[1], DayProgress.COMPLETED, attempts_count=1, last_attempt_at=ts)
        self._run_grandfather()
        prog.refresh_from_db()
        self.assertTrue(prog.notes_completed)
        self.assertIsNotNone(prog.notes_completed_at)

    def test_revision_recommended_status_is_grandfathered(self):
        prog = self._make_progress(self.days[2], DayProgress.REVISION, attempts_count=1)
        self._run_grandfather()
        prog.refresh_from_db()
        self.assertTrue(prog.notes_completed)

    def test_in_progress_with_no_attempts_is_not_grandfathered(self):
        prog = self._make_progress(self.days[3], DayProgress.IN_PROGRESS, attempts_count=0, last_attempt_at=None)
        self._run_grandfather()
        prog.refresh_from_db()
        self.assertFalse(prog.notes_completed)
        self.assertIsNone(prog.notes_completed_at)

    def test_in_progress_with_attempts_is_grandfathered(self):
        """An in-progress record that nevertheless has attempts should be grandfathered."""
        prog = self._make_progress(self.days[4], DayProgress.IN_PROGRESS, attempts_count=2)
        self._run_grandfather()
        prog.refresh_from_db()
        self.assertTrue(prog.notes_completed)

    def test_grandfathered_timestamp_matches_last_attempt_at(self):
        from django.utils import timezone
        ts = timezone.now()
        prog = self._make_progress(self.days[5], DayProgress.COMPLETED, attempts_count=1, last_attempt_at=ts)
        self._run_grandfather()
        prog.refresh_from_db()
        self.assertEqual(prog.notes_completed_at, ts)

    def test_completed_with_null_last_attempt_at_gets_null_timestamp(self):
        """If last_attempt_at is null, notes_completed_at should also remain null."""
        prog = DayProgress.objects.create(
            user=self.user, day=self.days[1], status=DayProgress.COMPLETED,
            attempts_count=1, last_attempt_at=None,
        )
        self._run_grandfather()
        prog.refresh_from_db()
        self.assertTrue(prog.notes_completed)
        self.assertIsNone(prog.notes_completed_at)


@PLAIN_STATIC
class IndependentLearningLevelTests(CareersBase):
    def setUp(self):
        self.login()
        self.experienced_day1 = LearningDay.objects.create(
            role=self.role, level=LEVEL_EXPERIENCED, day_number=1, title='Experienced Day 1')
        self.experienced_question, self.experienced_options = make_question(
            self.experienced_day1, 'Experienced-only question', self.sql)

    def test_same_numbered_day_and_milestone_can_exist_per_level(self):
        self.assertEqual(self.days[1].level, LEVEL_BEGINNER)
        self.assertEqual(self.experienced_day1.level, LEVEL_EXPERIENCED)
        MilestoneExam.objects.create(role=self.role, number=1, start_day=1, end_day=5)
        MilestoneExam.objects.create(role=self.role, level=LEVEL_EXPERIENCED,
                                     number=1, start_day=1, end_day=5)

    def test_experienced_day_is_independent_and_only_shows_its_questions(self):
        response = self.client.get(reverse('careers:level_day_detail', args=[
            self.role.slug, LEVEL_EXPERIENCED, 1]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Experienced-only question')
        self.assertNotContains(response, 'D1 first')
        self.assertEqual(response.context['level'], LEVEL_EXPERIENCED)

    def test_level_page_rejects_invalid_level(self):
        response = self.client.get(reverse('careers:level_role_detail', args=[self.role.slug, 'expert']))
        self.assertEqual(response.status_code, 404)

    def test_notes_and_submissions_are_separate_by_day_record(self):
        self.client.post(reverse('careers:level_complete_notes', args=[
            self.role.slug, LEVEL_EXPERIENCED, 1]))
        experienced_progress = DayProgress.objects.get(user=self.user, day=self.experienced_day1)
        self.assertTrue(experienced_progress.notes_completed)
        self.assertFalse(DayProgress.objects.filter(user=self.user, day=self.days[1]).exists())
        result = self.client.post(self.experienced_day1.get_absolute_url(), {
            f'q_{self.experienced_question.pk}': self.experienced_options[0].pk,
        })
        self.assertEqual(result.status_code, 302)
        self.assertEqual(DayAttempt.objects.filter(user=self.user, day=self.experienced_day1).count(), 1)
        self.assertEqual(DayAttempt.objects.filter(user=self.user, day=self.days[1]).count(), 0)

    def test_beginner_progress_does_not_unlock_experienced_next_day(self):
        experienced_day2 = LearningDay.objects.create(
            role=self.role, level=LEVEL_EXPERIENCED, day_number=2, title='Experienced Day 2')
        make_question(experienced_day2, 'Experienced Day 2 question', self.sql)
        # Finish the Beginner Day 1 flow first.
        self.client.post(reverse('careers:complete_notes', args=[self.role.slug, 1]))
        self.client.post(self.days[1].get_absolute_url(), self.answers(1))
        locked = self.client.get(experienced_day2.get_absolute_url())
        self.assertEqual(locked.status_code, 302)
        # The Experienced path unlocks independently after its own Day 1 is completed.
        self.client.post(reverse('careers:level_complete_notes', args=[
            self.role.slug, LEVEL_EXPERIENCED, 1]))
        self.client.post(self.experienced_day1.get_absolute_url(), {
            f'q_{self.experienced_question.pk}': self.experienced_options[0].pk,
        })
        self.assertEqual(self.client.get(experienced_day2.get_absolute_url()).status_code, 200)

    def test_experienced_attempt_result_cannot_be_opened_as_beginner(self):
        self.client.post(reverse('careers:level_complete_notes', args=[
            self.role.slug, LEVEL_EXPERIENCED, 1]))
        self.client.post(self.experienced_day1.get_absolute_url(), {
            f'q_{self.experienced_question.pk}': self.experienced_options[0].pk,
        })
        attempt = DayAttempt.objects.get(user=self.user, day=self.experienced_day1)
        wrong_path = reverse('careers:day_result', args=[
            self.role.slug, self.experienced_day1.day_number, attempt.pk])
        self.assertEqual(self.client.get(wrong_path).status_code, 404)

    def test_milestone_pool_and_assignment_are_level_scoped(self):
        beginner_milestone = MilestoneExam.objects.create(
            role=self.role, number=1, start_day=1, end_day=5)
        experienced_milestone = MilestoneExam.objects.create(
            role=self.role, level=LEVEL_EXPERIENCED, number=1, start_day=1, end_day=5)
        self.assertNotIn(self.experienced_question, beginner_milestone.get_questions())
        self.assertIn(self.experienced_question, experienced_milestone.get_questions())
        assignment = MilestoneQuestion(milestone=beginner_milestone, question=self.experienced_question)
        with self.assertRaises(ValidationError):
            assignment.full_clean()


@PLAIN_STATIC
class CareerPreferencesJourneyTests(CareersBase):
    """Exercise saved career preferences through the student learning journey."""

    def setUp(self):
        self.login()
        self.exact_day1 = LearningDay.objects.create(
            role=self.role, level=LEVEL_EXPERIENCED, experience_band='3_5',
            day_number=1, title='Targeted experienced lesson', lesson_body='Targeted lesson body')
        self.exact_question, self.exact_options = make_question(
            self.exact_day1, 'Question for three to five years experience', self.sql)
        self.general_day1 = LearningDay.objects.create(
            role=self.role, level=LEVEL_EXPERIENCED, experience_band='all',
            day_number=1, title='General Day 1')
        make_question(self.general_day1, 'General Day 1 question', self.sql)
        self.general_day2 = LearningDay.objects.create(
            role=self.role, level=LEVEL_EXPERIENCED, experience_band='all',
            day_number=2, title='General fallback Day 2')
        make_question(self.general_day2, 'General fallback Day 2 question', self.sql)
        self.other_band_day2 = LearningDay.objects.create(
            role=self.role, level=LEVEL_EXPERIENCED, experience_band='1_2',
            day_number=2, title='Unrelated experience Day 2')
        make_question(self.other_band_day2, 'Unrelated experience question', self.sql)

    def test_settings_post_drives_personalized_plan_and_preserves_history_links(self):
        from exams.models import Profile

        legacy_progress = DayProgress.objects.create(
            user=self.user, day=self.days[1], status=DayProgress.COMPLETED,
            best_score=80, last_score=80, attempts_count=1)
        legacy_attempt = DayAttempt.objects.create(
            user=self.user, day=self.days[1], correct_marks=1, total_marks=1, score_percent=100)

        settings_url = reverse('exams:profile_settings')
        settings_page = self.client.get(f'{settings_url}?tab=career')
        self.assertEqual(settings_page.status_code, 200)
        self.assertIn('career_preferences_form', settings_page.context)

        saved = self.client.post(reverse('exams:update_career_preferences'), {
            'career_role': self.role.pk,
            'experience_band': '3_5',
            'learning_path': LEVEL_EXPERIENCED,
        })
        self.assertRedirects(
            saved,
            reverse('careers:level_role_detail', args=[self.role.slug, LEVEL_EXPERIENCED]),
        )
        profile = Profile.objects.get(user=self.user)
        self.assertEqual(profile.career_role, self.role)
        self.assertEqual(profile.experience_band, '3_5')
        self.assertEqual(profile.learning_path, LEVEL_EXPERIENCED)

        role_page = self.client.get(self.role.get_absolute_url())
        self.assertEqual(role_page.status_code, 200)
        self.assertEqual(role_page.context['level'], LEVEL_EXPERIENCED)
        self.assertEqual(role_page.context['experience_band'], '3_5')
        selected_days = [row['day'] for row in role_page.context['rows']]
        self.assertEqual(selected_days, [self.exact_day1, self.general_day2])
        self.assertNotIn(self.general_day1, selected_days)
        self.assertNotIn(self.other_band_day2, selected_days)

        lesson_url = reverse('careers:level_day_detail', args=[
            self.role.slug, LEVEL_EXPERIENCED, 1])
        lesson = self.client.get(lesson_url)
        self.assertEqual(lesson.status_code, 200)
        self.assertEqual(lesson.context['day'], self.exact_day1)
        self.assertEqual(list(lesson.context['questions']), [self.exact_question])
        self.assertContains(lesson, 'Question for three to five years experience')
        self.assertNotContains(lesson, 'General Day 1 question')

        notes = self.client.post(reverse('careers:level_complete_notes', args=[
            self.role.slug, LEVEL_EXPERIENCED, 1]))
        self.assertEqual(notes.status_code, 302)
        result = self.client.post(self.exact_day1.get_absolute_url(), {
            f'q_{self.exact_question.pk}': self.exact_options[0].pk,
        })
        self.assertEqual(result.status_code, 302)
        current_attempt = DayAttempt.objects.get(user=self.user, day=self.exact_day1)
        self.assertEqual(current_attempt.answers.get().question, self.exact_question)

        legacy_progress.refresh_from_db()
        legacy_attempt.refresh_from_db()
        self.assertEqual(legacy_progress.day_id, self.days[1].pk)
        self.assertEqual(legacy_attempt.day_id, self.days[1].pk)
        self.assertTrue(DayProgress.objects.filter(user=self.user, day=self.exact_day1).exists())


@PLAIN_STATIC
class PopulateDay1LessonCommandTests(TestCase):
    """populate_day1_lesson should populate empty fields and never overwrite admin content."""

    @classmethod
    def setUpTestData(cls):
        call_command('seed_careers', verbosity=0)
        cls.role = CareerRole.objects.get(title='Data Analytics')
        cls.day1 = cls.role.days.get(day_number=1)

    def test_command_populates_empty_lesson_body(self):
        # Ensure the field is empty first
        self.day1.lesson_body = ''
        self.day1.save(update_fields=['lesson_body'])
        call_command('populate_day1_lesson', verbosity=0)
        self.day1.refresh_from_db()
        self.assertTrue(bool(self.day1.lesson_body))

    def test_command_does_not_overwrite_admin_content(self):
        self.day1.lesson_body = 'Admin wrote this — do not overwrite'
        self.day1.save(update_fields=['lesson_body'])
        call_command('populate_day1_lesson', verbosity=0)
        self.day1.refresh_from_db()
        self.assertEqual(self.day1.lesson_body, 'Admin wrote this — do not overwrite')

    def test_command_is_idempotent(self):
        call_command('populate_day1_lesson', verbosity=0)
        self.day1.refresh_from_db()
        body_after_first = self.day1.lesson_body
        call_command('populate_day1_lesson', verbosity=0)
        self.day1.refresh_from_db()
        self.assertEqual(self.day1.lesson_body, body_after_first)

    def test_dry_run_makes_no_changes(self):
        self.day1.lesson_body = ''
        self.day1.save(update_fields=['lesson_body'])
        call_command('populate_day1_lesson', '--dry-run', verbosity=0)
        self.day1.refresh_from_db()
        self.assertEqual(self.day1.lesson_body, '')
