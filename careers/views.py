"""Student-facing views for the career preparation feature.

Every view requires login. Students only ever see their own progress and
attempts, and only published roles and days are reachable.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from . import services
from .choices import EXPERIENCE_CHOICES, LEVEL_CHOICES
from .models import (CareerRole, DayAttempt, DayProgress, MilestoneAttempt,
                     LEVEL_BEGINNER)
from .selection import effective_learning_path, select_learning_days, select_milestones
from exams.forms import CareerLearningPreferencesForm


def _published_role(slug):
    return get_object_or_404(CareerRole, slug=slug, is_published=True)


def _level(level):
    if level not in dict(LEVEL_CHOICES):
        from django.http import Http404
        raise Http404('Unknown learning level.')
    return level


def _learner_selection(request, level=None):
    """Resolve the saved experience and path, allowing explicit path URLs to override."""
    profile = getattr(request.user, 'profile', None)
    experience_band = getattr(profile, 'experience_band', '') or ''
    selected_path = level if level is not None else getattr(profile, 'learning_path', '') or ''
    try:
        resolved_path = effective_learning_path(experience_band, selected_path)
    except ValueError as exc:
        raise Http404('Invalid career learning preferences.') from exc
    return _level(resolved_path), experience_band


def _selected_day(role, level, experience_band, day_number):
    """Return the one exact-or-general selected day for this learner."""
    day = next((day for day in select_learning_days(role, level, experience_band)
                if day.day_number == day_number), None)
    if day is None:
        raise Http404('Learning day not found.')
    return day


def _selected_milestone(role, level, experience_band, number):
    """Return the one exact-or-general selected milestone for this learner."""
    milestone = next((milestone for milestone in select_milestones(role, level, experience_band)
                      if milestone.number == number), None)
    if milestone is None:
        raise Http404('Milestone not found.')
    return milestone


@login_required
def dashboard(request):
    """Personal career-preparation overview for the learner's saved path."""
    from exams.models import Profile

    profile, _ = Profile.objects.get_or_create(user=request.user)
    path_form = CareerLearningPreferencesForm(
        request.POST if request.method == 'POST' else None, instance=profile)
    # The profile settings form keeps these choices optional, but a learner
    # entering Career prep for the first time must choose a complete path.
    for field_name in ('career_role', 'experience_band', 'learning_path'):
        path_form.fields[field_name].required = True
    path_form.fields['career_role'].empty_label = 'Please select a career role'
    for field_name, prompt in (
        ('experience_band', 'Please select your experience'),
        ('learning_path', 'Please select a learning path'),
    ):
        choices = path_form.fields[field_name].choices
        path_form.fields[field_name].choices = [('', prompt)] + [
            (value, label) for value, label in choices if value
        ]
    if (request.method == 'GET' and profile.experience_band == 'fresher'
            and not profile.learning_path):
        path_form.initial['learning_path'] = 'beginner'

    if request.method == 'POST':
        if path_form.is_valid():
            selected_profile = path_form.save()
            return redirect('careers:level_role_detail',
                            slug=selected_profile.career_role.slug,
                            level=selected_profile.learning_path)

    role = profile.career_role
    has_complete_selection = bool(
        role and role.is_published and profile.experience_band and profile.learning_path)
    if not has_complete_selection or (request.method == 'POST' and path_form.errors):
        return render(request, 'careers/dashboard.html', {
            'available_roles': CareerRole.objects.filter(is_published=True),
            'dashboard_view': profile.dashboard_view,
            'path_form': path_form,
        })

    level = effective_learning_path(profile.experience_band, profile.learning_path)
    rows = services.plan_overview(
        request.user, role, level, profile.experience_band)
    summary = services.role_summary(request.user, role, rows)
    recommendation = services.recommend(
        request.user, role, rows, level, profile.experience_band)
    skill_insights = recommendation['skill_insights']
    status_counts = {
        'completed': sum(1 for row in rows if row['status'] == DayProgress.COMPLETED),
        'revision': sum(1 for row in rows if row['status'] == DayProgress.REVISION),
        'in_progress': sum(1 for row in rows if row['status'] == DayProgress.IN_PROGRESS),
    }
    status_counts['not_started'] = max(
        summary['total_days'] - sum(status_counts.values()), 0)
    day_ids = [row['day'].pk for row in rows]
    recent_scores = list(DayAttempt.objects.filter(
        user=request.user, day_id__in=day_ids,
    ).select_related('day').order_by('-submitted_at')[:5])
    recent_scores.reverse()
    recent_practice_average = (
        round(sum(attempt.score_percent for attempt in recent_scores) / len(recent_scores), 1)
        if recent_scores else None
    )
    milestones_ready = sum(
        1 for item in recommendation['milestones'] if item['available'] and not item['passed'])

    return render(request, 'careers/dashboard.html', {
        'role': role,
        'dashboard_view': profile.dashboard_view,
        'level': level,
        'level_label': dict(LEVEL_CHOICES).get(level, 'Fresher'),
        'experience_label': dict(EXPERIENCE_CHOICES).get(
            profile.experience_band, 'Any experience'),
        'rows': rows,
        'summary': summary,
        'recommendation': recommendation,
        'skill_insights': skill_insights,
        'status_counts': status_counts,
        'recent_scores': recent_scores,
        'recent_practice_average': recent_practice_average,
        'milestones_ready': milestones_ready,
    })


