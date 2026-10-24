"""Server-side access checks and persistence for preparation drafts and sets."""

import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, models, transaction
from django.utils import timezone

from .intelligence_schema import count_valid_unique_questions
from .role_profiles import SENIORITY_LEVELS, profile_choices

from .models import PremiumAccessPeriod, PremiumOrder, PreparationSet, SavedQuestion, TrialUsage


MONTHLY_PREPARATION_SET_LIMIT = 2
MIN_PREPARATION_QUESTIONS = 30
MAX_PREPARATION_QUESTIONS = 60
DEFAULT_PREPARATION_QUESTIONS = 45
TRIAL_ALLOWANCE = 2
TRIAL_WINDOW = timedelta(days=20)
TRIAL_FEATURE_CODE = 'interview_prep'


class PremiumPreparationRequired(PermissionDenied):
    """Raised when an account has no approved, currently active monthly access."""


class PreparationSetLimitReached(PermissionDenied):
    """Raised when both preparation sets for the active month already exist."""


def get_active_access_period(user, at=None, lock=False):
    """Return this account's active paid or explicitly enabled test period."""
    if not user or not user.is_authenticated:
        return None

    at = at or timezone.now()
    periods = PremiumAccessPeriod.objects.filter(
        order__user=user,
        order__status=PremiumOrder.Status.APPROVED,
        order__plan_code='premium_monthly',
        starts_at__lte=at,
        ends_at__gt=at,
    ).order_by('-ends_at')
    if lock:
        periods = periods.select_for_update()
    period = periods.first()
    if period:
        return period

    # A local test entitlement is still available in development, but it uses
    # the same two-set limit as the normal free preview.
    if settings.INTERVIEW_PREP_TEST_ACCESS:
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
                defaults={'starts_at': at, 'ends_at': at + timedelta(days=36500)},
            )
            if lock:
                period = PremiumAccessPeriod.objects.select_for_update().get(pk=period.pk)
        if period.starts_at <= at < period.ends_at:
            return period

    # No active paid or explicitly enabled local test access exists.
    return None


def historical_trial_period_query(prefix='', at=None):
    """Match only existing preparations on an approved, date-active legacy trial period."""
    at = at or timezone.now()
    return models.Q(**{
        f'{prefix}access_period__order__plan_code': 'free_trial',
        f'{prefix}access_period__order__status': PremiumOrder.Status.APPROVED,
        f'{prefix}access_period__starts_at__lte': at,
        f'{prefix}access_period__ends_at__gt': at,
    })


def get_preparation_access(user, at=None):
    """Summarize free or active Premium access and the remaining monthly sets."""
    period = get_active_access_period(user, at=at)
    if period is None:
        if user and user.is_authenticated and not (user.is_staff or user.is_superuser):
            at = at or timezone.now()
            cutoff = at - TRIAL_WINDOW
            usages = TrialUsage.objects.filter(
                user=user,
                started_at__gt=cutoff,
            )
            used = usages.count()
            remaining = max(0, TRIAL_ALLOWANCE - used)
            oldest = usages.order_by('started_at').values_list('started_at', flat=True).first()
            return {
                'plan': 'free_trial',
                'premium_active': remaining > 0,
                'access_period': None,
                'sets_used': used,
                'sets_completed': used,
                'drafts_reserved': 0,
                'sets_remaining': remaining,
                'slots_available': remaining,
                'unopened_sets': 0,
                'set_limit': TRIAL_ALLOWANCE,
                'is_trial': True,
                'trial_resets_at': oldest + TRIAL_WINDOW if oldest else None,
            }
        return {
            'plan': 'free',
            'premium_active': False,
            'access_period': None,
            'sets_used': 0,
            'sets_completed': 0,
            'drafts_reserved': 0,
            'sets_remaining': 0,
            'slots_available': 0,
            'unopened_sets': 0,
            'set_limit': MONTHLY_PREPARATION_SET_LIMIT,
            'is_trial': False,
            'trial_resets_at': None,
        }

    preparations = list(PreparationSet.objects.filter(access_period=period).only(
        'generated_content', 'completed_question_ids',
    ))
    used = len(preparations)
    drafts_reserved = sum(1 for item in preparations if preparation_is_draft(item))
    is_trial = period.order.plan_code == 'local_test_monthly'
    if is_trial:
        # The DEBUG-only test plan counts durable preparation starts, without the
        # removed browser page-open beacon used by the historical trial flow.
        remaining = max(0, MONTHLY_PREPARATION_SET_LIMIT - used)
        slots_available = remaining
        premium_active = remaining > 0
        unopened_sets = 0
        completed = used - drafts_reserved
    else:
        remaining = max(0, MONTHLY_PREPARATION_SET_LIMIT - used)
        slots_available = remaining
        unopened_sets = 0
        premium_active = True
        completed = used - drafts_reserved
    return {
        'plan': ('local_test_trial' if period.order.plan_code == 'local_test_monthly' else 'free_trial') if is_trial else 'premium_monthly',
        'premium_active': premium_active,
        'access_period': period,
        'sets_used': completed if is_trial else used,
        'sets_completed': completed,
        'drafts_reserved': drafts_reserved,
        'sets_remaining': remaining,
        'slots_available': slots_available,
        'unopened_sets': unopened_sets,
        'set_limit': MONTHLY_PREPARATION_SET_LIMIT,
        'is_trial': is_trial,
        'trial_resets_at': None,
    }


