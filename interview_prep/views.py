import json
import logging
import queue
import threading
import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, JsonResponse, StreamingHttpResponse
from django.contrib.staticfiles import finders
from django.db import IntegrityError, close_old_connections, connections, transaction
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.views.decorators.http import require_POST
from django.utils import timezone

from .answer_content import normalize_answer_content
from .candidate_profile import PROFILE_SECTIONS, confirm_profile_edits, profile_to_resume_text
from .blueprint import map_jd_requirements
from .forms import PaymentSubmissionForm, PreparationRequestForm
from .intelligence_schema import count_valid_unique_questions
from .learning_aids import build_learning_aid
from .models import PaymentSubmission, PreparationSet, PremiumOrder
from .openai_generator import PreparationProviderError, extract_candidate_profile, generate_preparation, is_provider_configured, preparation_fingerprint
from .services import (
    PreparationSetLimitReached,
    PremiumPreparationRequired,
    claim_preparation_draft,
    claim_preparation_draft,
    checkpoint_preparation_draft,
    create_preparation_draft,
    get_preparation_access,
    mark_trial_attempt_opened,
    mark_preparation_draft_interrupted,
    mark_question_completed,
    preparation_is_draft,
    save_generated_preparation_set,
    toggle_saved_question,
    update_preparation_draft_target,
)

logger = logging.getLogger(__name__)
_ACTIVE_GENERATIONS = set()
_ACTIVE_GENERATIONS_LOCK = threading.Lock()


def _profile_review_sections(profile):
    sections = []
    for key, label in PROFILE_SECTIONS:
        rows = profile.get(key, []) if isinstance(profile, dict) else []
        sections.append({
            'name': f'profile_{key}',
            'label': label,
            'value': '\n'.join(
                str(row.get('text', '')).strip()
                for row in rows if isinstance(row, dict) and str(row.get('text', '')).strip()
            ) if isinstance(rows, list) else '',
        })
    return sections


def _candidate_profile_match(profile, role_family):
    """Build a transparent resume evidence score and match counts."""
    extraction = profile.get('extraction', {}) if isinstance(profile, dict) else {}
    requirements = extraction.get('jd_requirements', []) if isinstance(extraction, dict) else []
    if not isinstance(requirements, list) or not requirements:
        return None
    requirements, _diagnostics = map_jd_requirements(role_family, requirements)
    counts = {'strong': 0, 'partial': 0, 'not_evidenced': 0}
    matched_requirements = {'strong': [], 'partial': [], 'not_evidenced': []}
    total_weight = matched_weight = 0
    for requirement in requirements:
        level = requirement.get('match_level', 'not_evidenced')
        if requirement.get('mapping_status') == 'unmapped' or level not in counts:
            level = 'not_evidenced'
        counts[level] += 1
        matched_requirements[level].append(requirement.get('requirement', ''))
        weight = 2 if requirement.get('mandatory') else 1
        total_weight += weight
        matched_weight += weight * {'strong': 1, 'partial': .5, 'not_evidenced': 0}[level]
    return {
        'score': round(100 * matched_weight / total_weight) if total_weight else 0,
        'counts': counts,
        'requirements': matched_requirements,
        'total': len(requirements),
    }


def _preparation_form_context(request, form, access, candidate_profile=None, resuming_draft=False, saved_profile=None):
    previous_sets = list(PreparationSet.objects.filter(
        owner=request.user, access_period=access['access_period'],
    ).order_by('-created_at')) if access['access_period'] else []
    for item in previous_sets:
        item.is_draft = preparation_is_draft(item)
        item.generation_progress = (item.generated_content or {}).get('_generation_progress', {})
    role_family = form['role_family'].value() or 'general-software-engineering'
    return {
        'form': form,
        'access': access,
        'generation_configured': is_provider_configured(),
        'resuming_draft': resuming_draft,
        'candidate_profile': candidate_profile,
        'profile_match': _candidate_profile_match(candidate_profile, role_family) if candidate_profile else None,
        'saved_profile': saved_profile,
        'pending_preparation': bool(request.session.get('interview_prep_pending_request')),
        'profile_review_sections': _profile_review_sections(candidate_profile) if candidate_profile else [],
        'previous_sets': previous_sets,
    }