@login_required
def role_list(request):
    """List published career roles with the student's real progress."""
    roles = CareerRole.objects.filter(is_published=True)
    level, experience_band = _learner_selection(request)
    profile = getattr(request.user, 'profile', None)
    cards = []
    for role in roles:
        paths = []
        for path_level, label in LEVEL_CHOICES:
            selected_days = select_learning_days(role, path_level, experience_band)
            selected_day_ids = [day.pk for day in selected_days]
            total = len(selected_days)
            done = DayProgress.objects.filter(
                user=request.user, day_id__in=selected_day_ids,
                status__in=DayProgress.SUBMITTED_STATUSES,
            ).count()
            paths.append({'level': path_level, 'label': label, 'done': done, 'total': total,
                          'is_selected': path_level == level})
        cards.append({
            'role': role,
            'is_preferred_role': bool(profile and profile.career_role_id == role.pk),
            'paths': paths,
        })
    return render(request, 'careers/role_list.html', {
        'cards': cards,
        'preferred_role': getattr(profile, 'career_role', None),
        'level': level,
        'experience_label': dict(EXPERIENCE_CHOICES).get(experience_band, 'Any experience'),
        'selected_path_label': dict(LEVEL_CHOICES).get(level, 'Fresher'),
        'has_career_preferences': bool(
            profile and (profile.career_role_id or profile.experience_band or profile.learning_path)),
    })


@login_required
def role_detail(request, slug, level=None):
    """Role overview: syllabus, day plan, milestones, progress, next step."""
    role = _published_role(slug)
    level, experience_band = _learner_selection(request, level)
    rows = services.plan_overview(request.user, role, level, experience_band)
    latest_attempts = {}
    for attempt in DayAttempt.objects.filter(
            user=request.user, day_id__in=[row['day'].pk for row in rows]
    ).order_by('-submitted_at'):
        latest_attempts.setdefault(attempt.day_id, attempt)
    for row in rows:
        row['latest_attempt'] = latest_attempts.get(row['day'].pk)
    recommendation = services.recommend(request.user, role, rows, level, experience_band)
    # Show each milestone after the last published day at or before its end day,
    # so it stays visible even when the exact end day is unpublished.
    numbers = [row['day'].day_number for row in rows]
    for row in rows:
        row['milestones'] = []
    unanchored = []
    for item in recommendation['milestones']:
        anchor = max((n for n in numbers if n <= item['milestone'].end_day), default=None)
        if anchor is None:
            unanchored.append(item)
        else:
            next(r for r in rows if r['day'].day_number == anchor)['milestones'].append(item)
    return render(request, 'careers/role_detail.html', {
        'role': role,
        'level': level,
        'level_label': dict(LEVEL_CHOICES).get(level, 'Fresher'),
        'experience_band': experience_band,
        'experience_label': dict(EXPERIENCE_CHOICES).get(experience_band, 'Any experience'),
        'rows': rows,
        'unanchored_milestones': unanchored,
        'summary': services.role_summary(request.user, role, rows),
        'recommendation': recommendation,
    })