def preparation_is_draft(preparation_set):
    """Whether a preparation row is an incomplete, resumable generation draft."""
    return (preparation_set.generated_content or {}).get('_generation_state') in {
        'in_progress', 'incomplete', 'temporarily_unavailable', 'interrupted',
    }


def create_preparation_draft(
    user, request_reference, company_name, job_title, job_description,
    role_family='general-software-engineering', seniority='entry', input_fingerprint=None,
    target_question_count=DEFAULT_PREPARATION_QUESTIONS,
):
    """Reserve one monthly slot and persist an empty, resumable preparation draft."""
    if not user or not user.is_authenticated:
        raise PremiumPreparationRequired('Sign in to use Premium preparation.')
    try:
        request_reference = uuid.UUID(str(request_reference))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValidationError('A valid preparation request reference is required.') from exc
    if (
        isinstance(target_question_count, bool)
        or not isinstance(target_question_count, int)
        or not MIN_PREPARATION_QUESTIONS <= target_question_count <= MAX_PREPARATION_QUESTIONS
    ):
        raise ValidationError('Choose between 30 and 60 interview questions.')

    with transaction.atomic():
        period = get_active_access_period(user, lock=True)
        if period is None:
            raise PremiumPreparationRequired('An approved, active monthly plan is required.')
        existing = PreparationSet.objects.filter(owner=user, request_reference=request_reference).first()
        if existing:
            if existing.access_period_id != period.pk:
                raise PremiumPreparationRequired('This request belongs to a different subscription month.')
            return existing
        if input_fingerprint:
            existing = PreparationSet.objects.filter(
                owner=user, access_period=period, input_fingerprint=input_fingerprint,
            ).first()
            if existing:
                return existing
        existing_sets = PreparationSet.objects.filter(access_period=period).count()
        if existing_sets >= MONTHLY_PREPARATION_SET_LIMIT:
            raise PreparationSetLimitReached('Two preparation sets have already been used this month.')
        if not job_title or len(job_title) > 150 or not job_description:
            raise ValidationError('A valid job title and job description are required.')
        return PreparationSet.objects.create(
            owner=user,
            access_period=period,
            request_reference=request_reference,
            set_number=existing_sets + 1,
            company_name=(company_name or '').strip(),
            job_title=job_title.strip(),
            role_family=role_family,
            seniority=seniority,
            job_description=job_description.strip(),
            input_fingerprint=input_fingerprint,
            generated_content={
                '_generation_state': 'incomplete',
                '_question_target': target_question_count,
                '_generation_progress': {'completed': 0, 'total': target_question_count},
                'rounds': [],
            },
        )


