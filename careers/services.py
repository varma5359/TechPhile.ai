"""Business rules for career preparation: scoring, progress and recommendations.

All scores, completion flags and unlock decisions are computed on the server
from stored data. Nothing here trusts values sent by the browser, other than
the selected option ids, which are validated against the question.
"""
from collections import defaultdict
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import (
    CareerRole, DayAnswer, DayAttempt, DayProgress, LearningDay, MilestoneAnswer,
    MilestoneAttempt, MilestoneExam, DAYS_PER_MILESTONE, MILESTONE_PASS_PERCENT, LEVEL_BEGINNER,
)
from .selection import select_learning_days, select_milestones

DUPLICATE_SUBMIT_WINDOW = timedelta(seconds=5)

READINESS_LEVELS = [
    (90, 'Interview ready'),
    (75, 'Proficient'),
    (50, 'Developing'),
    (0, 'Foundation building'),
]


class SubmissionError(Exception):
    """Raised when submitted answers are incomplete or invalid."""


def published_days(role, level=LEVEL_BEGINNER, experience_band=''):
    """Published, de-duplicated day sequence for a role/path/experience selection."""
    return select_learning_days(role, level, experience_band)


def day_questions(day):
    """Published questions of a day with their options prefetched."""
    return list(day.questions.filter(is_published=True).select_related('skill').prefetch_related('options'))


def progress_map(user, role, level=LEVEL_BEGINNER, experience_band=''):
    """Return progress only for day records selected by this role/path/band."""
    days = published_days(role, level, experience_band)
    return {p.day_id: p for p in DayProgress.objects.filter(
        user=user, day_id__in=[day.pk for day in days])}


@transaction.atomic
def mark_notes_completed(user, day):
    """Record notes completion for a student on a specific learning day."""
    progress, _ = DayProgress.objects.select_for_update().get_or_create(user=user, day=day)
    if not progress.notes_completed:
        progress.notes_completed = True
        progress.notes_completed_at = timezone.now()
        progress.save()
    return progress


def best_milestone_score(user, milestone):
    """Return the student's highest score percent on ``milestone`` across all attempts."""
    scores = MilestoneAttempt.objects.filter(user=user, milestone=milestone).values_list('score_percent', flat=True)
    return max(scores) if scores else None


def previous_milestone_for_day(role, day, experience_band=''):
    """Return the published MilestoneExam for the block immediately before ``day``."""
    block = (day.day_number - 1) // DAYS_PER_MILESTONE + 1
    if block <= 1:
        return None
    prev_block = block - 1
    milestones = select_milestones(role, day.level, experience_band or day.experience_band)
    milestone = next((item for item in milestones if item.number == prev_block), None)
    if milestone is None:
        milestone = next((item for item in sorted(milestones, key=lambda m: m.end_day, reverse=True)
                          if item.end_day <= prev_block * DAYS_PER_MILESTONE), None)
    return milestone


def is_day_unlocked(role, day, days, progress, user=None, experience_band=''):
    """Whether the student may open ``day`` under the role's unlock policy.

    ``days`` is the ordered list of published days and ``progress`` the map
    from :func:`progress_map`.
    """
    if role.unlock_policy == CareerRole.UNLOCK_OPEN:
        return True
    index = next((i for i, d in enumerate(days) if d.pk == day.pk), None)
    if index is None:
        return False
    if index == 0:
        return True

    # Five-day milestone block gating:
    # If the day belongs to block B > 1 (e.g. Day 6 is block 2), the prerequisite milestone
    # must be published and the student's best score must be at least 75%.
    block = (day.day_number - 1) // DAYS_PER_MILESTONE + 1
    if block > 1:
        prev_milestone = previous_milestone_for_day(role, day, experience_band)
        if prev_milestone is None:
            # Prerequisite milestone missing or unpublished
            return False
        if user is None and progress:
            first_entry = next(iter(progress.values()), None)
            if first_entry:
                user = first_entry.user
        if user is None:
            return False
        best = best_milestone_score(user, prev_milestone)
        if best is None or best < MILESTONE_PASS_PERCENT:
            return False

    # Sequential check: previous day notes must be complete and questions submitted
    previous_day = days[index - 1]
    previous = progress.get(previous_day.pk)
    if previous is None or not previous.notes_completed:
        return False

    has_questions = (
        previous_day.question_total > 0
        if hasattr(previous_day, 'question_total')
        else previous_day.questions.filter(is_published=True).exists()
    )
    if has_questions and not previous.is_submitted:
        return False

    if role.unlock_policy == CareerRole.UNLOCK_MIN_SCORE:
        return (previous.best_score or 0) >= role.pass_percent
    return True


