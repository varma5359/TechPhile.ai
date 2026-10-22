"""Server-side access checks and persistence for generated preparation sets.

The repository has no resume parser or preparation question generator yet.
The generator must call ``save_generated_preparation_set`` only after it has
created a complete result; this module does not fabricate analysis or questions.
"""

import uuid
from datetime import timedelta

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import PremiumAccessPeriod, PremiumOrder, PreparationSet, SavedQuestion


MONTHLY_PREPARATION_SET_LIMIT = 2


class PremiumPreparationRequired(PermissionDenied):
    """Raised when an account has no approved, currently active monthly access."""


class PreparationSetLimitReached(PermissionDenied):
    """Raised when both preparation sets for the active month already exist."""


def get_active_access_period(user, at=None, lock=False):
    """Return this account's current approved monthly access period, if any."""
    if not user or not user.is_authenticated:
        return None

    at = at or timezone.now()
    allowed_plan_codes = ['premium_monthly']
    if settings.INTERVIEW_PREP_TEST_ACCESS:
        allowed_plan_codes.append('local_test_monthly')

    periods = PremiumAccessPeriod.objects.filter(
        order__user=user,
        order__status=PremiumOrder.Status.APPROVED,
        order__plan_code__in=allowed_plan_codes,
        starts_at__lte=at,
        ends_at__gt=at,
    ).order_by('-ends_at')
    if lock:
        periods = periods.select_for_update()
    period = periods.first()
    if period or not settings.INTERVIEW_PREP_TEST_ACCESS:
        return period

    # Explicit local-only access creates a distinct plan code so it cannot be
    # mistaken for a payment approved by an administrator.
    with transaction.atomic():
        order = PremiumOrder.objects.filter(
            user=user,
            plan_code='local_test_monthly',
            status=PremiumOrder.Status.APPROVED,
        ).order_by('-created_at').first()
        if order is None:
            order = PremiumOrder.objects.create(
                user=user,
                plan_code='local_test_monthly',
                amount=settings.INTERVIEW_PREP_MONTHLY_PRICE,
                currency=settings.INTERVIEW_PREP_CURRENCY,
                status=PremiumOrder.Status.APPROVED,
            )
        period, _ = PremiumAccessPeriod.objects.get_or_create(
            order=order,
            defaults={
                'starts_at': at,
                'ends_at': at + timedelta(days=30),
            },
        )
    if period.starts_at <= at < period.ends_at:
        return period
    return None


def get_preparation_access(user, at=None):
    """Summarize free or active Premium access and the remaining monthly sets."""
    period = get_active_access_period(user, at=at)
    if period is None:
        return {
            'plan': 'free',
            'premium_active': False,
            'access_period': None,
            'sets_used': 0,
            'sets_remaining': 0,
            'set_limit': MONTHLY_PREPARATION_SET_LIMIT,
        }

    used = PreparationSet.objects.filter(access_period=period).count()
    return {
        'plan': 'local_test_monthly' if period.order.plan_code == 'local_test_monthly' else 'premium_monthly',
        'premium_active': True,
        'access_period': period,
        'sets_used': used,
        'sets_remaining': max(0, MONTHLY_PREPARATION_SET_LIMIT - used),
        'set_limit': MONTHLY_PREPARATION_SET_LIMIT,
    }