@login_required
@require_http_methods(['POST'])
def complete_notes(request, slug, day_number, level=None):
    """Mark the day's lesson notes complete for the authenticated student."""
    role = _published_role(slug)
    level, experience_band = _learner_selection(request, level)
    day = _selected_day(role, level, experience_band, day_number)
    days = list(services.published_days(role, level, experience_band))
    progress = services.progress_map(request.user, role, level, experience_band)
    if not services.is_day_unlocked(role, day, days, progress, user=request.user,
                                    experience_band=experience_band):
        messages.warning(request, 'This day is locked.')
        return redirect('careers:level_role_detail', slug=role.slug, level=level)

    services.mark_notes_completed(request.user, day)
    messages.success(request, f'Day {day.day_number} notes marked complete! You can now check your understanding below.')
    return redirect('careers:level_day_detail', slug=role.slug, level=level, day_number=day.day_number)


@login_required
@require_http_methods(['GET', 'POST'])
def day_detail(request, slug, day_number, level=None):
    """Show a day's questions (GET) or score a submission (POST)."""
    role = _published_role(slug)
    level, experience_band = _learner_selection(request, level)
    day = _selected_day(role, level, experience_band, day_number)
    days = list(services.published_days(role, level, experience_band))
    progress = services.progress_map(request.user, role, level, experience_band)
    if not services.is_day_unlocked(role, day, days, progress, user=request.user,
                                    experience_band=experience_band):
        messages.warning(request, 'Finish the previous day to unlock this one.')
        return redirect('careers:level_role_detail', slug=role.slug, level=level)

    day_progress = progress.get(day.pk)
    questions = services.day_questions(day)
    posted = request.POST if request.method == 'POST' else {}
    for question in questions:
        question.selected_id = posted.get(f'q_{question.pk}', '')

    if request.method == 'POST':
        if not (day_progress and day_progress.notes_completed):
            messages.error(request, 'Please complete the lesson notes before submitting questions.')
        else:
            try:
                attempt, _ = services.submit_day(request.user, day, request.POST, experience_band)
            except services.SubmissionError as exc:
                messages.error(request, str(exc))
            else:
                return redirect('careers:level_day_result', slug=role.slug, level=level,
                                day_number=day.day_number, attempt_id=attempt.pk)
    else:
        # Opening a day marks it in progress only; it never completes notes or questions.
        if day_progress is None:
            day_progress, _ = DayProgress.objects.get_or_create(user=request.user, day=day)
            progress[day.pk] = day_progress

    return render(request, 'careers/day_detail.html', {
        'role': role,
        'level': level,
        'experience_band': experience_band,
        'day': day,
        'questions': questions,
        'progress': day_progress,
        'notes_completed': bool(day_progress and day_progress.notes_completed),
        **_day_navigation(request.user, role, day, days, progress, level, experience_band),
    })


def _day_navigation(user, role, day, days, progress, level=LEVEL_BEGINNER, experience_band=''):
    """Previous/next day, whether the next one is unlocked, and role progress."""
    position = next(i for i, d in enumerate(days) if d.pk == day.pk)
    previous_day = days[position - 1] if position > 0 else None
    next_day = days[position + 1] if position + 1 < len(days) else None
    return {
        'previous_day': previous_day,
        'next_day': next_day,
        'next_unlocked': bool(next_day) and services.is_day_unlocked(
            role, next_day, days, progress, user=user, experience_band=experience_band),
        'role_summary': services.role_summary(
            user, role, services.plan_overview(user, role, level, experience_band)),
        'lesson': day.has_lesson,
    }


@login_required
def day_result(request, slug, day_number, attempt_id, level=None):
    """Result of one of the student's own day attempts."""
    role = _published_role(slug)
    level, experience_band = _learner_selection(request, level)
    attempt = get_object_or_404(
        DayAttempt.objects.select_related('day'), pk=attempt_id, user=request.user,
        day__role=role, day__level=level, day__day_number=day_number, day__is_published=True)
    answers = list(attempt.answers.select_related('question__skill', 'selected_option')
                   .prefetch_related('question__options'))
    breakdown = services.skill_breakdown(answers)
    strengths, weak = services.split_strengths(breakdown, role.pass_percent)
    rows = services.plan_overview(request.user, role, level, experience_band)
    return render(request, 'careers/day_result.html', {
        'role': role,
        'level': level,
        'experience_band': experience_band,
        'day': attempt.day,
        'attempt': attempt,
        'answers': answers,
        'strengths': strengths,
        'weak': weak,
        'solid': attempt.score_percent >= role.pass_percent,
        'recommendation': services.recommend(request.user, role, rows, level, experience_band),
        'history': DayAttempt.objects.filter(user=request.user, day=attempt.day)[:10],
    })