def start_trial_preparation(
    user, request_reference, request_fingerprint, company_name, job_title,
    job_description, role_family='general-software-engineering', seniority='entry',
    target_question_count=DEFAULT_PREPARATION_QUESTIONS, candidate_profile=None,
):
    """Atomically reserve one rolling-window trial and create its resumable draft."""
    if not user or not user.is_authenticated:
        raise PremiumPreparationRequired('Sign in to use Interview Preparation.')
    if user.is_staff or user.is_superuser:
        raise PremiumPreparationRequired('Free trials are available to student accounts.')
    try:
        request_reference = uuid.UUID(str(request_reference))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValidationError('A valid preparation request reference is required.') from exc
    if not isinstance(request_fingerprint, str) or len(request_fingerprint) != 64:
        raise ValidationError('A valid request fingerprint is required.')
    if (
        isinstance(target_question_count, bool)
        or not isinstance(target_question_count, int)
        or not MIN_PREPARATION_QUESTIONS <= target_question_count <= MAX_PREPARATION_QUESTIONS
    ):
        raise ValidationError('Choose between 30 and 60 interview questions.')
    company_name = (company_name or '').strip()
    job_title = (job_title or '').strip()
    job_description = (job_description or '').strip()
    valid_roles = {value for value, _label in profile_choices()}
    if (
        len(company_name) > 120
        or not job_title
        or len(job_title) > 150
        or not job_description
        or len(job_description) > 25000
        or role_family not in valid_roles
        or seniority not in SENIORITY_LEVELS
    ):
        raise ValidationError('A valid company, job title, and job description are required.')

    with transaction.atomic():
        # A stable user row serializes starts even when there are no ledger rows to lock.
        get_user_model().objects.select_for_update().get(pk=user.pk)
        prior = TrialUsage.objects.select_related('preparation').filter(
            user=user,
            feature_code=TRIAL_FEATURE_CODE,
            idempotency_key=request_reference,
        ).first()
        if prior:
            if prior.request_fingerprint != request_fingerprint:
                raise ValidationError('This request key was already used for different preparation details.')
            if prior.preparation_id is None:
                raise ValidationError('This started preparation is no longer available to resume.')
            return prior.preparation

        paid_period = get_active_access_period(user, lock=True)
        if paid_period:
            return create_preparation_draft(
                user, request_reference, company_name, job_title, job_description,
                role_family, seniority, request_fingerprint,
                target_question_count=target_question_count,
            )

        now = timezone.now()
        cutoff = now - TRIAL_WINDOW
        usages = TrialUsage.objects.filter(
            user=user,
            started_at__gt=cutoff,
        )
        if usages.count() >= TRIAL_ALLOWANCE:
            raise PreparationSetLimitReached('You have used both free preparation trials in the last 20 days.')

        initial_content = {
            '_generation_state': 'incomplete',
            '_question_target': target_question_count,
            '_generation_progress': {'completed': 0, 'total': target_question_count},
            'rounds': [],
        }
        if candidate_profile is not None:
            initial_content['_candidate_profile'] = candidate_profile
            initial_content['_candidate_profile_state'] = 'review'
        preparation = PreparationSet.objects.create(
            owner=user,
            access_period=None,
            request_reference=request_reference,
            set_number=usages.count() + 1,
            company_name=company_name,
            job_title=job_title,
            role_family=role_family,
            seniority=seniority,
            job_description=job_description,
            input_fingerprint=request_fingerprint,
            generated_content=initial_content,
        )
        TrialUsage.objects.create(
            user=user,
            feature_code=TRIAL_FEATURE_CODE,
            idempotency_key=request_reference,
            request_fingerprint=request_fingerprint,
            started_at=now,
            preparation=preparation,
        )
        return preparation


def update_preparation_draft_target(preparation_id, target_question_count):
    """Persist a validated target before a draft is claimed for generation."""
    if (
        isinstance(target_question_count, bool)
        or not isinstance(target_question_count, int)
        or not MIN_PREPARATION_QUESTIONS <= target_question_count <= MAX_PREPARATION_QUESTIONS
    ):
        raise ValidationError('Choose between 30 and 60 interview questions.')
    with transaction.atomic():
        draft = PreparationSet.objects.select_for_update().get(pk=preparation_id)
        if not preparation_is_draft(draft):
            raise ValidationError('This preparation is already complete and its target cannot be changed.')
        content = dict(draft.generated_content or {})
        completed = count_valid_unique_questions(content.get('rounds') or [])
        if target_question_count < completed:
            raise ValidationError(f'The target cannot be lower than the {completed} valid questions already saved.')
        current = content.get('_question_target')
        lease_until = content.get('_generation_lease_until', 0)
        if current != target_question_count and content.get('_generation_state') == 'in_progress' and lease_until > timezone.now().timestamp():
            raise ValidationError('Generation is already running. Wait for it to finish before changing the target.')
        content['_question_target'] = target_question_count
        content['_generation_progress'] = {'completed': completed, 'total': target_question_count}
        if content.get('_generation_state') not in {'in_progress'}:
            content['_generation_state'] = 'incomplete'
        draft.generated_content = content
        draft.save(update_fields=['generated_content', 'updated_at'])
        return draft