def _sse_message(payload):
    return f"data: {json.dumps(payload, ensure_ascii=True)}\n\n"


def _preparation_progress_stream(*, user, data, previous_questions, fingerprint, draft, resume_content=None):
    """Stream question progress while saving validated batches as resumable drafts."""
    if not claim_preparation_draft(draft.pk):
        yield _sse_message({
            'type': 'error',
            'message': 'This preparation is already being generated in another tab. Your saved draft is still available.',
            'draft_url': reverse('interview_prep:preparation_questions', args=[draft.pk]),
            'resume_url': f"{reverse('interview_prep:create_preparation')}?resume={draft.pk}",
        })
        return

    events = queue.Queue()
    result = {}

    def run_generation(manage_connections=True):
        if manage_connections:
            close_old_connections()
        try:
            with _ACTIVE_GENERATIONS_LOCK:
                _ACTIVE_GENERATIONS.add(draft.pk)

            def report_progress(progress):
                if progress.get('validated_questions'):
                    checkpoint_preparation_draft(
                        draft.pk, progress['round_number'], progress['round_questions'], progress['completed'],
                        total=progress.get('total', 60),
                    )
                    progress = {key: value for key, value in progress.items() if key != 'round_questions'}
                events.put(('progress', progress))

            result['content'] = generate_preparation(
                resume_text=data['resume_text'], job_description=data['job_description'],
                company_name=data['company_name'], job_title=data['job_title'],
                role_family=data['role_family'], seniority=data['seniority'],
                previous_questions=previous_questions, progress_callback=report_progress,
                resume_content=resume_content,
                confirmed_extraction=data.get('confirmed_extraction'),
                target_question_count=data['question_target'],
            )
            result['preparation'] = save_generated_preparation_set(
                user=user, request_reference=data['request_reference'], company_name=data['company_name'],
                job_title=data['job_title'], job_description=data['job_description'],
                generated_content=result['content'], role_family=data['role_family'],
                seniority=data['seniority'], input_fingerprint=fingerprint,
            )
        except Exception as exc:
            result['error'] = exc
        finally:
            if result.get('error'):
                try:
                    mark_preparation_draft_interrupted(draft.pk, str(result['error']))
                except Exception:
                    logger.exception('Could not mark interview preparation draft as interrupted')
            with _ACTIVE_GENERATIONS_LOCK:
                _ACTIVE_GENERATIONS.discard(draft.pk)
            events.put(('done', None))
            if manage_connections:
                close_old_connections()

    if connections['default'].vendor == 'sqlite':
        run_generation(manage_connections=False)
    else:
        worker = threading.Thread(target=run_generation, name='interview-prep-generation', daemon=True)
        with _ACTIVE_GENERATIONS_LOCK:
            _ACTIVE_GENERATIONS.add(draft.pk)
        worker.start()

    yield _sse_message({'type': 'progress', 'phase': 'starting', 'completed': 0, 'total': data['question_target'],
                        'message': 'Starting your role-fit review...'})
    yield _sse_message({
        'type': 'progress', 'phase': 'draft', 'completed': 0, 'total': data['question_target'],
        'draft_url': reverse('interview_prep:preparation_questions', args=[draft.pk]),
        'resume_url': f"{reverse('interview_prep:create_preparation')}?resume={draft.pk}",
    })
    while True:
        try:
            kind, payload = events.get(timeout=15)
        except queue.Empty:
            yield ': keep-alive\n\n'
            continue
        if kind == 'progress':
            yield _sse_message({'type': 'progress', **payload})
            continue
        break

    error = result.get('error')
    if error:
        if isinstance(error, (PreparationProviderError, PremiumPreparationRequired, PreparationSetLimitReached, ValidationError)):
            message = str(error)
        else:
            logger.error('Unexpected interview preparation generation failure', exc_info=(type(error), error, error.__traceback__))
            message = 'Your interviewer could not complete this preparation. Your saved questions are still available; you can resume the unfinished part.'
        partial = PreparationSet.objects.filter(pk=draft.pk, owner=user).first()
        content = (partial.generated_content or {}) if partial else {}
        completed = content.get('_generation_progress', {}).get('completed', 0)
        total = content.get('_generation_progress', {}).get('total', 60)
        if completed:
            message = (
                f'Generation paused after {completed} of {total} questions. Your completed questions '
                'are saved. Review them now or resume to continue the unfinished round.'
            )
        yield _sse_message({
            'type': 'error', 'message': message,
            'draft_url': reverse('interview_prep:preparation_questions', args=[draft.pk]),
            'resume_url': f"{reverse('interview_prep:create_preparation')}?resume={draft.pk}",
            'completed': completed,
        })
        return
    preparation = result['preparation']
    yield _sse_message({
        'type': 'complete', 'redirect_url': reverse('interview_prep:preparation_detail', args=[preparation.pk]),
        'message': 'Your preparation is ready.',
    })


