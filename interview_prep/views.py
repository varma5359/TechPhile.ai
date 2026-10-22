import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.contrib.staticfiles import finders
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils import timezone

from .forms import PaymentSubmissionForm, PreparationRequestForm
from .learning_aids import build_learning_aid
from .models import PaymentSubmission, PreparationSet, PremiumOrder
from .openai_generator import PreparationProviderError, generate_preparation, is_provider_configured, preparation_fingerprint
from .services import (
    PreparationSetLimitReached,
    PremiumPreparationRequired,
    get_preparation_access,
    mark_question_completed,
    save_generated_preparation_set,
    toggle_saved_question,
)


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

    initial = {'request_reference': uuid.uuid4()}
    form = PreparationRequestForm(initial=initial)
    if request.method == 'POST':
        form = PreparationRequestForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            previous_sets = PreparationSet.objects.filter(
                owner=request.user,
                access_period=access['access_period'],
            ).order_by('created_at') if access['access_period'] else PreparationSet.objects.none()
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
            if existing:
                return redirect('interview_prep:preparation_detail', preparation_id=existing.pk)

            access = get_preparation_access(request.user)
            if access['sets_remaining'] <= 0:
                form.add_error(None, 'You have used both preparation sets for this subscription month.')
            elif not is_provider_configured():
                form.add_error(None, 'AI preparation is not configured yet. Please check back later.')
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
    return render(request, 'interview_prep/create_preparation.html', {
        'form': form,
        'access': access,
        'generation_configured': is_provider_configured(),
        'previous_sets': PreparationSet.objects.filter(
            owner=request.user,
            access_period=access['access_period'],
        ).order_by('-created_at') if access['access_period'] else PreparationSet.objects.none(),
    })


@login_required
def preparation_detail(request, preparation_id):
    """Show the resume/JD review as the first, separate learner page."""
    preparation = _active_owned_preparation(request.user, preparation_id)
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
    rounds = content.get('rounds') or []
    if not rounds and content.get('questions'):
        rounds = [{'round_number': 1, 'title': 'Practice round 1', 'questions': content['questions']}]
    prepared_rounds = []
    saved_questions = []
    for question_round in rounds:
        questions = []
        for question_index, question in enumerate(question_round.get('questions', []), start=1):
            question = dict(question)
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