def plan_overview(user, role, level=LEVEL_BEGINNER, experience_band=''):
    """Day list for the role page with status and lock state for the student."""
    days = published_days(role, level, experience_band)
    progress = progress_map(user, role, level, experience_band)
    rows = []
    for day in days:
        entry = progress.get(day.pk)
        rows.append({
            'day': day,
            'progress': entry,
            'status': entry.status if entry else 'not_started',
            'status_label': entry.get_status_display() if entry else 'Not started',
            'unlocked': is_day_unlocked(
                role, day, days, progress, user=user, experience_band=experience_band),
            'has_questions': day.question_total > 0,
        })
    return rows


def role_summary(user, role, rows=None):
    """Real progress figures for a role. No fabricated values."""
    rows = rows if rows is not None else plan_overview(user, role)
    total = len(rows)
    submitted = [r for r in rows if r['progress'] and r['progress'].is_submitted]
    scores = [r['progress'].best_score for r in submitted if r['progress'].best_score is not None]
    average = round(sum(scores) / len(scores), 1) if scores else None
    level = None
    if average is not None:
        level = next(label for threshold, label in READINESS_LEVELS if average >= threshold)
    return {
        'total_days': total,
        'submitted_days': len(submitted),
        'in_progress_days': sum(1 for r in rows if r['status'] == DayProgress.IN_PROGRESS),
        'revision_days': sum(1 for r in rows if r['status'] == DayProgress.REVISION),
        'percent': round(len(submitted) * 100 / total) if total else 0,
        'average_score': average,
        'readiness': level,
    }


def _parse_selection(questions, data):
    """Validate posted answers and return ``{question_id: option}``.

    Every question must be answered with one of its own options.
    """
    selection = {}
    missing = []
    for question in questions:
        raw = data.get(f'q_{question.pk}')
        options = {str(o.pk): o for o in question.options.all()}
        if raw is None or raw == '':
            missing.append(question)
        elif raw not in options:
            raise SubmissionError('One of the submitted answers is not valid for its question.')
        else:
            selection[question.pk] = options[raw]
    if missing:
        raise SubmissionError(f'Please answer all questions ({len(missing)} unanswered).')
    return selection


def _grade(questions, selection):
    """Return (rows, correct_marks, total_marks) from validated selections."""
    rows, correct_marks, total_marks = [], 0, 0
    for question in questions:
        option = selection[question.pk]
        correct = bool(option.is_correct)
        total_marks += question.marks
        if correct:
            correct_marks += question.marks
        rows.append((question, option, correct))
    return rows, correct_marks, total_marks


@transaction.atomic
def submit_day(user, day, data, experience_band=''):
    """Score a day submission, store it and update progress.

    Returns ``(attempt, created)``. A repeated identical submission within a
    few seconds (double click) returns the existing attempt instead of
    creating another.
    """
    experience_band = experience_band or day.experience_band
    days = published_days(day.role, day.level, experience_band)
    progress_map_dict = progress_map(user, day.role, day.level, experience_band)
    if not is_day_unlocked(
        day.role, day, days, progress_map_dict, user=user, experience_band=experience_band):
        raise SubmissionError('This day is currently locked.')

    progress, _ = DayProgress.objects.select_for_update().get_or_create(user=user, day=day)
    if not progress.notes_completed:
        raise SubmissionError('Please complete the lesson notes before submitting questions.')

    questions = day_questions(day)
    if not questions:
        raise SubmissionError('This day has no questions yet.')
    selection = _parse_selection(questions, data)

    latest = DayAttempt.objects.filter(user=user, day=day).first()
    if latest and timezone.now() - latest.submitted_at < DUPLICATE_SUBMIT_WINDOW:
        previous = {a.question_id: a.selected_option_id for a in latest.answers.all()}
        if previous == {qid: opt.pk for qid, opt in selection.items()}:
            return latest, False

    rows, correct_marks, total_marks = _grade(questions, selection)
    percent = round(correct_marks * 100 / total_marks, 1) if total_marks else 0
    attempt = DayAttempt.objects.create(
        user=user, day=day, correct_marks=correct_marks, total_marks=total_marks, score_percent=percent)
    DayAnswer.objects.bulk_create([
        DayAnswer(attempt=attempt, question=q, selected_option=opt, is_correct=ok) for q, opt, ok in rows
    ])

    progress.attempts_count += 1
    progress.last_score = percent
    progress.best_score = max(percent, progress.best_score or 0)
    progress.last_attempt_at = attempt.submitted_at
    progress.status = (DayProgress.COMPLETED if progress.best_score >= day.role.pass_percent
                       else DayProgress.REVISION)
    progress.save()
    return attempt, True


