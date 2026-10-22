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
from django.http import Http404, StreamingHttpResponse
from django.contrib.staticfiles import finders
from django.db import IntegrityError, close_old_connections, connections, transaction
from django.shortcuts import get_object_or_404, redirect, render, reverse
from django.views.decorators.http import require_POST
from django.utils import timezone

from .answer_content import normalize_answer_content
from .forms import PaymentSubmissionForm, PreparationRequestForm
from .learning_aids import build_learning_aid
from .models import PaymentSubmission, PreparationSet, PremiumOrder
from .openai_generator import PreparationProviderError, generate_preparation, is_provider_configured, preparation_fingerprint
from .services import (
    PreparationSetLimitReached,
    PremiumPreparationRequired,
    claim_preparation_draft,
    checkpoint_preparation_draft,
    create_preparation_draft,
    get_preparation_access,
    mark_preparation_draft_interrupted,
    mark_question_completed,
    preparation_is_draft,
    save_generated_preparation_set,
    toggle_saved_question,
)

logger = logging.getLogger(__name__)
_ACTIVE_GENERATIONS = set()
_ACTIVE_GENERATIONS_LOCK = threading.Lock()


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
                    )
                    progress = {key: value for key, value in progress.items() if key != 'round_questions'}
                events.put(('progress', progress))

            result['content'] = generate_preparation(
                resume_text=data['resume_text'], job_description=data['job_description'],
                company_name=data['company_name'], job_title=data['job_title'],
                role_family=data['role_family'], seniority=data['seniority'],
                previous_questions=previous_questions, progress_callback=report_progress,
                resume_content=resume_content,
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

    yield _sse_message({'type': 'progress', 'phase': 'starting', 'completed': 0, 'total': 60,
                        'message': 'Starting your role-fit review...'})
    yield _sse_message({
        'type': 'progress', 'phase': 'draft', 'completed': 0, 'total': 60,
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
        yield _sse_message({
            'type': 'error', 'message': message,
            'draft_url': reverse('interview_prep:preparation_questions', args=[draft.pk]),
            'resume_url': f"{reverse('interview_prep:create_preparation')}?resume={draft.pk}",
            'completed': content.get('_generation_progress', {}).get('completed', 0),
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
    })


@login_required
@require_POST
def start_order(request):
    """Create or resume the learner's pending monthly order at server price."""
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
    """Generate and save one preparation set for an active Premium learner."""
    access = get_preparation_access(request.user)
    if not access['premium_active']:
        messages.info(request, 'An approved monthly Premium plan is required to prepare an interview set.')
        return redirect('interview_prep:monthly_plan')

    requested_draft = None
    draft_id = request.GET.get('resume', '')
    if request.method == 'GET' and draft_id.isdigit():
        requested_draft = PreparationSet.objects.filter(
            pk=int(draft_id), owner=request.user, access_period=access['access_period'],
        ).first()
        if requested_draft and not preparation_is_draft(requested_draft):
            return redirect('interview_prep:preparation_detail', preparation_id=requested_draft.pk)
    initial = {
        'request_reference': requested_draft.request_reference if requested_draft else uuid.uuid4(),
        'resume_draft_id': requested_draft.pk if requested_draft else '',
    }
    if requested_draft:
        initial.update({
            'company_name': requested_draft.company_name,
            'job_title': requested_draft.job_title,
            'role_family': requested_draft.role_family,
            'seniority': requested_draft.seniority,
            'job_description': requested_draft.job_description,
        })
    form = PreparationRequestForm(initial=initial)
    if request.method == 'POST':
        form = PreparationRequestForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
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
                        and data['seniority'] == draft.seniority
                        and data['job_description'].strip() == draft.job_description
                    )
                    if not matches_draft:
                        form.add_error(None, 'The role details must match the saved draft. Start a new preparation to change them.')
                        draft = None
                    else:
                        data['request_reference'] = draft.request_reference
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

            access = get_preparation_access(request.user)
            if form.errors:
                pass
            elif access['sets_remaining'] <= 0 and not draft:
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
                            resume_content=draft.generated_content if draft.generated_content.get('rounds') else None,
                        ),
                        content_type='text/event-stream',
                    )
                    response['Cache-Control'] = 'no-cache, no-transform'
                    response['X-Accel-Buffering'] = 'no'
                    return response
            else:
                try:
                    generated_content = generate_preparation(
                        resume_text=data['resume_text'],
                        job_description=data['job_description'],
                        company_name=data['company_name'],
                        job_title=data['job_title'],
                        role_family=data['role_family'],
                        seniority=data['seniority'],
                        previous_questions=previous_questions,
                        resume_content=draft.generated_content if draft and draft.generated_content.get('rounds') else None,
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
                    form.add_error(None, str(exc))
                else:
                    return redirect(
                        'interview_prep:preparation_detail',
                        preparation_id=preparation.pk,
                    )

    access = get_preparation_access(request.user)
    previous_sets = list(PreparationSet.objects.filter(
        owner=request.user, access_period=access['access_period'],
    ).order_by('-created_at')) if access['access_period'] else []
    for item in previous_sets:
        item.is_draft = preparation_is_draft(item)
        item.generation_progress = (item.generated_content or {}).get('_generation_progress', {})
    return render(request, 'interview_prep/create_preparation.html', {
        'form': form,
        'access': access,
        'generation_configured': is_provider_configured(),
        'resuming_draft': bool(requested_draft),
        'previous_sets': previous_sets,
    })


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
    total_question_count = sum(len(question_round.get('questions', [])) for question_round in prepared_rounds)
    return render(request, 'interview_prep/preparation_questions.html', {
        'preparation': preparation,
        'question_rounds': prepared_rounds,
        'saved_questions': saved_questions,
        'total_question_count': total_question_count,
        'saved_question_ids': saved_question_ids,
        'completed_question_ids': set(preparation.completed_question_ids or []),
        'is_draft': is_draft,
        'generation_progress': content.get('_generation_progress', {}),
    })


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
