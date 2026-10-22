from datetime import timedelta
from unittest.mock import patch

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from careers.models import (
    CareerRole,
    DayAttempt,
    DayProgress,
    LearningDay,
    MilestoneAttempt,
    MilestoneExam,
    ScenarioQuestion,
    Skill,
)
from techphile_exams.settings import show_debug_toolbar


class AdminDebugToolbarVisibilityTests(TestCase):
    def test_debug_toolbar_is_hidden_on_admin_but_remains_available_elsewhere(self):
        request_factory = RequestFactory()
        with patch('debug_toolbar.middleware.show_toolbar', return_value=True):
            self.assertFalse(show_debug_toolbar(request_factory.get('/admin/')))
            self.assertFalse(show_debug_toolbar(request_factory.get('/admin/careers/')))
            self.assertTrue(show_debug_toolbar(request_factory.get('/')))


class TechPhileAdminDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = get_user_model().objects.create_superuser(
            username='dashboard-admin',
            email='dashboard-admin@example.com',
            password='safe-test-password',
        )
        cls.learner = get_user_model().objects.create_user(
            username='dashboard-learner', email='dashboard-learner@example.com', password='safe-test-password',
        )
        cls.role = CareerRole.objects.create(
            title='Dashboard Analytics', summary='Practice analytics.', is_published=True,
        )
        cls.empty_role = CareerRole.objects.create(
            title='Dashboard Empty Track', summary='Track awaiting content.', is_published=True,
        )
        CareerRole.objects.create(
            title='Dashboard Draft Track', summary='Draft track.', is_published=False,
        )
        cls.covered_day = LearningDay.objects.create(
            role=cls.role, day_number=1, title='Metrics', is_published=True,
        )
        cls.uncovered_day = LearningDay.objects.create(
            role=cls.role, day_number=2, title='Reporting', is_published=True,
        )
        cls.draft_day = LearningDay.objects.create(
            role=cls.role, day_number=3, title='Draft reporting', is_published=False,
        )
        cls.skill = Skill.objects.create(name='Dashboard SQL')
        cls.unused_skill = Skill.objects.create(name='Dashboard Unused Skill')
        cls.question = ScenarioQuestion.objects.create(
            day=cls.covered_day, skill=cls.skill, text='How do you validate a metric?', is_published=True,
        )
        ScenarioQuestion.objects.create(
            day=cls.covered_day, text='How do you handle unassigned topics?', is_published=True,
        )
        cls.day_attempt = DayAttempt.objects.create(
            user=cls.learner, day=cls.covered_day, correct_marks=1, total_marks=1, score_percent=100,
        )
        cls.milestone = MilestoneExam.objects.create(
            role=cls.role, number=1, start_day=1, end_day=5, is_published=True,
        )
        cls.milestone_attempt = MilestoneAttempt.objects.create(
            user=cls.learner, milestone=cls.milestone,
            correct_marks=1, total_marks=1, score_percent=100,
        )
        DayProgress.objects.create(
            user=cls.learner, day=cls.covered_day,
            notes_completed=True, status=DayProgress.COMPLETED,
        )

    def test_admin_index_shows_dashboard_shell_and_existing_app_navigation(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse('admin:index'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['is_fullwidth'], '1')
        self.assertContains(response, 'Analytics overview')
        self.assertContains(response, 'Career &amp; Learning Content')
        self.assertContains(response, 'Career roles')
        self.assertContains(response, 'Learners &amp; Progress')
        self.assertContains(response, 'nav-sidebar')
        self.assertNotContains(response, 'id="recent-actions-module"')
        self.assertContains(response, 'id="tp-activity-chart"')
        self.assertContains(response, 'tp-activity-data')
        self.assertContains(response, 'View daily values')
        self.assertContains(response, 'class="tp-kpi-dot tone-1"')
        for model in (CareerRole, LearningDay, ScenarioQuestion, DayProgress):
            self.assertTrue(admin.site.is_registered(model))

    def test_admin_index_remains_protected(self):
        response = self.client.get(reverse('admin:index'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('admin:login'), response.url)

    def test_dashboard_metrics_charts_and_review_links_use_real_records(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse('admin:index'), {'days': '7'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['selected_activity_range'], 7)
        metrics = {item['label']: item['value'] for item in response.context['dashboard_kpis']}
        self.assertEqual(metrics['Non-staff accounts'], '1')
        self.assertEqual(metrics['Active learners'], '1')
        self.assertEqual(metrics['Submitted attempts'], '2')
        self.assertEqual(metrics['Published career roles'], '2')
        self.assertEqual(metrics['Published learning days'], '2')
        self.assertEqual(metrics['Published scenario questions'], '2')
        self.assertEqual(metrics['Completed learning days'], '1')
        self.assertEqual(response.context['activity_total'], 2)
        self.assertTrue(all(point['label'] for point in response.context['activity_chart']))
        self.assertContains(response, response.context['activity_date_range'])
        publishing = {item['label']: item for item in response.context['publishing_status']}
        self.assertEqual((publishing['Career roles']['published'], publishing['Career roles']['draft']), (2, 1))
        self.assertEqual(
            (publishing['Learning days in published roles']['published'],
             publishing['Learning days in published roles']['draft']),
            (2, 1),
        )
        self.assertIn('Unassigned', [item['name'] for item in response.context['skill_coverage']])
        self.assertEqual(
            {(item['name'], item['count']) for item in response.context['skill_coverage']},
            {('Dashboard SQL', 1), ('Unassigned', 1)},
        )
        self.assertNotContains(response, 'dashboard-learner')
        self.assertContains(response, 'Dashboard Empty Track has no published learning days')
        self.assertContains(response, 'Dashboard Analytics: 1 published day(s) have no questions')
        self.assertIn(
            'Dashboard Unused Skill',
            [item['name'] for item in response.context['skill_coverage_preview']],
        )

        for action in response.context['dashboard_actions']:
            with self.subTest(action=action['label']):
                self.assertEqual(self.client.get(action['url']).status_code, 200)
        for metric in response.context['dashboard_kpis']:
            if metric['url']:
                with self.subTest(metric=metric['label']):
                    self.assertEqual(self.client.get(metric['url']).status_code, 200)
        for item in response.context['skill_coverage']:
            with self.subTest(skill_filter=item['name']):
                self.assertEqual(self.client.get(item['url']).status_code, 200)
        for item in response.context['publishing_status']:
            for target in ('published_url', 'draft_url'):
                with self.subTest(publishing_filter=target, label=item['label']):
                    self.assertEqual(self.client.get(item[target]).status_code, 200)
        for insight in response.context['dashboard_insights']:
            with self.subTest(insight=insight['title']):
                self.assertEqual(self.client.get(insight['url']).status_code, 200)
                if insight.get('questions_url'):
                    questions_response = self.client.get(insight['questions_url'])
                    self.assertEqual(questions_response.status_code, 200)
                    self.assertIn(f'day__role__id__exact={self.role.pk}', insight['questions_url'])

    def test_dashboard_range_defaults_safely_and_empty_activity_has_an_empty_state(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse('admin:index'), {'days': '999'})
        self.assertEqual(response.context['selected_activity_range'], 30)

        DayAttempt.objects.all().delete()
        MilestoneAttempt.objects.all().delete()
        response = self.client.get(reverse('admin:index'), {'days': '7'})

        self.assertEqual(response.context['activity_total'], 0)
        self.assertContains(response, 'No learning attempts were submitted during this period.')

        ScenarioQuestion.objects.all().delete()
        response = self.client.get(reverse('admin:index'))
        self.assertEqual(response.context['skills_with_one_question'], 0)
        self.assertTrue(all(
            skill['count'] == 0 for skill in response.context['skill_coverage_preview']
        ))

    def test_activity_range_filters_attempts_by_submission_date(self):
        old_submission = timezone.now() - timedelta(days=10)
        DayAttempt.objects.filter(pk=self.day_attempt.pk).update(submitted_at=old_submission)
        MilestoneAttempt.objects.filter(pk=self.milestone_attempt.pk).update(submitted_at=old_submission)
        self.client.force_login(self.admin_user)

        short_range = self.client.get(reverse('admin:index'), {'days': '7'})
        long_range = self.client.get(reverse('admin:index'), {'days': '30'})

        short_metrics = {item['label']: item['value'] for item in short_range.context['dashboard_kpis']}
        long_metrics = {item['label']: item['value'] for item in long_range.context['dashboard_kpis']}
        self.assertEqual(short_metrics['Active learners'], '0')
        self.assertEqual(short_metrics['Submitted attempts'], '0')
        self.assertEqual(long_metrics['Active learners'], '1')
        self.assertEqual(long_metrics['Submitted attempts'], '2')

    def test_dashboard_hides_metrics_without_the_matching_model_permissions(self):
        staff_user = get_user_model().objects.create_user(
            username='dashboard-limited-staff', is_staff=True, password='safe-test-password',
        )
        staff_user.user_permissions.add(Permission.objects.get(
            content_type__app_label='auth', codename='view_user',
        ))
        self.client.force_login(staff_user)

        response = self.client.get(reverse('admin:index'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['label'] for item in response.context['dashboard_kpis']], ['Non-staff accounts'])
        self.assertNotContains(response, 'Dashboard Analytics, day 2 has no published questions')

    def test_enhanced_career_admin_lists_render_and_keep_existing_forms_registered(self):
        self.client.force_login(self.admin_user)

        for model in (CareerRole, LearningDay, ScenarioQuestion, Skill):
            with self.subTest(model=model.__name__):
                response = self.client.get(reverse(
                    f'admin:{model._meta.app_label}_{model._meta.model_name}_changelist',
                ))
                self.assertEqual(response.status_code, 200)
                self.assertTrue(admin.site.is_registered(model))

        self.assertEqual(self.client.get(reverse('admin:careers_learningday_add')).status_code, 200)