def claim_preparation_draft(preparation_id, lease_seconds=1800):
    """Acquire or reclaim an expired generation lease across web workers."""
    with transaction.atomic():
        draft = PreparationSet.objects.select_for_update().get(pk=preparation_id)
        content = dict(draft.generated_content or {})
        if not preparation_is_draft(draft):
            return False
        lease_until = content.get('_generation_lease_until', 0)
        if content.get('_generation_state') == 'in_progress' and lease_until > timezone.now().timestamp():
            return False
        legacy_fallback = content.get('_generation_fallback_rounds')
        if isinstance(legacy_fallback, list):
            content['rounds'] = legacy_fallback
        content.pop('_generation_retry_all', None)
        content.pop('_generation_fallback_rounds', None)
        content['_generation_state'] = 'in_progress'
        content['_generation_lease_until'] = timezone.now().timestamp() + lease_seconds
        draft.generated_content = content
        draft.save(update_fields=['generated_content', 'updated_at'])
        return True


def checkpoint_preparation_draft(preparation_id, round_number, questions, completed, total=60):
    """Persist one validated round prefix without storing the submitted resume."""
    with transaction.atomic():
        draft = PreparationSet.objects.select_for_update().get(pk=preparation_id)
        content = dict(draft.generated_content or {})
        if content.get('_generation_state') not in {'in_progress', 'interrupted'}:
            return draft
        rounds = list(content.get('rounds') or [])
        while len(rounds) < round_number:
            index = len(rounds) + 1
            rounds.append({'round_number': index, 'title': f'Practice round {index}', 'questions': []})
        rounds[round_number - 1] = {
            **rounds[round_number - 1],
            'round_number': round_number,
            'title': f'Practice round {round_number}',
            'questions': questions,
        }
        content['rounds'] = rounds
        content['_generation_state'] = 'in_progress'
        target = content.get('_question_target', total)
        content['_question_target'] = target
        content['_generation_progress'] = {'completed': count_valid_unique_questions(rounds), 'total': target}
        content['_generation_lease_until'] = timezone.now().timestamp() + 1800
        draft.generated_content = content
        draft.save(update_fields=['generated_content', 'updated_at'])
        return draft