def save_generated_preparation_set(
    user,
    request_reference,
    company_name,
    job_title,
    job_description,
    generated_content,
    role_family='general-software-engineering',
    seniority='entry',
    input_fingerprint=None,
):
    """Persist completed generator output under active Premium access.

    Callers must create and retain one request reference for a generation
    attempt, then reuse it when retrying persistence. The database uniqueness
    rule makes that retry return the already-created set rather than consume
    another monthly slot.
    """
    if not user or not user.is_authenticated:
        raise PremiumPreparationRequired('Sign in to use Premium preparation.')

    active_period = get_active_access_period(user)
    if active_period is None:
        raise PremiumPreparationRequired('An approved, active monthly plan is required.')

    try:
        request_reference = uuid.UUID(str(request_reference))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValidationError('A valid preparation request reference is required.') from exc

    existing = PreparationSet.objects.filter(
        owner=user,
        request_reference=request_reference,
    ).first()
    if existing is None and input_fingerprint:
        existing = PreparationSet.objects.filter(
            owner=user,
            access_period=active_period,
            input_fingerprint=input_fingerprint,
        ).first()
    if existing:
        if existing.access_period_id != active_period.pk:
            raise PremiumPreparationRequired('This request belongs to a different subscription month.')
        return existing

    company_name = (company_name or '').strip()
    job_title = (job_title or '').strip()
    job_description = (job_description or '').strip()
    if len(company_name or '') > 120:
        raise ValidationError('Company name must be 120 characters or fewer.')
    if not job_title or len(job_title) > 150:
        raise ValidationError('Enter a job title of 1 to 150 characters.')
    if not job_description:
        raise ValidationError('A job description is required.')
    if not isinstance(generated_content, dict):
        raise ValidationError('Complete generated preparation content is required.')
    rounds = generated_content.get('rounds')
    if rounds is not None:
        if not isinstance(rounds, list) or len(rounds) != 2 or any(
            not isinstance(row, dict) or not isinstance(row.get('questions'), list) or len(row['questions']) != 30
            for row in rounds
        ):
            raise ValidationError('A complete preparation needs two rounds of 30 questions.')
        questions = [question for row in rounds for question in row['questions']]
    else:
        # Read old persisted content during the transition; all new pipeline
        # output uses the two-round contract above.
        questions = generated_content.get('questions')
    if not isinstance(questions, list) or not questions:
        raise ValidationError('Complete generated preparation content is required.')
    seen_question_ids = set()
    for question in questions:
        if not isinstance(question, dict):
            raise ValidationError('Each generated question must be an object.')
        question_id = str(question.get('id', '')).strip()
        question_text = question.get('question')
        if not question_id or len(question_id) > 128 or not isinstance(question_text, str) or not question_text.strip():
            raise ValidationError('Each generated question needs a stable ID and question text.')
        if question_id in seen_question_ids:
            raise ValidationError('Generated question IDs must be unique within a set.')
        seen_question_ids.add(question_id)

    try:
        with transaction.atomic():
            period = get_active_access_period(user, lock=True)
            if period is None:
                raise PremiumPreparationRequired('An approved, active monthly plan is required.')

            existing = PreparationSet.objects.filter(
                owner=user,
                request_reference=request_reference,
            ).first()
            if existing:
                if existing.access_period_id != period.pk:
                    raise PremiumPreparationRequired('This request belongs to a different subscription month.')
                return existing

            existing_by_fingerprint = None
            if input_fingerprint:
                existing_by_fingerprint = PreparationSet.objects.filter(
                    owner=user,
                    access_period=period,
                    input_fingerprint=input_fingerprint,
                ).first()
            if existing_by_fingerprint:
                return existing_by_fingerprint

            set_number = PreparationSet.objects.filter(access_period=period).count() + 1
            if set_number > MONTHLY_PREPARATION_SET_LIMIT:
                raise PreparationSetLimitReached('Two preparation sets have already been used this month.')

            return PreparationSet.objects.create(
                owner=user,
                access_period=period,
                request_reference=request_reference,
                set_number=set_number,
                company_name=company_name,
                job_title=job_title,
                role_family=role_family,
                seniority=seniority,
                job_description=job_description,
                input_fingerprint=input_fingerprint,
                generated_content=generated_content,
            )
    except IntegrityError as exc:
        existing = PreparationSet.objects.filter(
            owner=user,
            request_reference=request_reference,
        ).first()
        if existing is None and input_fingerprint:
            existing = PreparationSet.objects.filter(
                owner=user,
                access_period=active_period,
                input_fingerprint=input_fingerprint,
            ).first()
        if existing:
            return existing
        raise PreparationSetLimitReached('The monthly preparation set limit has been reached.') from exc


def _get_owned_active_set(user, preparation_set_id, at=None, lock=False):
    """Load a set only when the owner still has active access to its period."""
    at = at or timezone.now()
    sets = PreparationSet.objects.filter(
        pk=preparation_set_id,
        owner=user,
        access_period__order__status=PremiumOrder.Status.APPROVED,
        access_period__starts_at__lte=at,
        access_period__ends_at__gt=at,
    )
    if lock:
        sets = sets.select_for_update()
    return sets.first()


def _find_question(preparation_set, question_id):
    """Find one question in the stored output without trusting a client snapshot."""
    content = preparation_set.generated_content
    questions = content.get('questions', [])
    questions.extend(
        question
        for question_round in content.get('rounds', [])
        for question in question_round.get('questions', [])
    )
    for question in questions:
        if isinstance(question, dict) and str(question.get('id', '')) == str(question_id):
            return question
    return None


def toggle_saved_question(user, preparation_set_id, question_id):
    """Save or unsave one question after checking set ownership and access."""
    with transaction.atomic():
        preparation_set = _get_owned_active_set(
            user,
            preparation_set_id,
            lock=True,
        )
        if preparation_set is None:
            raise PremiumPreparationRequired('This preparation is unavailable or its access period has ended.')

        question = _find_question(preparation_set, question_id)
        if question is None:
            raise ValidationError('That question is not part of this preparation set.')

        saved, created = SavedQuestion.objects.get_or_create(
            preparation_set=preparation_set,
            question_id=str(question_id),
            defaults={'question_text': str(question.get('question', ''))},
        )
        if not created:
            saved.delete()
            return False
        return True


def mark_question_completed(user, preparation_set_id, question_id, completed=True):
    """Update progress only for a question in the owner's active preparation."""
    with transaction.atomic():
        preparation_set = _get_owned_active_set(
            user,
            preparation_set_id,
            lock=True,
        )
        if preparation_set is None:
            raise PremiumPreparationRequired('This preparation is unavailable or its access period has ended.')

        question = _find_question(preparation_set, question_id)
        if question is None:
            raise ValidationError('That question is not part of this preparation set.')

        completed_ids = list(preparation_set.completed_question_ids or [])
        normalized_id = str(question_id)
        if completed and normalized_id not in completed_ids:
            completed_ids.append(normalized_id)
        elif not completed and normalized_id in completed_ids:
            completed_ids.remove(normalized_id)

        preparation_set.completed_question_ids = completed_ids
        preparation_set.save(update_fields=['completed_question_ids', 'updated_at'])
        return len(completed_ids)


def get_saved_questions(user):
    """Return saved question snapshots belonging to the owner's active plans."""
    now = timezone.now()
    return SavedQuestion.objects.filter(
        preparation_set__owner=user,
        preparation_set__access_period__order__status=PremiumOrder.Status.APPROVED,
        preparation_set__access_period__starts_at__lte=now,
        preparation_set__access_period__ends_at__gt=now,
    ).select_related('preparation_set').order_by('-saved_at')
