"""Permission-aware sidebar groups for the TechPhile admin workspace."""

from django.contrib import admin
from django.urls import NoReverseMatch, reverse


GROUPS = (
    ('Career & Learning Content', {'careers'}),
    ('Learners & Progress', {'accounts', 'auth', 'career_progress'}),
    ('Interview & Payments', {'interview_prep'}),
    ('Coding & Exams', {'coding', 'core', 'exams'}),
    ('System', {'sites', 'authtoken', 'tech'}),
)

MODEL_TITLES = {
    ('auth', 'user'): 'Users',
    ('auth', 'group'): 'Groups & permissions',
    ('sites', 'site'): 'Sites',
    ('authtoken', 'tokenproxy'): 'Auth tokens',
    ('careers', 'dayprogress'): 'Day progress',
    ('careers', 'dayattempt'): 'Day attempts',
    ('careers', 'milestoneattempt'): 'Milestone attempts',
    ('interview_prep', 'preparationset'): 'Preparation sets',
    ('interview_prep', 'premiumorder'): 'Premium orders',
    ('interview_prep', 'paymentsubmission'): 'Payment submissions',
    ('interview_prep', 'paymentreview'): 'Payment reviews',
    ('interview_prep', 'premiumaccessperiod'): 'Premium access periods',
    ('coding', 'userprofile'): 'Coding profiles',
    ('core', 'submissions'): 'Code submissions',
    ('core', 'userprogress'): 'User progress',
    ('exams', 'examattempt'): 'Exam attempts',
    ('exams', 'interviewfeedback'): 'Interview feedback',
    ('tech', 'contact'): 'Contact form submissions',
}


def sidebar_navigation(request):
    """Build navigation from the registered admins so links obey their perms."""
    registered = list(admin.site._registry.items())
    grouped = {title: [] for title, _ in GROUPS}

    for model, model_admin in registered:
        key = (model._meta.app_label, model._meta.model_name)
        app_label = model._meta.app_label
        group_title = next(
            (title for title, labels in GROUPS if app_label in labels),
            'System',
        )
        if key == ('auth', 'group'):
            group_title = 'System'
        elif key[0] == 'exams' and key[1] in {
            'applicant', 'interviewer', 'interviewfeedback',
        }:
            group_title = 'Interview & Payments'
        elif key == ('core', 'userprogress'):
            group_title = 'Learners & Progress'
        permissions = model_admin.get_model_perms(request)
        can_view_list = permissions.get('view') or permissions.get('change')
        if can_view_list:
            url_name = f'admin:{app_label}_{model._meta.model_name}_changelist'
        elif permissions.get('add'):
            url_name = f'admin:{app_label}_{model._meta.model_name}_add'
        else:
            continue
        try:
            url = reverse(url_name)
        except NoReverseMatch:
            continue

        item = {
            'title': MODEL_TITLES.get(key, str(model._meta.verbose_name_plural).title()),
            'icon': 'circle',
            'link': url,
            'permission': lambda current_request, allowed=True: allowed,
        }
        if key == ('careers', 'careerrole'):
            item['badge'] = model.objects.filter(is_published=True).count()
            item['badge_variant'] = 'info'
        elif key == ('careers', 'learningday'):
            item['badge'] = model.objects.filter(
                is_published=True, role__is_published=True,
            ).count()
            item['badge_variant'] = 'info'
        elif key == ('careers', 'scenarioquestion'):
            item['badge'] = model.objects.filter(
                is_published=True,
                day__is_published=True,
                day__role__is_published=True,
            ).count()
            item['badge_variant'] = 'info'
        if key in {
            ('auth', 'user'),
            ('careers', 'dayprogress'),
            ('careers', 'dayattempt'),
            ('careers', 'milestoneattempt'),
        }:
            group_title = 'Learners & Progress'
        if item not in grouped[group_title]:
            grouped[group_title].append(item)

    overview = {
        'title': 'Analytics overview',
        'icon': 'dashboard',
        'link': reverse('admin:index'),
        'permission': lambda current_request: current_request.user.is_staff,
    }
    groups = [{'title': 'Overview', 'items': [overview]}]
    groups.extend(
        {
            'title': title,
            'separator': True,
            'collapsible': True,
            'items': items,
        }
        for title, items in grouped.items()
        if items
    )
    return groups