def mark_preparation_draft_interrupted(preparation_id, message=''):
    """Keep completed batches available after a generation failure."""
    with transaction.atomic():
        draft = PreparationSet.objects.select_for_update().get(pk=preparation_id)
        content = dict(draft.generated_content or {})
        if content.get('_generation_state') in {'in_progress', 'incomplete'}:
            if 'final quality check' in message.casefold():
                content['_generation_fallback_rounds'] = list(content.get('rounds') or [])
            rounds = content.get('rounds') or []
            content['_generation_progress'] = {
                'completed': count_valid_unique_questions(rounds),
                'total': content.get('_question_target', content.get('_generation_progress', {}).get('total', 60)),
            }
            content['_generation_state'] = 'temporarily_unavailable'
            content['_generation_message'] = message[:240]
            content.pop('_generation_lease_until', None)
            draft.generated_content = content
            draft.save(update_fields=['generated_content', 'updated_at'])
        return draft


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
    """Persist completed output under active Premium access or a started trial.

    Callers must create and retain one request reference for a generation
    attempt, then reuse it when retrying persistence. The database uniqueness
    rule makes that retry return the already-created set rather than consume
    another monthly slot.
    """
    if not user or not user.is_authenticated:
        raise PremiumPreparationRequired('Sign in to use Premium preparation.')

    try:
        request_reference = uuid.UUID(str(request_reference))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValidationError('A valid preparation request reference is required.') from exc

    existing = PreparationSet.objects.select_related('access_period__order').filter(
        owner=user,
        request_reference=request_reference,
    ).first()
    is_trial_draft = bool(existing and hasattr(existing, 'trial_usage'))
    legacy_period_active = bool(
        existing
        and existing.access_period_id
        and existing.access_period.order.plan_code == 'free_trial'
        and existing.access_period.order.status == PremiumOrder.Status.APPROVED
        and existing.access_period.starts_at <= timezone.now() < existing.access_period.ends_at
    )
    active_period = get_active_access_period(user)
    if active_period is None and not is_trial_draft and not legacy_period_active:
        raise PremiumPreparationRequired('An approved, active monthly plan is required.')
    if existing is not None and not preparation_is_draft(existing):
        if is_trial_draft or legacy_period_active:
            return existing
        if existing.access_period_id != active_period.pk:
            raise PremiumPreparationRequired('This request belongs to a different subscription month.')
        return existing
    if existing is None and input_fingerprint:
        existing = PreparationSet.objects.filter(
            owner=user,
            access_period=active_period,
            input_fingerprint=input_fingerprint,
        ).first()
    if existing and not preparation_is_draft(existing):
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
        raw_question_count = sum(
            len(row.get('questions', [])) for row in rounds if isinstance(row, dict) and isinstance(row.get('questions'), list)
        ) if isinstance(rounds, list) else 0
        valid_question_count = count_valid_unique_questions(rounds)
        target_question_count = generated_content.get('_question_target')
        invalid_target = target_question_count is not None and (
            isinstance(target_question_count, bool)
            or not isinstance(target_question_count, int)
            or not MIN_PREPARATION_QUESTIONS <= target_question_count <= MAX_PREPARATION_QUESTIONS
            or valid_question_count != target_question_count
        )
        if not isinstance(rounds, list) or len(rounds) not in {1, 2} or any(
            not isinstance(row, dict) or not isinstance(row.get('questions'), list) or not 1 <= len(row['questions']) <= 30
            for row in rounds
        ) or not 30 <= raw_question_count <= 60 or valid_question_count != raw_question_count or invalid_target:
            raise ValidationError('A complete preparation needs 30 to 60 valid, unique questions with answers.')
        generated_content = dict(generated_content)
        if target_question_count is not None:
            generated_content['_generation_state'] = 'complete'
            generated_content['_generation_progress'] = {
                'completed': valid_question_count,
                'total': target_question_count,
            }
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

    if is_trial_draft:
        # Generation resumes an already charged trial; it never charges again.
        existing.generated_content = generated_content
        existing.input_fingerprint = input_fingerprint or existing.input_fingerprint
        existing.save(update_fields=['generated_content', 'input_fingerprint', 'updated_at'])
        return existing

    if legacy_period_active:
        # Resume a historical started set only while its original trial period is active.
        with transaction.atomic():
            existing = PreparationSet.objects.select_for_update().select_related(
                'access_period__order',
            ).get(pk=existing.pk, owner=user)
            if not (
                existing.access_period
                and existing.access_period.order.plan_code == 'free_trial'
                and existing.access_period.order.status == PremiumOrder.Status.APPROVED
                and existing.access_period.starts_at <= timezone.now() < existing.access_period.ends_at
            ):
                raise PremiumPreparationRequired('This historical trial period has ended.')
            if not preparation_is_draft(existing):
                return existing
            existing.generated_content = generated_content
            existing.input_fingerprint = input_fingerprint or existing.input_fingerprint
            existing.save(update_fields=['generated_content', 'input_fingerprint', 'updated_at'])
            return existing

    try:
        with transaction.atomic():
            period = get_active_access_period(user, lock=True)
            if period is None:
                raise PremiumPreparationRequired('An approved, active monthly plan is required.')

            existing = PreparationSet.objects.filter(
                owner=user,
                request_reference=request_reference,
            ).first()
            if existing and not preparation_is_draft(existing):
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
                if not preparation_is_draft(existing_by_fingerprint):
                    return existing_by_fingerprint
                existing = existing_by_fingerprint

            if existing and preparation_is_draft(existing):
                if existing.access_period_id != period.pk:
                    raise PremiumPreparationRequired('This request belongs to a different subscription month.')
                existing.generated_content = generated_content
                existing.input_fingerprint = input_fingerprint or existing.input_fingerprint
                existing.save(update_fields=['generated_content', 'input_fingerprint', 'updated_at'])
                return existing

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
    ).filter(
        models.Q(trial_usage__isnull=False)
        | historical_trial_period_query()
        | models.Q(
            access_period__order__status=PremiumOrder.Status.APPROVED,
            access_period__order__plan_code__in=['premium_monthly', 'local_test_monthly'],
            access_period__starts_at__lte=at,
            access_period__ends_at__gt=at,
        )
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
    ).filter(
        models.Q(preparation_set__trial_usage__isnull=False)
        | historical_trial_period_query(prefix='preparation_set__', at=now)
        | models.Q(
            preparation_set__access_period__order__status=PremiumOrder.Status.APPROVED,
            preparation_set__access_period__order__plan_code__in=['premium_monthly', 'local_test_monthly'],
            preparation_set__access_period__starts_at__lte=now,
            preparation_set__access_period__ends_at__gt=now,
        )
    ).select_related('preparation_set').order_by('-saved_at')
