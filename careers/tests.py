from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import resolve, reverse

from .models import (
    CareerRole, DayAttempt, DayProgress, LearningDay, MilestoneAttempt, MilestoneExam,
    MilestoneQuestion, QuestionOption, ScenarioQuestion, Skill,
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

    def submit(self, day_number, correct=(True, True)):
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
        data = self.answers(1, correct=(True, False))
        data['score'] = '100'
        data['status'] = 'completed'
        response = self.client.post(self.days[1].get_absolute_url(), data)
        attempt = DayAttempt.objects.get(user=self.user, day=self.days[1])
        self.assertRedirects(response, reverse('careers:day_result', args=[self.role.slug, 1, attempt.pk]))
        self.assertEqual(attempt.score_percent, 50.0)
        self.assertEqual(attempt.answers.filter(is_correct=True).count(), 1)

    def test_all_questions_must_be_answered(self):
        data = self.answers(1)
        data.pop(next(iter(data)))
        response = self.client.post(self.days[1].get_absolute_url(), data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'unanswered')
        self.assertEqual(DayAttempt.objects.count(), 0)

    def test_option_from_another_question_is_rejected(self):
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
        self.assertRedirects(response, self.role.get_absolute_url(), fetch_redirect_response=False)
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
        rec = services.recommend(self.user, self.role)
        self.assertEqual([d.day_number for d in rec['revision_days']], [1, 2])
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
        self.assertRedirects(response, self.role.get_absolute_url(), fetch_redirect_response=False)
        for n in range(1, 6):
            self.submit(n)
        self.assertEqual(self.client.get(self.m1.get_absolute_url()).status_code, 200)

    def test_milestone_scoring_and_persistence(self):
        for n in range(1, 6):
            self.submit(n)
        data = {}
        for i, question in enumerate(self.m1.get_questions()):
            options = list(question.options.all())
            pick = next(o for o in options if o.is_correct) if i < 6 else next(o for o in options if not o.is_correct)
            data[f'q_{question.pk}'] = pick.pk
        response = self.client.post(self.m1.get_absolute_url(), data)
        attempt = MilestoneAttempt.objects.get(user=self.user, milestone=self.m1)
        self.assertRedirects(response, reverse('careers:milestone_result', args=[self.role.slug, 1, attempt.pk]))
        self.assertEqual(attempt.total_marks, 10)
        self.assertEqual(attempt.correct_marks, 6)
        self.assertEqual(attempt.score_percent, 60.0)
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
    """The coding and interview entry points are hidden by configuration only."""

    def test_entry_points_hidden_by_default(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse('home_page_coding'))
        self.assertNotContains(response, reverse('exams:mock_interview_form'))
        self.assertContains(response, reverse('careers:role_list'))

    @override_settings(FEATURE_FLAGS={'coding': True, 'mock_interviews': True})
    def test_flags_restore_entry_points(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, reverse('home_page_coding'))
        self.assertContains(response, reverse('exams:mock_interview_form'))

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
                         'Quick revision', 'Check your understanding', 'Q1', 'Q2'):
            self.assertIn(expected, html)
        self.assertGreaterEqual(html.count('<figure class="lx-figure">'), 2)

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
        self.assertIsNone(response.context['lesson'])
        self.assertNotContains(response, 'lx-header')

    def test_feedback_after_submission_teaches_every_option(self):
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
        data = {f'q_{q.pk}': q.options.get(is_correct=True).pk for q in self.day1.questions.all()}
        self.client.post(self.day1.get_absolute_url(), data)
        response = self.client.get(self.day1.get_absolute_url())
        self.assertTrue(response.context['next_unlocked'])

    def test_lesson_text_is_escaped(self):
        self.day1.lesson = {'intro': '<script>alert(1)</script> **bold**'}
        self.day1.save()
        html = self.client.get(self.day1.get_absolute_url()).content.decode()
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn('<strong>bold</strong>', html)

    def test_seed_keeps_admin_edited_lesson(self):
        self.day1.lesson = {'intro': 'Edited by admin'}
        self.day1.save()
        call_command('seed_careers', verbosity=0)
        self.day1.refresh_from_db()
        self.assertEqual(self.day1.lesson, {'intro': 'Edited by admin'})