def _payments_ready():
    qr_image = settings.INTERVIEW_PREP_UPI_QR_IMAGE
    return bool(
        settings.INTERVIEW_PREP_PAYMENTS_ENABLED
        and is_provider_configured()
        and qr_image
        and finders.find(qr_image)
        and settings.INTERVIEW_PREP_MERCHANT_NAME
        and settings.INTERVIEW_PREP_UPI_ID
    )


def monthly_plan(request):
    """Show the individual monthly Premium plan and its UPI payment route."""
    qr_image = settings.INTERVIEW_PREP_UPI_QR_IMAGE
    payments_ready = _payments_ready()
    return render(request, 'interview_prep/monthly_plan.html', {
        'monthly_price': settings.INTERVIEW_PREP_MONTHLY_PRICE,
        'currency': settings.INTERVIEW_PREP_CURRENCY,
        'preparation_set_limit': 2,
        'payments_ready': payments_ready,
        'access': get_preparation_access(request.user),
        'pending_preparation': bool(request.session.get('interview_prep_pending_request')),
    })


@login_required
@require_POST
def start_order(request):
    """Create or resume the learner's pending monthly order at server price."""
    access = get_preparation_access(request.user)
    if access['is_trial'] and access['premium_active']:
        messages.info(request, 'Use your two free preparation sets before starting a monthly plan.')
        return redirect('interview_prep:create_preparation')
    if not _payments_ready():
        messages.info(request, 'Monthly Premium payments are not open yet.')
        return redirect('interview_prep:monthly_plan')

    with transaction.atomic():
        user = get_user_model().objects.select_for_update().get(pk=request.user.pk)
        existing_order = PremiumOrder.objects.filter(
            user=user,
            status__in=[
                PremiumOrder.Status.PENDING_PAYMENT,
                PremiumOrder.Status.SUBMITTED,
            ],
        ).first()
        order = existing_order or PremiumOrder.create_monthly(user)

    return redirect('interview_prep:order_detail', public_reference=order.public_reference)


