"""Business rules for career preparation: scoring, progress and recommendations.

All scores, completion flags and unlock decisions are computed on the server
from stored data. Nothing here trusts values sent by the browser, other than
the selected option ids, which are validated against the question.
"""
from collections import defaultdict
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from .models import (
    CareerRole, DayAnswer, DayAttempt, DayProgress, LearningDay, MilestoneAnswer,
    MilestoneAttempt,
)

DUPLICATE_SUBMIT_WINDOW = timedelta(seconds=5)

READINESS_LEVELS = [
    (90, 'Interview ready'),
    (75, 'Proficient'),
    (50, 'Developing'),
    (0, 'Foundation building'),
]


class SubmissionError(Exception):
    """Raised when submitted answers are incomplete or invalid."""


def published_days(role):
    """Published learning days of a role, in plan order."""
    return role.days.filter(is_published=True).order_by('day_number')


def day_questions(day):
    """Published questions of a day with their options prefetched."""
    return list(day.questions.filter(is_published=True).select_related('skill').prefetch_related('options'))


def progress_map(user, role):
    """Return ``{day_id: DayProgress}`` for the user within a role."""
    return {p.day_id: p for p in DayProgress.objects.filter(user=user, day__role=role)}


def is_day_unlocked(role, day, days, progress):
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
    previous = progress.get(days[index - 1].pk)
    if previous is None or not previous.is_submitted:
        return False
    if role.unlock_policy == CareerRole.UNLOCK_MIN_SCORE:
        return (previous.best_score or 0) >= role.pass_percent
    return True


def plan_overview(user, role):
    """Day list for the role page with status and lock state for the student."""
    days = list(published_days(role).annotate(
        question_total=Count('questions', filter=Q(questions__is_published=True))))
    progress = progress_map(user, role)
    rows = []
    for day in days:
        entry = progress.get(day.pk)
        rows.append({
            'day': day,
            'progress': entry,
            'status': entry.status if entry else 'not_started',
            'status_label': entry.get_status_display() if entry else 'Not started',
            'unlocked': is_day_unlocked(role, day, days, progress),
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
def submit_day(user, day, data):
    """Score a day submission, store it and update progress.

    Returns ``(attempt, created)``. A repeated identical submission within a
    few seconds (double click) returns the existing attempt instead of
    creating another.
    """
    questions = day_questions(day)
    if not questions:
        raise SubmissionError('This day has no questions yet.')
    selection = _parse_selection(questions, data)

    progress, _ = DayProgress.objects.select_for_update().get_or_create(user=user, day=day)
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
def submit_milestone(user, milestone, data):
    """Score a milestone submission and store the attempt and answers."""
    questions = milestone.get_questions()
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


def _latest_attempt_ids(user, role):
    seen, ids = set(), []
    for pk, day_id in DayAttempt.objects.filter(user=user, day__role=role).order_by(
            '-submitted_at').values_list('pk', 'day_id'):
        if day_id not in seen:
            seen.add(day_id)
            ids.append(pk)
    return ids


def role_weak_skills(user, role, limit=3):
    """Weakest skills from each day's latest attempt, below the role pass mark."""
    ids = _latest_attempt_ids(user, role)
    if not ids:
        return []
    answers = DayAnswer.objects.filter(attempt_id__in=ids).select_related('question__skill')
    weak = [r for r in skill_breakdown(answers) if r['percent'] < role.pass_percent]
    return weak[:limit]


def milestone_status(user, milestone, days=None, progress=None):
    """Availability and best result of a milestone for the student."""
    role = milestone.role
    days = days if days is not None else list(published_days(role))
    progress = progress if progress is not None else progress_map(user, role)
    covered = [d for d in days if milestone.start_day <= d.day_number <= milestone.end_day]
    submitted = sum(1 for d in covered if progress.get(d.pk) and progress[d.pk].is_submitted)
    if not covered:
        available, reason = False, 'No published days in this block yet.'
    elif role.unlock_policy == CareerRole.UNLOCK_OPEN or submitted == len(covered):
        available, reason = True, ''
    else:
        available = False
        reason = f'Submit all {len(covered)} days of this block first ({submitted} done).'
    attempts = list(milestone.attempts.filter(user=user))
    best = max((a.score_percent for a in attempts), default=None)
    return {
        'milestone': milestone,
        'available': available,
        'reason': reason,
        'attempts': len(attempts),
        'best_score': best,
        'latest_attempt': attempts[0] if attempts else None,
        'done': bool(attempts),
    }


def recommend(user, role, rows=None):
    """Transparent, rule based next steps for the student.

    Rules: continue with the first open day that has not been submitted, revise
    days flagged for revision and the weakest skills, and take a milestone once
    its whole block is submitted.
    """
    rows = rows if rows is not None else plan_overview(user, role)
    next_row = next((r for r in rows if r['unlocked'] and r['has_questions']
                     and not (r['progress'] and r['progress'].is_submitted)), None)
    revision_days = [r['day'] for r in rows if r['status'] == DayProgress.REVISION][:3]

    weak = role_weak_skills(user, role)
    skill_days = []
    for item in weak:
        days = list(LearningDay.objects.filter(
            role=role, is_published=True, questions__skill__name=item['skill'],
            questions__is_published=True).distinct().order_by('day_number')[:3])
        skill_days.append({**item, 'days': days})

    days = [r['day'] for r in rows]
    progress = {r['day'].pk: r['progress'] for r in rows if r['progress']}
    milestones = [
        milestone_status(user, m, days, progress)
        for m in role.milestones.filter(is_published=True)
    ]
    milestone_due = next((m for m in milestones if m['available'] and not m['done']
                          and all(progress.get(d.pk) and progress[d.pk].is_submitted
                                  for d in days if m['milestone'].start_day <= d.day_number
                                  <= m['milestone'].end_day)), None)
    return {
        'next_day': next_row['day'] if next_row else None,
        'revision_days': revision_days,
        'weak_skills': skill_days,
        'milestone_due': milestone_due,
        'milestones': milestones,
    }