@transaction.atomic
def submit_milestone(user, milestone, data, experience_band=''):
    """Score a milestone submission and store the attempt and answers."""
    experience_band = experience_band or milestone.experience_band
    status = milestone_status(user, milestone, experience_band=experience_band)
    if not status['available']:
        raise SubmissionError(status['reason'] or 'This milestone exam is currently locked.')

    questions = milestone.get_questions(experience_band)
    if not questions:
        raise SubmissionError('This milestone has no questions yet.')
    selection = _parse_selection(questions, data)

    latest = MilestoneAttempt.objects.filter(user=user, milestone=milestone).first()
    if latest and timezone.now() - latest.submitted_at < DUPLICATE_SUBMIT_WINDOW:
        previous = {a.question_id: a.selected_option_id for a in latest.answers.all()}
        if previous == {qid: opt.pk for qid, opt in selection.items()}:
            return latest, False

    rows, correct_marks, total_marks = _grade(questions, selection)
    percent = round(correct_marks * 100 / total_marks, 1) if total_marks else 0
    attempt = MilestoneAttempt.objects.create(
        user=user, milestone=milestone, correct_marks=correct_marks,
        total_marks=total_marks, score_percent=percent)
    MilestoneAnswer.objects.bulk_create([
        MilestoneAnswer(attempt=attempt, question=q, selected_option=opt, is_correct=ok) for q, opt, ok in rows
    ])
    return attempt, True


def skill_breakdown(answers):
    """Group answered questions by skill, weakest first.

    ``answers`` are DayAnswer or MilestoneAnswer rows with ``question__skill``
    available.
    """
    buckets = defaultdict(lambda: [0, 0])
    for answer in answers:
        name = answer.question.skill.name if answer.question.skill else 'General'
        buckets[name][1] += 1
        if answer.is_correct:
            buckets[name][0] += 1
    result = [
        {'skill': name, 'correct': c, 'total': t, 'percent': round(c * 100 / t)}
        for name, (c, t) in buckets.items()
    ]
    return sorted(result, key=lambda r: (r['percent'], r['skill']))


def split_strengths(breakdown, pass_percent):
    """Return (strengths, weak_areas) from a skill breakdown."""
    strengths = [r for r in breakdown if r['percent'] >= pass_percent]
    weak = [r for r in breakdown if r['percent'] < pass_percent]
    return strengths, weak


def _latest_attempt_ids(user, role, level=LEVEL_BEGINNER, experience_band=''):
    seen, ids = set(), []
    selected_day_ids = [d.pk for d in published_days(role, level, experience_band)]
    for pk, day_id in DayAttempt.objects.filter(user=user, day_id__in=selected_day_ids).order_by(
            '-submitted_at').values_list('pk', 'day_id'):
        if day_id not in seen:
            seen.add(day_id)
            ids.append(pk)
    return ids


def role_weak_skills(user, role, limit=3, level=LEVEL_BEGINNER, experience_band=''):
    """Weakest skills from each day's latest attempt, below the role pass mark."""
    ids = _latest_attempt_ids(user, role, level, experience_band)
    if not ids:
        return []
    answers = DayAnswer.objects.filter(attempt_id__in=ids).select_related('question__skill')
    weak = [r for r in skill_breakdown(answers) if r['percent'] < role.pass_percent]
    return weak[:limit]