@login_required
def order_detail(request, public_reference):
    """Display an owned order and accept one UPI claim while it is payable."""
    order = get_object_or_404(
        PremiumOrder,
        public_reference=public_reference,
        user=request.user,
    )

    qr_image = settings.INTERVIEW_PREP_UPI_QR_IMAGE
    qr_image_available = bool(qr_image and finders.find(qr_image))
    merchant_name = settings.INTERVIEW_PREP_MERCHANT_NAME
    upi_id = settings.INTERVIEW_PREP_UPI_ID
    payment_configured = _payments_ready() and qr_image_available

    form = PaymentSubmissionForm()
    if request.method == 'POST':
        form = PaymentSubmissionForm(request.POST, request.FILES)
        if order.status != PremiumOrder.Status.PENDING_PAYMENT:
            messages.info(request, 'This order cannot accept another payment submission.')
            return redirect('interview_prep:order_detail', public_reference=order.public_reference)
        if not payment_configured:
            form.add_error(None, 'Payment details are not configured yet. Please check back later.')
        elif form.is_valid():
            try:
                with transaction.atomic():
                    locked_order = PremiumOrder.objects.select_for_update().get(
                        pk=order.pk,
                        user=request.user,
                    )
                    if locked_order.status != PremiumOrder.Status.PENDING_PAYMENT:
                        messages.info(request, 'This order already has a payment submission.')
                        return redirect(
                            'interview_prep:order_detail',
                            public_reference=locked_order.public_reference,
                        )

                    PaymentSubmission.objects.create(
                        order=locked_order,
                        transaction_reference=form.cleaned_data['transaction_reference'],
                        receipt_file=form.cleaned_data.get('receipt_file'),
                    )
                    locked_order.status = PremiumOrder.Status.SUBMITTED
                    locked_order.save(update_fields=['status', 'updated_at'])
            except IntegrityError:
                form.add_error(
                    'transaction_reference',
                    'That transaction reference has already been submitted. Check it and contact support if you need help.',
                )
            else:
                messages.success(
                    request,
                    'Your payment details were submitted for manual verification. Premium access is not active until approval.',
                )
                return redirect(
                    'interview_prep:order_detail',
                    public_reference=order.public_reference,
                )

    return render(request, 'interview_prep/order_detail.html', {
        'order': order,
        'form': form,
        'qr_image': qr_image,
        'qr_image_available': qr_image_available,
        'merchant_name': merchant_name,
        'upi_id': upi_id,
        'payment_configured': payment_configured,
    })