@login_required
@require_http_methods(['GET', 'POST'])
def milestone_detail(request, slug, number, level=None):
    """Show a milestone exam (GET) or score a submission (POST)."""
    role = _published_role(slug)
    level, experience_band = _learner_selection(request, level)
    milestone = _selected_milestone(role, level, experience_band, number)
    status = services.milestone_status(request.user, milestone, experience_band=experience_band)
    if not status['available']:
        messages.warning(request, status['reason'])
        return redirect('careers:level_role_detail', slug=role.slug, level=level)

    questions = milestone.get_questions(experience_band)
    posted = request.POST if request.method == 'POST' else {}
    for question in questions:
        question.selected_id = posted.get(f'q_{question.pk}', '')
    if request.method == 'POST':
        try:
            attempt, _ = services.submit_milestone(request.user, milestone, request.POST, experience_band)
        except services.SubmissionError as exc:
            messages.error(request, str(exc))
        else:
            return redirect('careers:level_milestone_result', slug=role.slug, level=level,
                            number=milestone.number, attempt_id=attempt.pk)
    return render(request, 'careers/milestone_detail.html', {
        'role': role,
        'level': level,
        'experience_band': experience_band,
        'milestone': milestone,
        'questions': questions,
        'status': status,
    })


@login_required
def milestone_result(request, slug, number, attempt_id, level=None):
    """Result of one of the student's own milestone attempts."""
    role = _published_role(slug)
    level, experience_band = _learner_selection(request, level)
    attempt = get_object_or_404(
        MilestoneAttempt.objects.select_related('milestone'), pk=attempt_id, user=request.user,
        milestone__role=role, milestone__level=level, milestone__number=number,
        milestone__is_published=True)
    answers = list(attempt.answers.select_related('question__skill', 'question__day', 'selected_option')
                   .prefetch_related('question__options'))
    breakdown = services.skill_breakdown(answers)
    strengths, weak = services.split_strengths(breakdown, services.MILESTONE_PASS_PERCENT)
    selected_days = services.published_days(role, level, experience_band)
    revision_days = []
    for item in weak[:3]:
        matching_days = [
            day for day in selected_days
            if attempt.milestone.start_day <= day.day_number <= attempt.milestone.end_day
            and day.questions.filter(is_published=True, skill__name=item['skill']).exists()
        ]
        revision_days.extend(matching_days[:2])
    if not revision_days and attempt.score_percent < services.MILESTONE_PASS_PERCENT:
        revision_days.extend(d for d in selected_days
                             if attempt.milestone.start_day <= d.day_number <= attempt.milestone.end_day)
    seen, unique_days = set(), []
    for day in revision_days:
        if day.pk not in seen:
            seen.add(day.pk)
            unique_days.append(day)

    history = list(MilestoneAttempt.objects.filter(user=request.user, milestone=attempt.milestone).order_by('-submitted_at')[:10])
    best_score = max((h.score_percent for h in history), default=attempt.score_percent)
    passed = best_score >= services.MILESTONE_PASS_PERCENT
    next_block_start = attempt.milestone.end_day + 1
    next_block_day = (next((day for day in selected_days if day.day_number == next_block_start), None)
                      if passed else None)
    next_milestone = next((item for item in select_milestones(role, level, experience_band)
                           if item.number > attempt.milestone.number), None)

    return render(request, 'careers/milestone_result.html', {
        'role': role,
        'level': level,
        'experience_band': experience_band,
        'milestone': attempt.milestone,
        'attempt': attempt,
        'answers': answers,
        'strengths': strengths,
        'weak': weak,
        'solid': passed,
        'passed': passed,
        'best_score': best_score,
        'pass_percent': services.MILESTONE_PASS_PERCENT,
        'next_block_day': next_block_day,
        'revision_days': unique_days,
        'next_milestone': next_milestone,
        'history': history,
    })