def role_skill_insights(user, role, limit=3, min_answers=3,
                        level=LEVEL_BEGINNER, experience_band=''):
    """Return explainable skill strengths and practice opportunities.

    Uses each selected learning day's latest submitted attempt, and suppresses
    a skill until at least ``min_answers`` recorded answers support a pattern.
    """
    ids = _latest_attempt_ids(user, role, level, experience_band)
    if not ids:
        return {'strengths': [], 'practice': []}
    answers = DayAnswer.objects.filter(attempt_id__in=ids).select_related(
        'question__skill')
    breakdown = [item for item in skill_breakdown(answers)
                 if item['total'] >= min_answers]
    strengths = [item for item in breakdown
                 if item['percent'] >= role.pass_percent]
    practice = [item for item in breakdown
                if item['percent'] < role.pass_percent]
    return {
        'strengths': sorted(strengths, key=lambda item: (-item['percent'], item['skill']))[:limit],
        'practice': practice[:limit],
    }


def milestone_status(user, milestone, days=None, progress=None, experience_band='', attempts=None):
    """Availability and best result of a milestone for the student."""
    role = milestone.role
    experience_band = experience_band or milestone.experience_band
    days = days if days is not None else published_days(role, milestone.level, experience_band)
    progress = progress if progress is not None else progress_map(
        user, role, milestone.level, experience_band)
    covered = [d for d in days if milestone.start_day <= d.day_number <= milestone.end_day]
    completed_days = sum(
        1 for d in covered
        if progress.get(d.pk) and progress[d.pk].notes_completed and progress[d.pk].is_submitted
    )
    if not covered:
        available, reason = False, 'No published days in this block yet.'
    elif role.unlock_policy == CareerRole.UNLOCK_OPEN or completed_days == len(covered):
        available, reason = True, ''
    else:
        available = False
        reason = f'Complete notes and submit questions for all {len(covered)} days of this block first ({completed_days} done).'
    attempts = list(attempts) if attempts is not None else list(
        milestone.attempts.filter(user=user).order_by('-submitted_at'))
    best = max((a.score_percent for a in attempts), default=None)
    passed = best is not None and best >= MILESTONE_PASS_PERCENT
    return {
        'milestone': milestone,
        'available': available,
        'reason': reason,
        'attempts': len(attempts),
        'best_score': best,
        'passed': passed,
        'pass_percent': MILESTONE_PASS_PERCENT,
        'latest_attempt': attempts[0] if attempts else None,
        'done': bool(attempts),
    }


def recommend(user, role, rows=None, level=LEVEL_BEGINNER, experience_band=''):
    """Transparent, rule based next steps for the student.

    Rules: continue with the first open day that has not been submitted, revise
    days flagged for revision and the weakest skills, and take a milestone once
    its whole block is submitted.
    """
    rows = rows if rows is not None else plan_overview(user, role, level, experience_band)
    next_row = next((r for r in rows if r['unlocked'] and r['has_questions']
                     and not (r['progress'] and r['progress'].notes_completed and r['progress'].is_submitted)), None)
    revision_days = [r['day'] for r in rows if r['status'] == DayProgress.REVISION][:3]

    skill_insights = role_skill_insights(
        user, role, level=level, experience_band=experience_band)
    skill_days = []
    for item in skill_insights['practice']:
        days = list(LearningDay.objects.filter(
            pk__in=[d.pk for d in published_days(role, level, experience_band)],
            questions__skill__name=item['skill'],
            questions__is_published=True).distinct().order_by('day_number')[:3])
        skill_days.append({**item, 'days': days})

    days = [r['day'] for r in rows]
    progress = {r['day'].pk: r['progress'] for r in rows if r['progress']}
    selected_milestones = select_milestones(role, level, experience_band)
    attempts_by_milestone = defaultdict(list)
    if selected_milestones:
        for attempt in MilestoneAttempt.objects.filter(
                user=user, milestone_id__in=[m.pk for m in selected_milestones]
        ).order_by('-submitted_at'):
            attempts_by_milestone[attempt.milestone_id].append(attempt)
    milestones = [milestone_status(
        user, milestone, days, progress, experience_band,
        attempts=attempts_by_milestone[milestone.pk],
    ) for milestone in selected_milestones]
    milestone_due = next((m for m in milestones if m['available'] and not m['passed']
                          and all(progress.get(d.pk) and progress[d.pk].notes_completed and progress[d.pk].is_submitted
                                  for d in days if m['milestone'].start_day <= d.day_number
                                  <= m['milestone'].end_day)), None)
    return {
        'next_day': next_row['day'] if next_row else None,
        'revision_days': revision_days,
        'weak_skills': skill_days,
        'skill_insights': skill_insights,
        'milestone_due': milestone_due,
        'milestones': milestones,
    }