@login_required
def create_preparation(request):
    """Allow two free sets, then require an active monthly plan to continue."""
    access = get_preparation_access(request.user)

    requested_draft = None
    draft_id = request.GET.get('resume', '')
    if request.method == 'GET' and draft_id.isdigit():
        requested_draft = PreparationSet.objects.filter(
            pk=int(draft_id), owner=request.user, access_period=access['access_period'],
        ).first()
        if requested_draft and not preparation_is_draft(requested_draft):
            return redirect('interview_prep:preparation_detail', preparation_id=requested_draft.pk)
    if access['is_trial'] and not access['premium_active'] and not requested_draft:
        return redirect('interview_prep:monthly_plan')
    saved_profile = (requested_draft.generated_content or {}).get('_candidate_profile') if requested_draft else None
    candidate_profile = (
        saved_profile if saved_profile and (requested_draft.generated_content or {}).get('_candidate_profile_state') != 'confirmed'
        else None
    )
    initial = {
        'request_reference': requested_draft.request_reference if requested_draft else uuid.uuid4(),
        'resume_draft_id': requested_draft.pk if requested_draft else '',
    }
    pending_request = request.session.get('interview_prep_pending_request')
    if pending_request and not requested_draft:
        initial.update(pending_request)
    if requested_draft:
        saved_target = (requested_draft.generated_content or {}).get('_question_target')
        if not isinstance(saved_target, int) or isinstance(saved_target, bool) or not 30 <= saved_target <= 60:
            saved_target = (requested_draft.generated_content or {}).get('_generation_progress', {}).get('total', 45)
        if not isinstance(saved_target, int) or isinstance(saved_target, bool) or not 30 <= saved_target <= 60:
            saved_target = 45
        profile_text = profile_to_resume_text(saved_profile) if saved_profile else ''
        initial.update({
            'company_name': requested_draft.company_name,
            'job_title': requested_draft.job_title,
            'role_family': requested_draft.role_family,
            'seniority': requested_draft.seniority,
            'question_target': saved_target,
            'job_description': requested_draft.job_description,
            'resume_text': profile_text,
            'seniority': requested_draft.seniority,
        })
        if candidate_profile:
            initial['seniority'] = candidate_profile.get('recommended_seniority', requested_draft.seniority)
    form = PreparationRequestForm(initial=initial)
    if request.method == 'POST':
        form = PreparationRequestForm(request.POST, request.FILES)
        if form.is_valid():
            data = form.cleaned_data
            action = request.POST.get('preparation_action', 'generate')
            if not access['premium_active']:
                request.session['interview_prep_pending_request'] = {
                    key: (str(data[key]) if key == 'request_reference' else data[key]) for key in (
                        'request_reference', 'question_target', 'company_name', 'job_title',
                        'role_family', 'seniority', 'job_description', 'resume_text',
                        'consent_to_ai_provider',
                    )
                }
                messages.info(request, 'Your interview details are ready. Choose the monthly plan to continue to preparation.')
                return redirect('interview_prep:monthly_plan')
            request.session.pop('interview_prep_pending_request', None)
            if action == 'review':
                try:
                    prior_request = PreparationSet.objects.filter(
                        owner=request.user,
                        access_period=access['access_period'],
                        request_reference=data['request_reference'],
                    ).first()
                    if prior_request and not preparation_is_draft(prior_request):
                        return redirect('interview_prep:preparation_detail', preparation_id=prior_request.pk)
                    if prior_request and (prior_request.generated_content or {}).get('_candidate_profile'):
                        candidate_profile = prior_request.generated_content['_candidate_profile']
                        form = PreparationRequestForm(initial={
                            **data,
                            'request_reference': prior_request.request_reference,
                            'resume_draft_id': prior_request.pk,
                            'resume_text': profile_to_resume_text(candidate_profile),
                            'seniority': candidate_profile.get('recommended_seniority', data['seniority']),
                            'consent_to_ai_provider': True,
                        })
                        access = get_preparation_access(request.user)
                        return render(request, 'interview_prep/create_preparation.html',
                                      _preparation_form_context(request, form, access, candidate_profile, True, candidate_profile))
                    profile = extract_candidate_profile(
                        data['resume_text'], data['job_description'], data['job_title'],
                        data['role_family'], data['seniority'],
                    )
                    fingerprint = preparation_fingerprint(
                        data['resume_text'], data['job_description'], data['company_name'],
                        data['job_title'], data['role_family'], data['seniority'],
                        target_question_count=data['question_target'],
                    )
                    draft = create_preparation_draft(
                        request.user, data['request_reference'], data['company_name'],
                        data['job_title'], data['job_description'], data['role_family'],
                        data['seniority'], fingerprint,
                        target_question_count=data['question_target'],
                    )
                    if not preparation_is_draft(draft):
                        return redirect('interview_prep:preparation_detail', preparation_id=draft.pk)
                    draft_content = dict(draft.generated_content or {})
                    draft_content['_candidate_profile'] = profile
                    draft_content['_candidate_profile_state'] = 'review'
                    draft.generated_content = draft_content
                    draft.save(update_fields=['generated_content', 'updated_at'])
                    candidate_profile = profile
                    form = PreparationRequestForm(initial={
                        **data,
                        'request_reference': draft.request_reference,
                        'resume_draft_id': draft.pk,
                        'resume_text': profile_to_resume_text(profile),
                        'seniority': profile.get('recommended_seniority', data['seniority']),
                        'consent_to_ai_provider': True,
                    })
                    access = get_preparation_access(request.user)
                    return render(request, 'interview_prep/create_preparation.html',
                                  _preparation_form_context(request, form, access, candidate_profile, True, profile))
                except (PreparationProviderError, PremiumPreparationRequired, PreparationSetLimitReached, ValidationError) as exc:
                    form.add_error(None, str(exc))
            draft = None
            if data.get('resume_draft_id'):
                draft = PreparationSet.objects.filter(
                    pk=data['resume_draft_id'], owner=request.user,
                    access_period=access['access_period'],
                ).first()
                if not draft or not preparation_is_draft(draft):
                    form.add_error(None, 'That preparation draft is no longer available. Please start a new preparation.')
                    draft = None
                else:
                    matches_draft = (
                        data['company_name'].strip() == draft.company_name
                        and data['job_title'].strip() == draft.job_title
                        and data['role_family'] == draft.role_family
                        and data['job_description'].strip() == draft.job_description
                    )
                    if not matches_draft:
                        form.add_error(None, 'The role details must match the saved draft. Start a new preparation to change them.')
                        draft = None
                    else:
                        data['request_reference'] = draft.request_reference
                        saved_profile = (draft.generated_content or {}).get('_candidate_profile')
                        if saved_profile:
                            if (draft.generated_content or {}).get('_candidate_profile_state') != 'confirmed':
                                candidate_profile = saved_profile
                            if (draft.generated_content or {}).get('_candidate_profile_state') != 'confirmed':
                                try:
                                    saved_profile = confirm_profile_edits(saved_profile, request.POST)
                                except ValueError as exc:
                                    form.add_error(None, str(exc))
                                    candidate_profile = saved_profile
                                else:
                                    content = dict(draft.generated_content or {})
                                    content['_candidate_profile'] = saved_profile
                                    content['_candidate_profile_state'] = 'confirmed'
                                    content['_confirmed_extraction'] = saved_profile['extraction']
                                    draft.generated_content = content
                                    draft.seniority = data['seniority']
                                    draft.save(update_fields=['generated_content', 'seniority', 'updated_at'])
                            else:
                                draft.seniority = data['seniority']
                                draft.save(update_fields=['seniority', 'updated_at'])
                            if (draft.generated_content or {}).get('_candidate_profile_state') == 'confirmed':
                                data['resume_text'] = profile_to_resume_text(saved_profile)
                                data['confirmed_extraction'] = (draft.generated_content or {}).get('_confirmed_extraction')
            previous_sets = PreparationSet.objects.filter(
                owner=request.user,
                access_period=access['access_period'],
                job_title=data['job_title'],
                role_family=data['role_family'],
                seniority=data['seniority'],
                job_description=data['job_description'],
            ).order_by('created_at') if access['access_period'] else PreparationSet.objects.none()
            if draft:
                previous_sets = previous_sets.exclude(pk=draft.pk)
            previous_questions = []
            for previous_set in previous_sets:
                content = previous_set.generated_content
                if content.get('rounds'):
                    previous_questions.extend(
                        question for question_round in content['rounds']
                        for question in question_round.get('questions', [])
                    )
                else:
                    previous_questions.extend(content.get('questions', []))
            fingerprint = preparation_fingerprint(
                data['resume_text'], data['job_description'], data['company_name'],
                data['job_title'], data['role_family'], data['seniority'], previous_questions,
                target_question_count=data['question_target'],
            ) if is_provider_configured() else ''
            existing = PreparationSet.objects.filter(
                owner=request.user,
                request_reference=data['request_reference'],
                access_period=access['access_period'],
            ).first()
            if existing is None and fingerprint:
                existing = PreparationSet.objects.filter(
                    owner=request.user,
                    access_period=access['access_period'],
                    input_fingerprint=fingerprint,
                ).first()
            if existing and not preparation_is_draft(existing):
                return redirect('interview_prep:preparation_detail', preparation_id=existing.pk)
            if existing and preparation_is_draft(existing):
                draft = existing

            if draft and not form.errors:
                try:
                    draft = update_preparation_draft_target(draft.pk, data['question_target'])
                except ValidationError as exc:
                    form.add_error('question_target', str(exc))

            access = get_preparation_access(request.user)
            if form.errors:
                pass
            elif access['slots_available'] <= 0 and not draft:
                form.add_error(None, 'You have used both preparation sets for this subscription month.')
            elif not is_provider_configured():
                form.add_error(None, 'Interview preparation is not available right now. Please check back later.')
            elif request.headers.get('Accept') == 'text/event-stream':
                if draft is None:
                    try:
                        draft = create_preparation_draft(
                            request.user, data['request_reference'], data['company_name'],
                            data['job_title'], data['job_description'], data['role_family'],
                            data['seniority'], fingerprint,
                            target_question_count=data['question_target'],
                        )
                    except (PremiumPreparationRequired, PreparationSetLimitReached, ValidationError) as exc:
                        form.add_error(None, str(exc))
                        draft = None
                if draft:
                    with _ACTIVE_GENERATIONS_LOCK:
                        already_running = draft.pk in _ACTIVE_GENERATIONS
                    if already_running:
                        return redirect('interview_prep:preparation_questions', preparation_id=draft.pk)
                    response = StreamingHttpResponse(
                        _preparation_progress_stream(
                            user=request.user, data=data, previous_questions=previous_questions,
                            fingerprint=fingerprint, draft=draft,
                            resume_content=draft.generated_content if draft else None,
                        ),
                        content_type='text/event-stream',
                    )
                    response['Cache-Control'] = 'no-cache, no-transform'
                    response['X-Accel-Buffering'] = 'no'
                    return response
            else:
                draft_claimed = False
                try:
                    if draft is None:
                        draft = create_preparation_draft(
                            request.user, data['request_reference'], data['company_name'],
                            data['job_title'], data['job_description'], data['role_family'],
                            data['seniority'], fingerprint,
                            target_question_count=data['question_target'],
                        )
                    if draft:
                        draft = update_preparation_draft_target(draft.pk, data['question_target'])
                    if not draft or not claim_preparation_draft(draft.pk):
                        raise ValidationError('This preparation is already being generated in another tab. Refresh to see its saved progress.')
                    draft_claimed = True

                    def checkpoint_progress(progress):
                        if progress.get('validated_questions'):
                            checkpoint_preparation_draft(
                                draft.pk, progress['round_number'], progress['round_questions'],
                                progress['completed'], total=progress.get('total', data['question_target']),
                            )

                    generated_content = generate_preparation(
                        resume_text=data['resume_text'],
                        job_description=data['job_description'],
                        company_name=data['company_name'],
                        job_title=data['job_title'],
                        role_family=data['role_family'],
                        seniority=data['seniority'],
                        previous_questions=previous_questions,
                        resume_content=draft.generated_content if draft else None,
                        confirmed_extraction=data.get('confirmed_extraction'),
                        target_question_count=data['question_target'],
                        progress_callback=checkpoint_progress,
                    )
                    preparation = save_generated_preparation_set(
                        user=request.user,
                        request_reference=data['request_reference'],
                        company_name=data['company_name'],
                        job_title=data['job_title'],
                        job_description=data['job_description'],
                        generated_content=generated_content,
                        role_family=data['role_family'],
                        seniority=data['seniority'],
                        input_fingerprint=fingerprint,
                    )
                except (
                    PreparationProviderError,
                    PremiumPreparationRequired,
                    PreparationSetLimitReached,
                    ValidationError,
                ) as exc:
                    if draft_claimed and draft and preparation_is_draft(draft):
                        mark_preparation_draft_interrupted(draft.pk, str(exc))
                        messages.warning(request, str(exc))
                        return redirect('interview_prep:preparation_questions', preparation_id=draft.pk)
                    form.add_error(None, str(exc))
                except Exception as exc:
                    logger.exception('Unexpected interview preparation generation failure')
                    if draft_claimed and draft and preparation_is_draft(draft):
                        mark_preparation_draft_interrupted(draft.pk, str(exc))
                        messages.warning(request, 'Generation paused. Your saved questions are safe; resume when the service is available.')
                        return redirect('interview_prep:preparation_questions', preparation_id=draft.pk)
                    form.add_error(None, 'Interview preparation is temporarily unavailable.')
                else:
                    return redirect(
                        'interview_prep:preparation_detail',
                        preparation_id=preparation.pk,
                    )

    access = get_preparation_access(request.user)
    return render(request, 'interview_prep/create_preparation.html',
                  _preparation_form_context(request, form, access, candidate_profile,
                                            bool(requested_draft), saved_profile))


