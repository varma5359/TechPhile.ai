from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.urls import reverse
from django.utils import timezone
from unfold.sites import UnfoldAdminSite

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


class TechPhileAdminSite(UnfoldAdminSite):
    """Project admin site with permission-aware learning analytics."""

    index_template = 'techphile_admin/index.html'
    site_header = 'TechPhile Administration'
    site_title = 'TechPhile Admin'
    index_title = 'Analytics overview'

    activity_ranges = (7, 30, 90)

    @staticmethod
    def _can_view(request, model):
        return request.user.has_perm(f'{model._meta.app_label}.view_{model._meta.model_name}')

    @staticmethod
    def _changelist_url(model):
        return reverse(f'admin:{model._meta.app_label}_{model._meta.model_name}_changelist')

    @staticmethod
    def _count_card(label, value, description, url=None):
        icons = {
            'Non-staff accounts': 'group',
            'Active learners': 'person_check',
            'Submitted attempts': 'task_alt',
            'Published career roles': 'work',
            'Published learning days': 'calendar_month',
            'Published scenario questions': 'quiz',
            'Completed learning days': 'check_circle',
        }
        return {
            'label': label,
            'value': f'{value:,}',
            'description': description,
            'url': url,
            'icon': icons.get(label, 'monitoring'),
        }

    def _activity_window(self, request):
        try:
            period_days = int(request.GET.get('days', 30))
        except (TypeError, ValueError):
            period_days = 30
        if period_days not in self.activity_ranges:
            period_days = 30

        today = timezone.localdate()
        start_date = today - timedelta(days=period_days - 1)
        current_tz = timezone.get_current_timezone()
        start_at = timezone.make_aware(datetime.combine(start_date, time.min), current_tz)
        end_at = timezone.make_aware(datetime.combine(today + timedelta(days=1), time.min), current_tz)
        return period_days, start_date, start_at, end_at

    def _activity_chart(self, start_date, start_at, end_at):
        by_date = {}
        current_tz = timezone.get_current_timezone()
        for model in (DayAttempt, MilestoneAttempt):
            rows = (
                model.objects.filter(submitted_at__gte=start_at, submitted_at__lt=end_at)
                .annotate(activity_date=TruncDate('submitted_at', tzinfo=current_tz))
                .values('activity_date')
                .annotate(attempt_count=Count('pk'))
            )
            for row in rows:
                by_date[row['activity_date']] = by_date.get(row['activity_date'], 0) + row['attempt_count']

        today = timezone.localdate()
        dates = [start_date + timedelta(days=offset) for offset in range((today - start_date).days + 1)]
        peak = max((by_date.get(day, 0) for day in dates), default=0)
        return [
            {
                'date': day,
                'label': f'{day.strftime("%b")} {day.day}',
                'count': by_date.get(day, 0),
                'height': max(4, round(by_date.get(day, 0) * 100 / peak))
                if peak and by_date.get(day, 0) else 0,
            }
            for day in dates
        ]

    def _dashboard_context(self, request):
        period_days, start_date, start_at, end_at = self._activity_window(request)
        kpis = []
        actions = []
        insights = []
        activity = []
        skill_coverage = []
        publishing_status = []
        has_activity_permissions = (
            self._can_view(request, DayAttempt) and self._can_view(request, MilestoneAttempt)
        )

        user_model = get_user_model()
        if self._can_view(request, user_model):
            kpis.append(self._count_card(
                'Non-staff accounts',
                user_model.objects.filter(is_staff=False).count(),
                'Registered accounts not marked as staff; account roles are not tracked.',
                reverse('admin:auth_user_changelist'),
            ))
            actions.append({'label': 'Manage users', 'url': reverse('admin:auth_user_changelist'), 'group': 'Accounts'})

        if has_activity_permissions:
            active_learners = user_model.objects.filter(is_staff=False).filter(
                Q(career_day_attempts__submitted_at__gte=start_at,
                  career_day_attempts__submitted_at__lt=end_at)
                | Q(career_milestone_attempts__submitted_at__gte=start_at,
                    career_milestone_attempts__submitted_at__lt=end_at)
            ).distinct().count()
            attempts = (
                DayAttempt.objects.filter(submitted_at__gte=start_at, submitted_at__lt=end_at).count()
                + MilestoneAttempt.objects.filter(submitted_at__gte=start_at, submitted_at__lt=end_at).count()
            )
            kpis.extend((
                self._count_card(
                    'Active learners', active_learners,
                    f'Non-staff users with submitted learning activity in the selected {period_days}-day period.',
                ),
                self._count_card(
                    'Submitted attempts', attempts,
                    'Day and milestone submissions in the selected period.',
                ),
            ))
            activity = self._activity_chart(start_date, start_at, end_at)
            actions.extend((
                {'label': 'Review day attempts', 'url': self._changelist_url(DayAttempt), 'group': 'Learner activity'},
                {'label': 'Review milestone attempts', 'url': self._changelist_url(MilestoneAttempt), 'group': 'Learner activity'},
            ))

        if self._can_view(request, CareerRole):
            published_roles = CareerRole.objects.filter(is_published=True).count()
            kpis.append(self._count_card(
                'Published career roles', published_roles,
                'Career roles currently marked as published.',
                f'{self._changelist_url(CareerRole)}?is_published__exact=1',
            ))
            actions.append({'label': 'Manage career roles', 'url': self._changelist_url(CareerRole), 'group': 'Learning content'})

            if self._can_view(request, LearningDay):
                published_days = LearningDay.objects.filter(
                    is_published=True, role__is_published=True,
                ).count()
                draft_days = LearningDay.objects.filter(
                    is_published=False, role__is_published=True,
                ).count()
                total_days = published_days + draft_days
                publishing_status.append({
                    'label': 'Learning days in published roles',
                    'published': published_days,
                    'draft': draft_days,
                    'published_percent': round(published_days * 100 / total_days) if total_days else 0,
                    'draft_percent': round(draft_days * 100 / total_days) if total_days else 0,
                    'total': total_days,
                    'published_url': (
                        f'{self._changelist_url(LearningDay)}?is_published__exact=1'
                        '&role__is_published__exact=1'
                    ),
                    'draft_url': (
                        f'{self._changelist_url(LearningDay)}?is_published__exact=0'
                        '&role__is_published__exact=1'
                    ),
                })
            else:
                published_days = draft_days = 0

            role_draft_count = CareerRole.objects.filter(is_published=False).count()
            publishing_status.append({
                'label': 'Career roles',
                'published': published_roles,
                'draft': role_draft_count,
                'published_percent': round(published_roles * 100 / (published_roles + role_draft_count))
                if published_roles + role_draft_count else 0,
                'draft_percent': round(role_draft_count * 100 / (published_roles + role_draft_count))
                if published_roles + role_draft_count else 0,
                'total': published_roles + role_draft_count,
                'published_url': f'{self._changelist_url(CareerRole)}?is_published__exact=1',
                'draft_url': f'{self._changelist_url(CareerRole)}?is_published__exact=0',
            })

            if self._can_view(request, LearningDay):
                kpis.append(self._count_card(
                    'Published learning days', published_days,
                    'Published days belonging to published career roles.',
                    f'{self._changelist_url(LearningDay)}?is_published__exact=1&role__is_published__exact=1',
                ))
                actions.append({'label': 'Manage learning days', 'url': self._changelist_url(LearningDay), 'group': 'Learning content'})

                empty_roles = CareerRole.objects.filter(is_published=True).annotate(
                    published_day_count=Count('days', filter=Q(days__is_published=True)),
                ).filter(published_day_count=0).order_by('title')[:5]
                for role in empty_roles:
                    insights.append({
                        'title': f'{role.title} has no published learning days',
                        'detail': 'Review whether this published role is ready for learners.',
                        'url': reverse('admin:careers_careerrole_change', args=[role.pk]),
                        'kind': 'review',
                    })

        if self._can_view(request, ScenarioQuestion):
            published_questions = ScenarioQuestion.objects.filter(
                is_published=True,
                day__is_published=True,
                day__role__is_published=True,
            )
            kpis.append(self._count_card(
                'Published scenario questions', published_questions.count(),
                'Questions on published learning days and roles.',
                f'{self._changelist_url(ScenarioQuestion)}?is_published__exact=1&day__is_published__exact=1&day__role__is_published__exact=1',
            ))
            actions.append({'label': 'Manage scenario questions', 'url': self._changelist_url(ScenarioQuestion), 'group': 'Learning content'})

            if self._can_view(request, LearningDay):
                day_question_counts = LearningDay.objects.filter(
                    is_published=True, role__is_published=True,
                ).annotate(
                    published_question_count=Count(
                        'questions', filter=Q(questions__is_published=True),
                    ),
                ).filter(published_question_count=0).select_related('role').order_by('role__title', 'day_number')[:5]
                question_gaps = {}
                for day in day_question_counts:
                    role_gap = question_gaps.setdefault(day.role_id, {
                        'role': day.role,
                        'days': [],
                        'first_day': day,
                    })
                    role_gap['days'].append(day.day_number)
                for gap in question_gaps.values():
                    day_numbers = ', '.join(str(number) for number in gap['days'])
                    insights.append({
                        'title': f"{gap['role'].title}: {len(gap['days'])} published day(s) have no questions",
                        'detail': f'Days {day_numbers}. Review whether they need question coverage.',
                        'url': reverse('admin:careers_learningday_change', args=[gap['first_day'].pk]),
                        'questions_url': (
                            f"{self._changelist_url(ScenarioQuestion)}?day__role__id__exact={gap['role'].pk}"
                        ),
                        'kind': 'review',
                    })

            if self._can_view(request, Skill):
                grouped = list(published_questions.values('skill_id', 'skill__name').annotate(
                    question_count=Count('pk'),
                ).order_by('-question_count', 'skill__name'))
                maximum = max((row['question_count'] for row in grouped), default=0)
                skill_coverage = [
                    {
                        'name': row['skill__name'] or 'Unassigned',
                        'count': row['question_count'],
                        'max_count': maximum,
                        'width': max(3, round(row['question_count'] * 100 / maximum)) if maximum else 0,
                        'url': (
                            f'{self._changelist_url(ScenarioQuestion)}?is_published__exact=1&day__is_published__exact=1&day__role__is_published__exact=1&skill__isnull=True'
                            if row['skill_id'] is None
                            else f'{self._changelist_url(ScenarioQuestion)}?is_published__exact=1&day__is_published__exact=1&day__role__is_published__exact=1&skill__id__exact={row["skill_id"]}'
                        ),
                    }
                    for row in grouped
                ]
                if not any(row['skill_id'] is None for row in grouped):
                    unassigned_count = published_questions.filter(skill__isnull=True).count()
                    if unassigned_count:
                        skill_coverage.append({
                            'name': 'Unassigned',
                            'count': unassigned_count,
                            'max_count': maximum,
                            'width': max(3, round(unassigned_count * 100 / maximum)) if maximum else 100,
                            'url': (
                                f'{self._changelist_url(ScenarioQuestion)}?is_published__exact=1'
                                '&day__is_published__exact=1&day__role__is_published__exact=1&skill__isnull=True'
                            ),
                        })
                uncovered_skills = Skill.objects.annotate(
                    published_question_count=Count(
                        'questions',
                        filter=Q(
                            questions__is_published=True,
                            questions__day__is_published=True,
                            questions__day__role__is_published=True,
                        ),
                    ),
                ).filter(published_question_count=0).order_by('name')[:5]
                for skill in uncovered_skills:
                    insights.append({
                        'title': f'{skill.name} has no published question coverage',
                        'detail': 'Review this skill tag or add published questions that use it.',
                        'url': reverse('admin:careers_skill_change', args=[skill.pk]),
                        'kind': 'suggestion',
                    })

                all_skill_counts = list(Skill.objects.annotate(
                    published_question_count=Count(
                        'questions',
                        filter=Q(
                            questions__is_published=True,
                            questions__day__is_published=True,
                            questions__day__role__is_published=True,
                        ),
                    ),
                ).order_by('published_question_count', 'name'))
                all_skill_max = max(
                    (skill.published_question_count for skill in all_skill_counts),
                    default=0,
                )
                skill_coverage_preview = [{
                    'name': skill.name,
                    'count': skill.published_question_count,
                    'width': (
                        max(4, round(skill.published_question_count * 100 / all_skill_max))
                        if all_skill_max else 0
                    ),
                    'url': self._changelist_url(ScenarioQuestion) + (
                        '?is_published__exact=1&day__is_published__exact=1'
                        f'&day__role__is_published__exact=1&skill__id__exact={skill.pk}'
                    ),
                } for skill in all_skill_counts[:7]]
                skill_count = len(all_skill_counts)
                one_question_skill_count = sum(
                    skill.published_question_count == 1 for skill in all_skill_counts
                )
                if one_question_skill_count:
                    insights.append({
                        'title': f'{one_question_skill_count} skills have only one published question',
                        'detail': 'Consider adding varied practice for these skills.',
                        'url': self._changelist_url(Skill),
                        'kind': 'suggestion',
                    })
            else:
                skill_coverage_preview = []
                skill_count = one_question_skill_count = 0
        else:
            skill_coverage_preview = []
            skill_count = one_question_skill_count = 0

        if self._can_view(request, Skill):
            actions.append({'label': 'Manage skills', 'url': self._changelist_url(Skill), 'group': 'Learning content'})
        if self._can_view(request, MilestoneExam):
            actions.append({'label': 'Manage milestones', 'url': self._changelist_url(MilestoneExam), 'group': 'Learning content'})
        if self._can_view(request, DayProgress):
            kpis.append(self._count_card(
                'Completed learning days',
                DayProgress.objects.filter(
                    notes_completed=True,
                    status__in=DayProgress.SUBMITTED_STATUSES,
                ).count(),
                'Completed per the submitted-status and notes rule.',
                self._changelist_url(DayProgress),
            ))
            actions.append({'label': 'View learner progress', 'url': self._changelist_url(DayProgress), 'group': 'Learner activity'})

        action_groups = [
            {'name': group, 'actions': [action for action in actions if action['group'] == group]}
            for group in ('Learning content', 'Learner activity', 'Accounts')
            if any(action['group'] == group for action in actions)
        ]
        quick_action_names = (
            ('Manage career roles', 'Career roles', 'Manage'),
            ('Manage learning days', 'Learning days', 'Manage'),
            ('Manage scenario questions', 'Scenario questions', 'Manage'),
            ('Manage skills', 'Skills', 'Manage'),
            ('Manage milestones', 'Milestones', 'Manage'),
            ('Review day attempts', 'Day attempts', 'Review'),
            ('View learner progress', 'Learner progress', 'View'),
            ('Manage users', 'Users', 'Manage'),
        )
        quick_actions_by_label = {action['label']: action for action in actions}
        dashboard_quick_actions = [
            {
                **quick_actions_by_label[label],
                'title': title,
                'verb': verb,
            }
            for label, title, verb in quick_action_names
            if label in quick_actions_by_label
        ]
        today = timezone.localdate()
        activity_peak = max((point['count'] for point in activity), default=0)
        prioritized_insights = sorted(
            insights,
            key=lambda insight: (
                0 if 'only one published question' in insight['title'] else
                1 if 'have no questions' in insight['title'] else 2,
                insight['title'],
            ),
        )

        return {
            'dashboard_description': 'A live overview of career learning content and learner activity.',
            'dashboard_kpis': kpis,
            'dashboard_actions': actions,
            'dashboard_action_groups': action_groups,
            'dashboard_quick_actions': dashboard_quick_actions,
            'dashboard_primary_kpis': [
                item for label in (
                    'Non-staff accounts', 'Active learners',
                    'Published scenario questions', 'Submitted attempts',
                    'Published career roles', 'Completed learning days',
                )
                for item in kpis if item['label'] == label
            ],
            'dashboard_insights': prioritized_insights[:3],
            'activity_ranges': self.activity_ranges,
            'selected_activity_range': period_days,
            'activity_date_range': f'{start_date.strftime("%b")} {start_date.day} to {today.strftime("%b")} {today.day}, {today.year}',
            'activity_timezone': timezone.get_current_timezone_name(),
            'activity_chart': activity,
            'activity_chart_data': {
                'labels': [point['label'] for point in activity],
                'full_labels': [
                    f"{point['date'].strftime('%A, %B')} {point['date'].day}, {point['date'].year}"
                    for point in activity
                ],
                'datasets': [{
                    'label': 'Submitted day and milestone attempts',
                    'data': [point['count'] for point in activity],
                }],
            },
            'activity_total': sum(point['count'] for point in activity),
            'activity_peak': activity_peak,
            'activity_midpoint': (activity_peak + 1) // 2,
            'has_activity_chart': bool(activity) and has_activity_permissions,
            'can_view_skill_coverage': (
                self._can_view(request, ScenarioQuestion) and self._can_view(request, Skill)
            ),
            'can_view_content_insights': (
                (self._can_view(request, CareerRole) and self._can_view(request, LearningDay))
                or (self._can_view(request, ScenarioQuestion) and self._can_view(request, LearningDay))
                or (self._can_view(request, ScenarioQuestion) and self._can_view(request, Skill))
            ),
            'publishing_status': publishing_status,
            'skill_coverage': skill_coverage,
            'skill_coverage_preview': skill_coverage_preview,
            'skill_total': skill_count,
            'skills_with_one_question': one_question_skill_count,
        }

    def index(self, request, extra_context=None):
        context = self._dashboard_context(request)
        # The overview is a dashboard rather than a record form. Use the whole
        # main column so its charts and content grids remain useful on desktop.
        context['is_fullwidth'] = '1'
        if extra_context:
            context.update(extra_context)
        return super().index(request, extra_context=context)
