"""Student-facing views for the career preparation feature.

Every view requires login. Students only ever see their own progress and
attempts, and only published roles and days are reachable.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from . import services
from .models import CareerRole, DayAttempt, DayProgress, MilestoneAttempt


def _published_role(slug):
    return get_object_or_404(CareerRole, slug=slug, is_published=True)


@login_required
def role_list(request):
    """List published career roles with the student's real progress."""
    roles = CareerRole.objects.filter(is_published=True).annotate(
        published_day_count=Count('days', filter=Q(days__is_published=True), distinct=True))
    submitted = dict(
        DayProgress.objects.filter(
            user=request.user, status__in=DayProgress.SUBMITTED_STATUSES, day__is_published=True,
        ).values_list('day__role_id').annotate(n=Count('id')))
    cards = []
    for role in roles:
        done = submitted.get(role.pk, 0)
        total = role.published_day_count
        cards.append({
            'role': role,
            'done': done,
            'total': total,
            'percent': round(done * 100 / total) if total else 0,
        })
    return render(request, 'careers/role_list.html', {'cards': cards})


@login_required
def role_detail(request, slug):
    """Role overview: syllabus, day plan, milestones, progress, next step."""
    role = _published_role(slug)
    rows = services.plan_overview(request.user, role)
    recommendation = services.recommend(request.user, role, rows)
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
        'rows': rows,
        'unanchored_milestones': unanchored,
        'summary': services.role_summary(request.user, role, rows),
        'recommendation': recommendation,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def day_detail(request, slug, day_number):
    """Show a day's questions (GET) or score a submission (POST)."""
    role = _published_role(slug)
    day = get_object_or_404(role.days.filter(is_published=True), day_number=day_number)
    days = list(services.published_days(role))
    progress = services.progress_map(request.user, role)
    if not services.is_day_unlocked(role, day, days, progress):
        messages.warning(request, 'Finish the previous day to unlock this one.')
        return redirect(role)

    questions = services.day_questions(day)
    posted = request.POST if request.method == 'POST' else {}
    for question in questions:
        question.selected_id = posted.get(f'q_{question.pk}', '')
    if request.method == 'POST':
        try:
            attempt, _ = services.submit_day(request.user, day, request.POST)
        except services.SubmissionError as exc:
            messages.error(request, str(exc))
        else:
            return redirect('careers:day_result', slug=role.slug, day_number=day.day_number,
                            attempt_id=attempt.pk)
    elif questions:
        # Opening a day marks it in progress only; it never completes it.
        DayProgress.objects.get_or_create(user=request.user, day=day)

    return render(request, 'careers/day_detail.html', {
        'role': role,
        'day': day,
        'questions': questions,
        'progress': progress.get(day.pk),
        **_day_navigation(request.user, role, day, days, progress),
    })


def _day_navigation(user, role, day, days, progress):
    """Previous/next day, whether the next one is unlocked, and role progress."""
    position = next(i for i, d in enumerate(days) if d.pk == day.pk)
    previous_day = days[position - 1] if position > 0 else None
    next_day = days[position + 1] if position + 1 < len(days) else None
    return {
        'previous_day': previous_day,
        'next_day': next_day,
        'next_unlocked': bool(next_day) and services.is_day_unlocked(role, next_day, days, progress),
        'role_summary': services.role_summary(user, role),
        'lesson': day.has_lesson,
    }


@login_required
def day_result(request, slug, day_number, attempt_id):
    """Result of one of the student's own day attempts."""
    role = _published_role(slug)
    attempt = get_object_or_404(
        DayAttempt.objects.select_related('day'), pk=attempt_id, user=request.user,
        day__role=role, day__day_number=day_number)
    answers = list(attempt.answers.select_related('question__skill', 'selected_option')
                   .prefetch_related('question__options'))
    breakdown = services.skill_breakdown(answers)
    strengths, weak = services.split_strengths(breakdown, role.pass_percent)
    rows = services.plan_overview(request.user, role)
    return render(request, 'careers/day_result.html', {
        'role': role,
        'day': attempt.day,
        'attempt': attempt,
        'answers': answers,
        'strengths': strengths,
        'weak': weak,
        'solid': attempt.score_percent >= role.pass_percent,
        'recommendation': services.recommend(request.user, role, rows),
        'history': DayAttempt.objects.filter(user=request.user, day=attempt.day)[:10],
    })


@login_required
@require_http_methods(['GET', 'POST'])
def milestone_detail(request, slug, number):
    """Show a milestone exam (GET) or score a submission (POST)."""
    role = _published_role(slug)
    milestone = get_object_or_404(role.milestones.filter(is_published=True), number=number)
    status = services.milestone_status(request.user, milestone)
    if not status['available']:
        messages.warning(request, status['reason'])
        return redirect(role)

    questions = milestone.get_questions()
    posted = request.POST if request.method == 'POST' else {}
    for question in questions:
        question.selected_id = posted.get(f'q_{question.pk}', '')
    if request.method == 'POST':
        try:
            attempt, _ = services.submit_milestone(request.user, milestone, request.POST)
        except services.SubmissionError as exc:
            messages.error(request, str(exc))
        else:
            return redirect('careers:milestone_result', slug=role.slug, number=milestone.number,
                            attempt_id=attempt.pk)
    return render(request, 'careers/milestone_detail.html', {
        'role': role,
        'milestone': milestone,
        'questions': questions,
        'status': status,
    })


@login_required
def milestone_result(request, slug, number, attempt_id):
    """Result of one of the student's own milestone attempts."""
    role = _published_role(slug)
    attempt = get_object_or_404(
        MilestoneAttempt.objects.select_related('milestone'), pk=attempt_id, user=request.user,
        milestone__role=role, milestone__number=number)
    answers = list(attempt.answers.select_related('question__skill', 'question__day', 'selected_option')
                   .prefetch_related('question__options'))
    breakdown = services.skill_breakdown(answers)
    strengths, weak = services.split_strengths(breakdown, role.pass_percent)
    revision_days = []
    for item in weak[:3]:
        revision_days.extend(
            d for d in role.days.filter(
                is_published=True, questions__skill__name=item['skill'],
                day_number__gte=attempt.milestone.start_day, day_number__lte=attempt.milestone.end_day,
            ).distinct().order_by('day_number')[:2])
    seen, unique_days = set(), []
    for day in revision_days:
        if day.pk not in seen:
            seen.add(day.pk)
            unique_days.append(day)
    next_milestone = role.milestones.filter(is_published=True, number__gt=attempt.milestone.number).first()
    return render(request, 'careers/milestone_result.html', {
        'role': role,
        'milestone': attempt.milestone,
        'attempt': attempt,
        'answers': answers,
        'strengths': strengths,
        'weak': weak,
        'solid': attempt.score_percent >= role.pass_percent,
        'revision_days': unique_days,
        'next_milestone': next_milestone,
        'history': MilestoneAttempt.objects.filter(user=request.user, milestone=attempt.milestone)[:10],
    })