@login_required
def preparation_detail(request, preparation_id):
    """Show the resume/JD review as the first, separate learner page."""
    preparation = _active_owned_preparation(request.user, preparation_id)
    if preparation_is_draft(preparation):
        return redirect('interview_prep:preparation_questions', preparation_id=preparation.pk)
    fit_requirements = []
    for source in (preparation.generated_content or {}).get('requirements', []):
        requirement = dict(source)
        requirement['student_suggestion'] = requirement.get('suggestion') or (
            'Add one truthful example: what you did, how you did it, and the result.'
            if requirement.get('match_level') == 'partial'
            else 'If you have this experience, add a real example. If this is new, use the practice page to learn the basics.'
        )
        fit_requirements.append(requirement)
    return render(request, 'interview_prep/preparation_detail.html', {
        'preparation': preparation,
        'fit_requirements': fit_requirements,
        'foundation_match_score': settings.INTERVIEW_PREP_FOUNDATION_MATCH_SCORE,
        'minimum_match_score': settings.INTERVIEW_PREP_MINIMUM_JD_MATCH_SCORE,
    })


def _active_owned_preparation(user, preparation_id):
    """Return an owned preparation while its approved monthly access is active."""
    now = timezone.now()
    return get_object_or_404(
        PreparationSet.objects.select_related('access_period'),
        pk=preparation_id,
        owner=user,
        access_period__order__status=PremiumOrder.Status.APPROVED,
        access_period__starts_at__lte=now,
        access_period__ends_at__gt=now,
    )


@login_required
def preparation_questions(request, preparation_id):
    """Show saved questions with answer formats tailored to each question."""
    preparation = _active_owned_preparation(request.user, preparation_id)
    saved_question_ids = set(preparation.saved_questions.values_list('question_id', flat=True))
    content = preparation.generated_content or {}
    is_draft = preparation_is_draft(preparation)
    rounds = content.get('rounds') or []
    if not rounds and content.get('questions'):
        rounds = [{'round_number': 1, 'title': 'Practice round 1', 'questions': content['questions']}]
    total_question_count = count_valid_unique_questions(rounds)
    progress_data = dict(content.get('_generation_progress') or {})
    target_question_count = content.get('_question_target')
    if not isinstance(target_question_count, int) or isinstance(target_question_count, bool) or not 30 <= target_question_count <= 60:
        target_question_count = progress_data.get('total') if is_draft else total_question_count
    if not isinstance(target_question_count, int) or isinstance(target_question_count, bool) or not 30 <= target_question_count <= 60:
        target_question_count = total_question_count
    progress_data['completed'] = total_question_count
    progress_data['total'] = target_question_count
    prepared_rounds = []
    saved_questions = []
    for question_round in rounds:
        questions = []
        for question_index, question in enumerate(question_round.get('questions', []), start=1):
            question = dict(question)
            question['answer_content'] = normalize_answer_content(question.get('answer_content'))
            question['learning_aid'] = build_learning_aid(question)
            if str(question.get('id', '')) in saved_question_ids:
                saved_questions.append({
                    'id': question.get('id'),
                    'question': question.get('question', ''),
                    'round_number': question_round.get('round_number', len(prepared_rounds) + 1),
                    'question_number': question_index,
                })
            questions.append(question)
        prepared_rounds.append({**question_round, 'questions': questions})
    return render(request, 'interview_prep/preparation_questions.html', {
        'preparation': preparation,
        'question_rounds': prepared_rounds,
        'saved_questions': saved_questions,
        'total_question_count': total_question_count,
        'saved_question_ids': saved_question_ids,
        'completed_question_ids': set(preparation.completed_question_ids or []),
        'is_draft': is_draft,
        'generation_progress': progress_data,
        'generation_state': content.get('_generation_state') if is_draft else 'complete',
        'target_question_count': target_question_count,
    })


@login_required
@require_POST
def mark_trial_attempt_opened_view(request, preparation_id):
    """Count a free attempt after the complete questions page has loaded."""
    preparation = _active_owned_preparation(request.user, preparation_id)
    preparation = mark_trial_attempt_opened(preparation.pk)
    content = preparation.generated_content or {}
    return JsonResponse({'counted': bool(content.get('_trial_attempt_consumed_at'))})


@login_required
@require_POST
def preparation_question_action(request, preparation_id, action):
    """Save a question or update its completion state with owner/access checks."""
    question_id = request.POST.get('question_id', '')
    try:
        if action == 'save':
            is_saved = toggle_saved_question(request.user, preparation_id, question_id)
            messages.success(request, 'Question saved for revision.' if is_saved else 'Question removed from saved items.')
        elif action == 'complete':
            completed = request.POST.get('completed') == 'true'
            mark_question_completed(request.user, preparation_id, question_id, completed=completed)
            messages.success(request, 'Practice progress updated.')
        else:
            raise Http404
    except PremiumPreparationRequired as exc:
        raise PermissionDenied from exc
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
    return redirect('interview_prep:preparation_questions', preparation_id=preparation_id)
