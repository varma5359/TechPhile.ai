from datetime import timezone
from venv import logger
from django.http import Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models.functions import Lower
from .models import Category, Exam, Profile, Question, Answer, ExamAttempt, UserAnswer
from .forms import AssignInterviewerForm, ExamAttemptForm, InterviewStatusForm, UserAnswerForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import admin
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.models import LogEntry, CHANGE 
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .models import Exam, Question, ExamAttempt, UserAnswer
from .forms import UserAnswerForm
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from .models import ExamAttempt  
from django.contrib.auth.forms import UserCreationForm,AuthenticationForm
from django.contrib.auth import login 
from django.shortcuts import render, redirect
from django.shortcuts import render, redirect
from django.contrib.auth import login as auth_login, logout as auth_logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from exams import models
from django.db.models import Q, Count, Max, Min, Avg, Sum, F
#  interview views
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from datetime import datetime, timedelta
import uuid
from .models import Applicant, ExamAttempt, UserAnswer, Profile, Interviewer
from .forms import (InterviewStatusForm, RescheduleInterviewForm, 
                )
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from .models import Applicant
from .forms import InterviewFeedbackForm, RescheduleInterviewForm
from django.shortcuts import render, get_object_or_404, redirect
from .models import Applicant  # âœ… Using Applicant as your Interview model
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth import update_session_auth_hash
from .forms import (
    ProfileUpdateForm,
    CareerLearningPreferencesForm,
    CustomPasswordChangeForm,
    NotificationSettingsForm,
    PreferencesForm
)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .serializers import (
    ExamSerializer, CategorySerializer, UserAnswerSerializer, 
    InterviewSerializer, ProfileSerializer, SignupSerializer, LoginSerializer
)

def exam_not_available(request, heading, explanation):
    """Render a learner-friendly 404 for unavailable exam content."""
    return render(request, 'exams/not_available.html', {
        'unavailable_heading': heading,
        'unavailable_explanation': explanation,
    }, status=404)


def exam_page_not_found(request, unmatched_path=''):
    return exam_not_available(
        request,
        'This exam page is not available',
        'The link may be out of date, or this page may not have been published yet. Browse the available exams to find current practice.',
    )


def exam_list(request):
    filter_slug = request.GET.get('filter', 'all')
    
    if filter_slug == 'all':
        exams = Exam.objects.all()
        active_filter = 'all'
    else:
        category = Category.objects.filter(slug=filter_slug).first()
        if category is None:
            return exam_not_available(
                request,
                'This subject is not available',
                'That subject filter may be out of date, or the subject is not currently published. Browse all available exams to see what you can practice now.',
            )
        exams = Exam.objects.filter(category=category)
        active_filter = category.slug
    exams = exams.select_related('category').order_by(Lower('title'), 'title', 'pk')
    categories = Category.objects.order_by(Lower('name'), 'name')
    levels = ['beginner', 'intermediate', 'advanced']
    set_numbers = [1, 2, 3]
    return render(request, 'exams/exam_list.html', {
    'exams': exams,
    'categories': categories,
    'active_filter': active_filter,
    'levels': levels,
    'set_numbers': set_numbers,
})

@login_required
def exam_detail(request, exam_slug):
    exam = Exam.objects.filter(slug=exam_slug).first()
    if exam is None:
        return exam_not_available(
            request,
            'This exam is not available',
            'It may have been removed or is not currently published. Browse the available exams to find another subject to practice.',
        )
    
    # Check for existing incomplete attempt
    incomplete_attempts = ExamAttempt.objects.filter(
        user=request.user,
        exam=exam,
        completed_at__isnull=True
    ).order_by('-started_at')
    incomplete_attempt = incomplete_attempts.first()

    set_rows = list(
        exam.questions.values('level', 'set_number')
        .annotate(question_count=Count('id'), first_question_order=Min('order'))
        .order_by('level', 'set_number')
    )
    question_counts = {
        (row['level'], row['set_number']): row['question_count']
        for row in set_rows
    }
    completed_sets = {}
    completed_answer_rows = UserAnswer.objects.filter(
        attempt__user=request.user,
        attempt__exam=exam,
        attempt__completed_at__isnull=False,
    ).values(
        'attempt_id', 'question__level', 'question__set_number',
    ).annotate(
        completed_at=Max('attempt__completed_at'),
    ).order_by()
    for row in completed_answer_rows:
        key = (row['question__level'], row['question__set_number'])
        if question_counts.get(key, 0):
            previous = completed_sets.get(key)
            if previous is None or row['completed_at'] > previous['completed_at']:
                completed_sets[key] = {
                    'attempt_id': row['attempt_id'],
                    'completed_at': row['completed_at'],
                }

    in_progress_sets = {}
    if incomplete_attempts.exists():
        progress_answer_rows = UserAnswer.objects.filter(
            attempt__in=incomplete_attempts,
            selected_answer__isnull=False,
        ).values_list('question__level', 'question__set_number', 'question__order').distinct()
        for level_name, set_number, question_order in progress_answer_rows:
            progress_key = (level_name, set_number)
            in_progress_sets.setdefault(progress_key, set()).add(question_order)

    question_orders_by_set = {}
    for level_name, set_number, question_order in exam.questions.order_by().values_list(
        'level', 'set_number', 'order',
    ):
        question_orders_by_set.setdefault((level_name, set_number), []).append(question_order)

    level_order = {value: index for index, (value, _label) in enumerate(Question.LEVEL_CHOICES)}
    levels_by_name = {}
    for row in set_rows:
        level_name = row['level']
        levels_by_name.setdefault(level_name, {
            'name': level_name,
            'sets': [],
            'completed_count': 0,
            'in_progress_count': 0,
            'question_count': 0,
        })
        completed = completed_sets.get((level_name, row['set_number']))
        answered_orders = in_progress_sets.get((level_name, row['set_number']), set())
        answered_count = len(answered_orders)
        in_progress = not completed and answered_count > 0
        unanswered_orders = [
            order for order in question_orders_by_set.get((level_name, row['set_number']), [])
            if order not in answered_orders
        ]
        levels_by_name[level_name]['sets'].append({
            'number': row['set_number'],
            'question_count': row['question_count'],
            'first_question_order': row['first_question_order'],
            'start_order': unanswered_orders[0] if in_progress and unanswered_orders else row['first_question_order'],
            'completed': completed is not None,
            'in_progress': in_progress,
            'answered_count': answered_count,
            'result_attempt_id': completed['attempt_id'] if completed else None,
        })
        levels_by_name[level_name]['question_count'] += row['question_count']
        if completed:
            levels_by_name[level_name]['completed_count'] += 1
        elif in_progress:
            levels_by_name[level_name]['in_progress_count'] += 1
    exam_levels = sorted(
        levels_by_name.values(),
        key=lambda item: (level_order.get(item['name'], len(level_order)), item['name']),
    )
    
    context = {
        'exam': exam,
        'incomplete_attempt': incomplete_attempt,
        'exam_levels': exam_levels,
    }
    return render(request, 'exams/exam_detail.html', context)


@login_required
def exam_question(request, exam_slug, level, set_number, question_order):

    # Step 1: Validate exam and normalize level
    exam = Exam.objects.filter(slug=exam_slug).first()
    if exam is None:
        return exam_not_available(
            request,
            'This exam is not available',
            'It may have been removed or is not currently published. Browse the available exams to find another subject to practice.',
        )
    level = level.lower()  # Ensure consistent case
    valid_levels = {value for value, _label in Question.LEVEL_CHOICES}
    if level not in valid_levels:
        return exam_not_available(
            request,
            'This practice level is not available',
            'The level in this link is not recognized. Choose an exam and select one of its available practice levels.',
        )
    
    # Step 2: Get questions for this set and level
    question_qs = Question.objects.filter(
        exam=exam,
        level=level,
        set_number=set_number
    ).order_by('order')
    
    # Step 3: Check if questions exist
    if not question_qs.exists():
        return render(request, 'exams/no_questions.html', {
            'exam': exam,
            'level': level,
            'set_number': set_number,
        })
    
    question_orders = list(question_qs.values_list('order', flat=True))

    # Step 4: Get current question
    question = question_qs.filter(order=question_order).first()
    if question is None:
        return exam_not_available(
            request,
            'This question is not available',
            'This question may have been removed or is not part of the selected set. Return to exam practice and choose an available set.',
        )
    
    # Keep each level and set in its own attempt so progress and scores cannot mix.
    attempt_session_key = f'exam_attempt_{exam.pk}_{level}_{set_number}'
    retaking = request.GET.get('retake') == '1'
    attempt = None
    if not retaking:
        attempt = ExamAttempt.objects.filter(
            pk=request.session.get(attempt_session_key),
            user=request.user,
            exam=exam,
            completed_at__isnull=True,
        ).first()
        if attempt is None:
            attempt = ExamAttempt.objects.filter(
                user=request.user,
                exam=exam,
                completed_at__isnull=True,
                user_answers__question__level=level,
                user_answers__question__set_number=set_number,
            ).distinct().order_by('-started_at').first()
    if attempt is None:
        attempt = ExamAttempt.objects.create(user=request.user, exam=exam)
    request.session[attempt_session_key] = attempt.pk
    if retaking and request.method == 'GET':
        return redirect(
            'exams:exam_question',
            exam_slug=exam.slug,
            level=level,
            set_number=set_number,
            question_order=question_order,
        )
    
    # Step 6: Handle POST request (answer submission)
    if request.method == 'POST':
        form = UserAnswerForm(request.POST, question=question)
        # The final confirmation is allowed to submit with this question blank.
        if form.is_valid() or request.POST.get('confirm_submit') == '1':
            selected_answer = form.cleaned_data.get('selected_answer') if form.is_valid() else None
            if selected_answer or request.POST.get('confirm_submit') == '1':
                UserAnswer.objects.update_or_create(
                    attempt=attempt,
                    question=question,
                    defaults={
                        'selected_answer': selected_answer,
                        'is_correct': bool(selected_answer and selected_answer.is_correct)
                    }
                )
            if request.POST.get('confirm_submit') == '1':
                correct_answers = UserAnswer.objects.filter(
                    attempt=attempt,
                    question__in=question_qs,
                    is_correct=True,
                ).count()
                attempt.score = (correct_answers / question_qs.count()) * 100
                attempt.completed_at = timezone.now()
                attempt.save()
                request.session.pop(attempt_session_key, None)
                return redirect('exams:exam_result', attempt_id=attempt.id)
            if selected_answer:
                # Do not finish a set while any question is still unanswered.
                answered_question_ids = UserAnswer.objects.filter(
                    attempt=attempt,
                    selected_answer__isnull=False,
                ).values('question_id')
                unanswered_questions = question_qs.exclude(pk__in=answered_question_ids)
                next_question = unanswered_questions.filter(order__gt=question_order).first()
                if next_question is None:
                    next_question = unanswered_questions.first()
                if next_question:
                    return redirect('exams:exam_question', 
                                  exam_slug=exam.slug,
                                  level=level,
                                  set_number=set_number,
                                  question_order=next_question.order)
                else:
                    # Calculate score and finish
                    correct_answers = UserAnswer.objects.filter(
                        attempt=attempt,
                        question__in=question_qs,
                        is_correct=True,
                    ).count()
                    attempt.score = (correct_answers / question_qs.count()) * 100
                    attempt.completed_at = timezone.now()
                    attempt.save()
                    request.session.pop(attempt_session_key, None)
                    return redirect('exams:exam_result', attempt_id=attempt.id)
    else:
        # Handle GET request
        try:
            initial = {'selected_answer': UserAnswer.objects.get(
                attempt=attempt, 
                question=question
            ).selected_answer}
        except UserAnswer.DoesNotExist:
            initial = None
        
        form = UserAnswerForm(initial=initial, question=question)
        form.fields['selected_answer'].queryset = question.answers.all()
    
    # Prepare context
    answered_orders = set(UserAnswer.objects.filter(
        attempt=attempt,
        question__level=level,
        question__set_number=set_number,
        selected_answer__isnull=False,
    ).values_list('question__order', flat=True))
    question_navigation = [
        {
            'order': order,
            'answered': order in answered_orders,
            'current': order == question_order,
        }
        for order in question_orders
    ]
    current_position = question_orders.index(question_order) + 1
    total_questions = len(question_orders)

    context = {
        'exam': exam,
        'question': question,
        'form': form,
        'current_question': question_order,
        'current_position': current_position,
        'level': level,
        'set_number': set_number,
        'total_questions': total_questions,
        'answered_count': len(answered_orders),
        'question_navigation': question_navigation,
        'previous_question': question_qs.filter(order__lt=question_order).order_by('-order').first(),
    }
    return render(request, 'exams/exam_question.html', context)



@login_required
def exam_result(request, attempt_id):
    attempt = ExamAttempt.objects.filter(id=attempt_id, user=request.user).first()
    if attempt is None:
        return exam_not_available(
            request,
            'This exam result is not available',
            'The result may have expired, or it may belong to a different account. Browse your available exam practice to continue.',
        )
    attempt_answers = attempt.user_answers.select_related('question', 'selected_answer').all()
    correct_answers = 0
    anchor_question = attempt_answers.first().question if attempt_answers.exists() else None
    user_answers = attempt_answers.filter(selected_answer__isnull=False)
    set_questions = Question.objects.filter(
        exam=attempt.exam,
        level=anchor_question.level,
        set_number=anchor_question.set_number,
    ).order_by('order') if anchor_question else Question.objects.none()
    total_questions = set_questions.count() or user_answers.count()
    answers_by_question = {ua.question_id: ua for ua in user_answers}
    review_rows = []
    for question in set_questions:
        ua = answers_by_question.get(question.pk)
        question.correct_answer = question.answers.filter(is_correct=True).first()
        if ua:
            ua.correct_answer = question.correct_answer
            if ua.is_correct and ua.selected_answer_id:
                correct_answers += 1
        review_rows.append({'question': question, 'user_answer': ua, 'correct_answer': question.correct_answer,
                            'is_correct': bool(ua and ua.selected_answer_id and ua.is_correct),
                            'answered': bool(ua and ua.selected_answer_id)})
    if not set_questions.exists():
        for ua in user_answers:
            ua.correct_answer = ua.question.answers.filter(is_correct=True).first()
            if ua.is_correct and ua.selected_answer_id:
                correct_answers += 1
            review_rows.append({'question': ua.question, 'user_answer': ua, 'correct_answer': ua.correct_answer,
                                'is_correct': bool(ua.is_correct and ua.selected_answer_id),
                                'answered': bool(ua.selected_answer_id)})
    answered_count = sum(1 for row in review_rows if row['answered'])
    incorrect_answers = answered_count - correct_answers
    return render(request, 'exams/exam_result.html', {
        'attempt': attempt,
        'user_answers': user_answers,
        'review_rows': review_rows,
        'correct_answers': correct_answers,
        'incorrect_answers': incorrect_answers,  # Add this line
        'total_questions': total_questions,
        'unanswered_count': total_questions - answered_count,
    })

# def signup(request):
#     if request.method == 'POST':
#         form = UserCreationForm(request.POST)
#         if form.is_valid():
#             user = form.save()
#             auth_login(request, user)  # Automatically logs in after signup
#             return redirect('exams:exam_list')
#     else:
#         form = UserCreationForm()
#     return render(request, 'registration/signup.html', {'form': form})


# def user_login(request):
#     if request.method == 'POST':
#         form = AuthenticationForm(request, data=request.POST)
#         if form.is_valid():
#             user = form.get_user()
#             auth_login(request, user)
#             return redirect('exams:exam_list')
#     else:
#         form = AuthenticationForm()
#     return render(request, 'registration/login.html', {'form': form})


# def user_logout(request):
#     auth_logout(request)
#     return redirect('login')


@login_required
def student_dashboard(request):
    from .models import ExamAttempt
    user = request.user
    profile = getattr(request, 'profile_preferences', None)
    dashboard_view = getattr(profile, 'dashboard_view', 'default')
    attempt_limit = {'compact': 3, 'detailed': 20}.get(dashboard_view, 6)
    all_attempts = ExamAttempt.objects.filter(user=user).select_related(
        'exam', 'exam__category').order_by('-started_at')
    scored_attempts = all_attempts.filter(
        completed_at__isnull=False, score__isnull=False).order_by('-completed_at')
    category_stats = list(scored_attempts.values('exam__category__name').annotate(
        total=Count('id'),
        avg_score=Avg('score')
    ).order_by('-avg_score', 'exam__category__name')[:6])
    highest_score_attempt = scored_attempts.order_by('-score', '-completed_at').first()
    highest_score = highest_score_attempt.score if highest_score_attempt else None
    highest_score_exam = highest_score_attempt.exam.title if highest_score_attempt else None
    last_five_average = scored_attempts[:5].aggregate(avg=Avg('score'))['avg']

    chart_width, chart_bottom, chart_height = 720, 184, 142
    recent_scores = list(scored_attempts[:6])
    recent_scores.reverse()
    count = len(recent_scores)
    plot_left, plot_width = 58, 640
    slot_width = plot_width / max(count, 1)
    exam_chart = []
    for index, attempt in enumerate(recent_scores):
        score = max(0, min(float(attempt.score), 100))
        height = round(chart_height * score / 100, 1)
        exam_chart.append({
            'attempt': attempt,
            'score': score,
            'x': round(plot_left + slot_width * index + (slot_width - min(48, slot_width * .58)) / 2, 1),
            'width': round(min(48, slot_width * .58), 1),
            'y': round(chart_bottom - height, 1),
            'height': height,
            'center': round(plot_left + slot_width * (index + .5), 1),
            'index': index + 1,
        })
    exam_chart_ticks = [
        {'value': value, 'y': chart_bottom - chart_height * value / 100}
        for value in (0, 25, 50, 75, 100)
    ]

    return render(request, 'exams/student_dashboard.html', {
        'total_attempts': all_attempts.count(),
        'completed_attempts': scored_attempts.count(),
        'in_progress_attempts': all_attempts.filter(completed_at__isnull=True).count(),
        'avg_score': scored_attempts.aggregate(avg=Avg('score'))['avg'],
        'last_five_average': last_five_average,
        'attempts': all_attempts[:attempt_limit],
        'dashboard_view': dashboard_view,
        'category_stats': category_stats,
        'highest_score': highest_score,
        'highest_score_exam': highest_score_exam,
        'exam_chart': exam_chart,
        'exam_chart_ticks': exam_chart_ticks,
        'exam_chart_width': chart_width,
    })


import re
import uuid
from datetime import datetime
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from .models import Applicant

@login_required
def mock_interview_form(request):
    if request.method == 'POST':
        try:
            # Collect and strip all form data
            form_data = {
                'user': request.user if request.user.is_authenticated else None,
                'email': request.POST.get('email', '').strip(),
                'first_name': request.POST.get('first_name', '').strip(),
                'last_name': request.POST.get('last_name', '').strip(),
                'phone': request.POST.get('phone', '').strip(),
                'year_of_passout': request.POST.get('year_of_passout', '').strip(),
                'qualification': request.POST.get('qualification', '').strip(),
                'experience': request.POST.get('experience', '').strip(),
                'heard_from': request.POST.get('heard_from', '').strip(),
                'skills': ', '.join(request.POST.getlist('skills')),
                'additional_skills': request.POST.get('additional_skills', '').strip(),
                'interview_date': request.POST.get('interview_date', '').strip(),
                'interview_time': request.POST.get('interview_time', '').strip(),
                'interview_type': request.POST.get('interview_type', 'technical'),
                'difficulty': request.POST.get('difficulty', 'medium'),
                'resume': request.FILES.get('resume')
            }

            required_fields = ['email', 'first_name', 'last_name', 'phone',
                               'year_of_passout', 'qualification', 'experience',
                               'interview_date', 'interview_time', 'skills']

            errors = {}

            # Required field check
            for field in required_fields:
                if not form_data.get(field):
                    errors[field] = f'The {field.replace("_", " ").title()} field is required.'

            if not form_data['resume']:
                errors['resume'] = 'Resume is required.'

            # Email format validation
            email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
            if form_data['email'] and not re.match(email_pattern, form_data['email']):
                errors['email'] = 'Enter a valid email address (e.g., yourname@example.com)'


            # Phone number validation (Indian 10-digit with optional +91/91/0)
            phone_pattern = r'^(\+91[\-\s]?|91[\-\s]?|0)?[6-9]\d{9}$'
            if form_data['phone'] and not re.match(phone_pattern, form_data['phone']):
                errors['phone'] = 'Enter a valid Indian mobile number (e.g., 9876543210 or +91-9876543210).'

            # Name validation (only letters, spaces, dots, hyphens)
            name_pattern = r'^[a-zA-Z][a-zA-Z.\-\s]{2,49}$'
            if form_data['first_name'] and not re.match(name_pattern, form_data['first_name']):
                errors['first_name'] = 'First name should start with a letter and contain only letters, spaces, dots, or hyphens (3-50 characters).'
            if form_data['last_name'] and not re.match(name_pattern, form_data['last_name']):
                errors['last_name'] = 'Last name should start with a letter and contain only letters, spaces, dots, or hyphens (3-50 characters).'
            # Resume file type and size
            allowed_extensions = ['pdf', 'doc', 'docx']
            max_file_size = 2 * 1024 * 1024  # 2MB
            resume = form_data['resume']
            if resume:
                extension = resume.name.split('.')[-1].lower()
                if extension not in allowed_extensions:
                    errors['resume'] = 'Resume must be a PDF or Word document.'
                elif resume.size > max_file_size:
                    errors['resume'] = 'Resume file size must be under 2MB.'

            # Year of passout validation
            if form_data['year_of_passout']:
                try:
                    year = int(form_data['year_of_passout'])
                    if year < 2000 or year > datetime.now().year + 5:
                        errors['year_of_passout'] = 'Enter a valid year (2000 to future).'
                except ValueError:
                    errors['year_of_passout'] = 'Year must be a number.'

            
            # Interview date validation (must be future)
            try:
                interview_date_obj = datetime.strptime(form_data['interview_date'], '%Y-%m-%d').date()
                if interview_date_obj <= datetime.now().date():
                    errors['interview_date'] = 'Interview date must be a future date.'
            except ValueError:
                errors['interview_date'] = 'Invalid date format. Use YYYY-MM-DD.'

            # Interview time slot validation
            valid_time_slots = ['09:00-10:00', '10:30-11:30', '12:00-13:00',
                                '14:00-15:00', '15:30-16:30', '17:00-18:00']
            if form_data['interview_time'] not in valid_time_slots:
                errors['interview_time'] = 'Select a valid interview time slot.'

            # If errors exist
            if errors:
                return JsonResponse({
                    'success': False,
                    'message': 'Please correct the errors.',
                    'errors': errors
                }, status=400)

            # Generate interview ID and link
            interview_id = uuid.uuid4()
            interview_link = f"{settings.BASE_URL}/interview/{interview_id}/join/"

            # Save applicant
            applicant = Applicant.objects.create(
                **form_data,
                interview_id=interview_id,
                interview_link=interview_link,
                status='scheduled'
            )

            # Send confirmation email
            send_confirmation_email(applicant)

            return JsonResponse({
                'success': True,
                'message': 'Interview scheduled successfully!',
                'interview_id': applicant.id,
                'interview_date': applicant.interview_date,
                'interview_time': applicant.interview_time,
                'interview_link': interview_link
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            }, status=500)

    # GET request
    years = list(range(2010, datetime.now().year + 5))
    programming_skills = [
    'Python', 'Java', 'C', 'C++', 'JavaScript', 'TypeScript', 'Go', 'Rust'
]

    web_dev_skills = [
        'HTML', 'CSS', 'JavaScript', 'React', 'Angular', 'Vue.js',
        'Node.js', 'Django', 'Flask', 'Next.js', 'Express.js',
        'Bootstrap', 'Tailwind CSS'
    ]
    
    ai_skills = [
        'Machine Learning', 'Deep Learning', 'NLP', 'Computer Vision',
        'TensorFlow', 'Keras', 'PyTorch', 'Pandas', 'NumPy',
        'Scikit-learn', 'OpenCV', 'Matplotlib', 'Seaborn'
    ]
    
    testing_skills = [
        'Manual Testing', 'Automation Testing', 'Selenium',
        'JUnit', 'TestNG', 'Postman', 'Cypress', 'JMeter'
    ]
    
    development_skills = [
        'Git', 'GitHub', 'VS Code', 'Docker', 'Kubernetes',
        'CI/CD', 'Jenkins', 'Agile', 'Scrum', 'Linux'
    ]
    
    visualization_skills = [
        'TIBCO Spotfire', 'Power BI', 'Tableau', 'Excel (Advanced)',
        'Google Data Studio', 'Looker'
    ]
    
    other_skills = [
        'SQL', 'MongoDB', 'PostgreSQL', 'Firebase', 'AWS',
        'Azure', 'Data Structures', 'Algorithms',
        'REST API', 'GraphQL', 'Unit Testing'
    ]
    
    time_slots = [
        '09:00-10:00', '10:30-11:30', '12:00-13:00',

        '14:00-15:00', '15:30-16:30', '17:00-18:00'
    ]

    return render(request, 'exams/interview_form.html', {
        'programming_skills': programming_skills,
        'web_dev_skills': web_dev_skills,
        'ai_skills': ai_skills,
        'testing_skills': testing_skills,
        'development_skills': development_skills,
        'visualization_skills': visualization_skills,
        'other_skills': other_skills,
        'years': years,
        'time_slots': time_slots,
        'today': datetime.now(),
        'interview_types': Applicant.INTERVIEW_TYPE_CHOICES,
        'difficulty_levels': Applicant.DIFFICULTY_CHOICES
    })

def send_confirmation_email(applicant):
    subject = 'Your Mock Interview Has Been Scheduled'
    html_message = render_to_string('emails/interview_confirmation.html', {
        'applicant': applicant,
        'interview_link': applicant.interview_link,
        'interview_date': applicant.interview_date,
        'interview_time': applicant.interview_time,
        'interview_type': applicant.interview_type,
        'difficulty': applicant.difficulty
    })
    plain_message = strip_tags(html_message)
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [applicant.email],
        fail_silently=False,
        html_message=html_message
    )

@login_required
def view_interview(request, pk):
    interview = get_object_or_404(Applicant, pk=pk, user=request.user)
    return render(request, 'exams/view_interview.html', {'interview': interview})


@login_required
def edit_interview(request, pk):
    interview = get_object_or_404(Applicant, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = InterviewStatusForm(request.POST, request.FILES, instance=interview)
        if form.is_valid():
            form.save()
            messages.success(request, 'Interview details updated successfully!')
            return redirect('view_interview', pk=interview.pk)
    else:
        form = InterviewStatusForm(instance=interview)
    
    return render(request, 'exams/edit_interview.html', {
        'form': form,
        'interview': interview
    })


@login_required
def interview_feedback(request, pk):
    interview = get_object_or_404(Applicant, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = InterviewFeedbackForm(request.POST, instance=interview)
        if form.is_valid():
            updated_interview = form.save(commit=False)
            updated_interview.status = 'completed'
            updated_interview.save()
            
            # Send feedback email
            send_feedback_email(updated_interview)
            
            messages.success(request, 'Feedback submitted successfully!')
            return redirect('view_interview', pk=interview.pk)
    else:
        form = InterviewFeedbackForm(instance=interview)
    
    return render(request, 'exams/interview_feedback.html', {
        'form': form,
        'interview': interview
    })

@login_required
def cancel_interview(request, pk):
    interview = get_object_or_404(Applicant, pk=pk, user=request.user)
    
    if request.method == 'POST':
        interview.status = 'canceled'
        interview.cancellation_reason = request.POST.get('cancellation_reason', '')
        interview.canceled_by = request.user
        interview.canceled_at = timezone.now()
        interview.save()
        
        # Send cancellation email
        send_cancellation_email(interview)
        
        messages.success(request, f'Interview with {interview.first_name} {interview.last_name} has been canceled successfully.')
        return redirect('exams:student_dashboard')
    
    return render(request, 'exams/cancel_interview.html', {'interview': interview})

@login_required
def reschedule_interview(request, pk):
    interview = get_object_or_404(Applicant, pk=pk, user=request.user)
    
    if request.method == 'POST':
        form = RescheduleInterviewForm(request.POST, instance=interview)
        if form.is_valid():
            updated_interview = form.save(commit=False)
            updated_interview.confirmed = False
            updated_interview.save()
            
            # Send rescheduling email
            send_reschedule_email(updated_interview)
            
            messages.success(request, 'Interview rescheduled successfully!')
            return redirect('exams:view_interview', pk=interview.pk)
    else:
        form = RescheduleInterviewForm(instance=interview)
    
    return render(request, 'exams/reschedule_interview.html', {
        'form': form,
        'interview': interview
    })


def join_interview(request, interview_id):
    interview = get_object_or_404(Applicant, interview_id=interview_id)
    
    # Check if interview is scheduled and not in past
    if interview.status != 'scheduled' or interview.interview_date < timezone.now().date():
        messages.error(request, 'This interview is not currently available.')
        return redirect('student_dashboard')
    
    return render(request, 'exams/join_interview.html', {'interview': interview})

from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Applicant
from .serializers import (
    ApplicantSerializer, 
    InterviewScheduleSerializer,
    InterviewFeedbackSerializer,
    InterviewRescheduleSerializer
)
from django.shortcuts import get_object_or_404
from django.utils import timezone
import uuid
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import datetime

class InterviewScheduleView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = InterviewScheduleSerializer(data=request.data)
        if serializer.is_valid():
            # Generate interview ID and Google Meet link
            interview_id = uuid.uuid4()
            google_meet_link = self.create_google_meet(serializer.validated_data)
            
            # Create applicant
            applicant = Applicant.objects.create(
                user=request.user,
                interview_id=interview_id,
                interview_link=google_meet_link,
                **serializer.validated_data
            )
            
            # Send confirmation email with calendar invite
            self.send_confirmation_email(applicant)
            
            return Response({
                'success': True,
                'interview': ApplicantSerializer(applicant, context={'request': request}).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def create_google_meet(self, data):
        """Create a Google Meet and return the join link"""
        try:
            # Set up Google Calendar API credentials
            creds = Credentials(
                token=settings.GOOGLE_API_TOKEN,
                refresh_token=settings.GOOGLE_API_REFRESH_TOKEN,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_API_CLIENT_ID,
                client_secret=settings.GOOGLE_API_CLIENT_SECRET
            )
            
            if creds.expired:
                creds.refresh(Request())
            
            service = build('calendar', 'v3', credentials=creds)
            
            # Convert date and time to datetime object
            interview_datetime = datetime.datetime.strptime(
                f"{data['interview_date']} {data['interview_time']}",
                "%Y-%m-%d %H:%M:%S"
            )
            
            # Create calendar event with Google Meet
            event = {
                'summary': 'Mock Interview Session',
                'description': f"Mock interview for {data['first_name']} {data['last_name']}",
                'start': {
                    'dateTime': interview_datetime.isoformat(),
                    'timeZone': 'UTC',
                },
                'end': {
                    'dateTime': (interview_datetime + datetime.timedelta(minutes=45)).isoformat(),
                    'timeZone': 'UTC',
                },
                'conferenceData': {
                    'createRequest': {
                        'requestId': str(uuid.uuid4()),
                        'conferenceSolutionKey': {
                            'type': 'hangoutsMeet'
                        }
                    }
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 24 * 60},  # 1 day before
                        {'method': 'popup', 'minutes': 30},       # 30 minutes before
                    ],
                }
            }
            
            event = service.events().insert(
                calendarId='primary',
                body=event,
                conferenceDataVersion=1
            ).execute()
            
            return event.get('hangoutLink')
            
        except Exception as e:
            logger.error(f"Error creating Google Meet: {str(e)}")
            # Fallback to your own link if Google Meet fails
            return f"{settings.BASE_URL}/api/interview/{interview_id}/join/"
    
    def send_confirmation_email(self, applicant):
        subject = 'Your Mock Interview Has Been Scheduled'
        
        # Calculate reminder time (30 minutes before)
        interview_datetime = datetime.datetime.strptime(
            f"{applicant.interview_date} {applicant.interview_time}",
            "%Y-%m-%d %H:%M:%S"
        )
        reminder_time = interview_datetime - datetime.timedelta(minutes=30)
        
        message = render_to_string('emails/interview_confirmation.html', {
            'applicant': applicant,
            'interview_link': applicant.interview_link,
            'reminder_time': reminder_time.strftime("%Y-%m-%d %H:%M"),
            'calendar_link': self.generate_calendar_link(applicant)
        })
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [applicant.email],
            fail_silently=False,
            html_message=message
        )
    
    def generate_calendar_link(self, applicant):
        """Generate Add to Calendar links"""
        interview_datetime = datetime.datetime.strptime(
            f"{applicant.interview_date} {applicant.interview_time}",
            "%Y-%m-%d %H:%M:%S"
        )
        end_datetime = interview_datetime + datetime.timedelta(minutes=45)
        
        # Google Calendar link
        google_url = (
            "https://www.google.com/calendar/render"
            "?action=TEMPLATE"
            f"&text=Mock+Interview+Session"
            f"&dates={interview_datetime.strftime('%Y%m%dT%H%M%S')}/{end_datetime.strftime('%Y%m%dT%H%M%S')}"
            f"&details=Your+mock+interview+session.+Join+link:+{applicant.interview_link}"
            f"&location={applicant.interview_link}"
            "&sf=true"
            "&output=xml"
        )
        
        return google_url


class InterviewDetailView(generics.RetrieveAPIView):
    serializer_class = ApplicantSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'
    
    def get_queryset(self):
        return Applicant.objects.filter(user=self.request.user)

class InterviewFeedbackView(generics.UpdateAPIView):
    serializer_class = InterviewFeedbackSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'
    
    def get_queryset(self):
        return Applicant.objects.filter(user=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(status='completed')
        self.send_feedback_email(serializer.instance)
    
    def send_feedback_email(self, applicant):
        subject = 'Your Interview Feedback'
        message = render_to_string('emails/interview_feedback.html', {
            'applicant': applicant
        })
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [applicant.email],
            fail_silently=False,
            html_message=message
        )

class InterviewCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        applicant = get_object_or_404(Applicant, pk=pk, user=request.user)
        applicant.status = 'canceled'
        applicant.save()
        
        # Send cancellation email
        self.send_cancellation_email(applicant)
        
        return Response({
            'success': True,
            'message': 'Interview has been canceled successfully.'
        })
    
    def send_cancellation_email(self, applicant):
        subject = 'Your Interview Has Been Canceled'
        message = render_to_string('emails/interview_cancellation.html', {
            'applicant': applicant
        })
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [applicant.email],
            fail_silently=False,
            html_message=message
        )

class InterviewRescheduleView(generics.UpdateAPIView):
    serializer_class = InterviewRescheduleSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'pk'
    
    def get_queryset(self):
        return Applicant.objects.filter(user=self.request.user)
    
    def perform_update(self, serializer):
        applicant = serializer.save(confirmed=False)
        self.send_reschedule_email(applicant)
    
    def send_reschedule_email(self, applicant):
        subject = 'Your Interview Has Been Rescheduled'
        message = render_to_string('emails/interview_reschedule.html', {
            'applicant': applicant
        })
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [applicant.email],
            fail_silently=False,
            html_message=message
        )

class InterviewJoinView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, interview_id):
        applicant = get_object_or_404(Applicant, interview_id=interview_id, user=request.user)
        
        if not applicant.is_upcoming():
            return Response({
                'error': 'This interview is not currently available.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'interview': ApplicantSerializer(applicant, context={'request': request}).data,
            'join_url': applicant.interview_link
        })

class InterviewListView(generics.ListAPIView):
    serializer_class = ApplicantSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Applicant.objects.filter(user=self.request.user).order_by('-interview_date')





def send_feedback_email(interview):
    subject = 'Your Interview Feedback'
    html_message = render_to_string('emails/interview_feedback.html', {
        'interview': interview
    })
    plain_message = strip_tags(html_message)
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [interview.email],
        html_message=html_message
    )



def send_cancellation_email(interview):
    subject = 'Interview Cancellation Confirmation'
    html_message = render_to_string('emails/interview_cancellation.html', {
        'interview': interview
    })
    plain_message = strip_tags(html_message)
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [interview.email],
        html_message=html_message
    )

def send_reschedule_email(interview):
    subject = 'Interview Rescheduled'
    html_message = render_to_string('emails/interview_reschedule.html', {
        'interview': interview
    })
    plain_message = strip_tags(html_message)
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [interview.email],
        html_message=html_message
    )


from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse
from .forms import (
    ProfileUpdateForm,
    CustomPasswordChangeForm,
    NotificationSettingsForm,
    PreferencesForm
)
from .models import Profile
from .utils import get_active_sessions, terminate_active_session

@login_required
def profile_settings(request):
    requested_tab = request.GET.get('tab', 'basic')
    active_tab = requested_tab if requested_tab in {
        'basic', 'notifications', 'career', 'preferences'
    } else 'basic'
    user_profile = request.user.profile
    # Initialize forms with instance
    profile_form = ProfileUpdateForm(instance=user_profile)
    password_form = CustomPasswordChangeForm(request.user)
    notification_form = NotificationSettingsForm(instance=user_profile)
    preferences_form = PreferencesForm(instance=user_profile)
    career_preferences_form = CareerLearningPreferencesForm(instance=user_profile)
    from careers.choices import LEVEL_CHOICES
    from careers.selection import recommend_learning_path
    recommended_path = recommend_learning_path(user_profile.experience_band)
    recommended_path_label = dict(LEVEL_CHOICES).get(recommended_path, 'Fresher')
    context = {
        'active_tab': active_tab,
        'profile_form': profile_form,
        'password_form': password_form,
        'notification_form': notification_form,
        'preferences_form': preferences_form,
        'career_preferences_form': career_preferences_form,
        'recommended_path_label': recommended_path_label,
        'active_sessions': get_active_sessions(request.user, request.session.session_key)
    }
    return render(request, 'exams/profile_settings.html', context)

@login_required
@require_POST
def update_profile(request):
    form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
    if form.is_valid():
        form.save()
        messages.success(request, 'Profile updated successfully.')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")
    return redirect(f"{reverse('exams:profile_settings')}?tab=basic")


@login_required
@require_POST
def update_career_preferences(request):
    """Save a learner's explicit role, experience, and learning-path choices."""
    form = CareerLearningPreferencesForm(request.POST, instance=request.user.profile)
    if form.is_valid():
        profile = form.save()
        messages.success(request, 'Career learning preferences saved.')
        if profile.career_role and profile.experience_band:
            from careers.selection import effective_learning_path

            level = effective_learning_path(
                profile.experience_band, profile.learning_path)
            return redirect(
                'careers:level_role_detail',
                slug=profile.career_role.slug,
                level=level,
            )
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f'{field}: {error}')
    return redirect(f"{reverse('exams:profile_settings')}?tab=career")

@login_required
@require_POST
def delete_profile_photo(request):
    profile = request.user.profile
    if profile.photo:
        profile.photo.delete(save=False)
        profile.save(update_fields=['photo'])
        messages.success(request, 'Profile photo removed.')
    return redirect(f"{reverse('exams:profile_settings')}?tab=basic")


@login_required
@require_POST
def change_password(request):
    form = CustomPasswordChangeForm(request.user, request.POST)
    if form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, 'Password changed successfully!')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")
    return redirect(f"{reverse('exams:profile_settings')}?tab=security")

@login_required
@require_POST
def update_notifications(request):
    form = NotificationSettingsForm(request.POST, instance=request.user.profile)
    if form.is_valid():
        form.save()
        messages.success(request, 'Notification preferences saved.')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")
    return redirect(f"{reverse('exams:profile_settings')}?tab=notifications")


@login_required
@require_POST
def update_preferences(request):
    form = PreferencesForm(request.POST, instance=request.user.profile)
    if form.is_valid():
        form.save()
        messages.success(request, 'Preferences saved.')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(request, f"{field}: {error}")
    return redirect(f"{reverse('exams:profile_settings')}?tab=preferences")


@login_required
@require_POST
def terminate_session(request, session_id):
    if terminate_active_session(request.user, session_id, request.session.session_key):
        messages.success(request, 'The selected session was signed out.')
    else:
        messages.error(request, 'That session is unavailable or cannot be signed out.')
    return redirect(f"{reverse('exams:profile_settings')}?tab=security")
def edit_interview(request, pk):
    interview = get_object_or_404(Applicant, pk=pk)
    if request.method == 'POST':
        interview.interview_type = request.POST.get('interview_type')
        interview.interview_date = request.POST.get('interview_date')
        interview.interview_time = request.POST.get('interview_time')
        interview.status = request.POST.get('status')
        interview.save()
        return redirect('exams:interviews_dashboard')
    return render(request, 'exams/edit_interview.html', {'interview': interview})

from django.shortcuts import render, redirect, get_object_or_404
from .models import Applicant, InterviewFeedback
from .forms import InterviewFeedbackForm

def interview_feedback(request, pk):
    interview = get_object_or_404(Applicant, pk=pk)

    feedback = getattr(interview, 'interview_feedback', None)
    overall_score_percent = 0
    if feedback and feedback.overall_score is not None:
        overall_score_percent = feedback.overall_score * 20  # since score is out of 5, times 20 = percent out of 100


    if request.method == 'POST':
        form = InterviewFeedbackForm(request.POST, instance=feedback)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.interview = interview
            feedback.evaluator = request.user
            feedback.save()
            interview.status = 'completed'
            interview.save()
            messages.success(request, 'Feedback submitted successfully!')
            return redirect('exams:interviews_dashboard')
    else:
        form = InterviewFeedbackForm(instance=feedback)


    context = {
        'interview': interview,
        'form': form,
        'overall_score_percent': overall_score_percent,
    }
    return render(request, 'exams/interview_feedback.html', context)


@login_required
@user_passes_test(lambda u: u.groups.filter(name='Interviewers').exists())
def interviewer_dashboard(request):
    # Get interviews assigned to this interviewer
    assigned_interviews = Applicant.objects.filter(
        interviewer=request.user,
        status='scheduled'
    ).order_by('interview_date')
    
    # Get completed interviews
    completed_interviews = Applicant.objects.filter(
        interviewer=request.user,
        status='completed'
    ).order_by('-completed_date')
    
    # Get upcoming interviews (next 7 days)
    upcoming_interviews = assigned_interviews.filter(
        interview_date__range=[
            timezone.now().date(),
            timezone.now().date() + timedelta(days=7)
        ]
    )
    
    return render(request, 'exams/interviewer_dashboard.html', {
        'assigned_interviews': assigned_interviews,
        'completed_interviews': completed_interviews,
        'upcoming_interviews': upcoming_interviews,
        'today': timezone.now().date()
    })
@login_required
@user_passes_test(lambda u: u.is_superuser)
def assign_interviewer(request, object_id):
    interview = get_object_or_404(Applicant, pk=object_id)
    
    # Debug print
    print("Available interviewers:", Interviewer.objects.filter(is_active=True).values_list('user__first_name', flat=True))
    
    if request.method == 'POST':
        form = AssignInterviewerForm(request.POST, instance=interview)
        if form.is_valid():
            interview = form.save(commit=False)
            interview.assigned_date = timezone.now()
            interview.save()
            messages.success(request, 'Interviewer assigned successfully!')
            return redirect('admin:exams_applicant_changelist')
    else:
        form = AssignInterviewerForm(instance=interview)
    
    return render(request, 'admin/assign_interviewer.html', {
        'form': form,
        'interview': interview,
        'opts': Applicant._meta,
        'title': 'Assign Interviewer'
    })
def send_interview_assignment_email(interview):
    subject = f'New Interview Assignment: {interview.first_name} {interview.last_name}'
    context = {
        'interview': interview,
        'interviewer': interview.interviewer,
        'interview_date': interview.interview_date.strftime("%B %d, %Y"),
        'interview_time': interview.interview_time,
        'interview_link': interview.interview_link,
        'admin_url': settings.ADMIN_SITE_URL
    }
    
    html_message = render_to_string('emails/interview_assignment.html', context)
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [interview.interviewer.email],
        html_message=html_message,
        fail_silently=False
    )
# django rest framework views
# Authentication API  views                                                       # Authentication api views
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.contrib.auth.password_validation import validate_password
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import re
@api_view(['POST'])
@permission_classes([AllowAny])
def api_signup(request):
    """
    User registration API with validation
    """
    serializer = SignupSerializer(data=request.data)
    
    # Custom validation
    errors = {}
    username = request.data.get('username', '')
    email = request.data.get('email', '')
    password = request.data.get('password', '')
    password2 = request.data.get('password2', '')
    
    # Username validation
    if len(username) < 4:
        errors['username'] = 'Username must be at least 4 characters long'
    if not re.match("^[a-zA-Z0-9_]+$", username):
        errors['username'] = 'Username can only contain letters, numbers and underscores'
    
    # Email validation
    try:
        validate_email(email)
    except ValidationError:
        errors['email'] = 'Enter a valid email address'
    
    # Password validation
    if password != password2:
        errors['password'] = 'Passwords do not match'
    try:
        validate_password(password)
    except ValidationError as e:
        errors['password'] = list(e.messages)
    
    if errors:
        return Response({'errors': errors}, status=status.HTTP_400_BAD_REQUEST)
    
    if serializer.is_valid():
        user = serializer.save()
        return Response(
            {"message": "User registered successfully.", "user_id": user.id},
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
@api_view(['POST'])
@permission_classes([AllowAny])
def api_login(request):
    """
    User login API with validation
    """
    serializer = LoginSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    username = serializer.validated_data['username']
    password = serializer.validated_data['password']
    
    # Check if user exists
    user = authenticate(request, username=username, password=password)
    
    if user is None:
        return Response(
            {"error": "Invalid credentials"}, 
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    if not user.is_active:
        return Response(
            {"error": "Account is disabled"}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    login(request, user)
    
    # Generate or get token if you're using token authentication
    return Response({
        "message": "Login successful",
        "user_id": user.id,
        "username": user.username,
        "email": user.email
    })
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_logout(request):
    """
    User logout API
    """
    logout(request)
    return Response({"message": "Logged out successfully"})
# Profile API views                                                            # profile api views 
# views.py
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from .serializers import ProfileSerializer
class ProfileAPIView(RetrieveUpdateAPIView):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]
    def get_object(self):
        return self.request.user.profile
    def perform_update(self, serializer):
        instance = serializer.save()
        
        # Handle file upload for profile photo
        if 'photo' in self.request.FILES:
            instance.photo = self.request.FILES['photo']
            instance.save()
        
        return instance
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_password(request):
    """
    Password change endpoint with validation
    """
    user = request.user
    serializer = CustomPasswordChangeForm(user=user, data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {"errors": serializer.errors}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate new password
    new_password = serializer.validated_data['new_password']
    try:
        validate_password(new_password)
    except ValidationError as e:
        return Response(
            {"password_errors": list(e.messages)}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if new password is different from old
    if serializer.validated_data['new_password'] == serializer.validated_data['old_password']:
        return Response(
            {"error": "New password must be different from old password"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = serializer.save()
    update_session_auth_hash(request, user)
    
    return Response({"message": "Password updated successfully"})
#  Exam API views                                                                                   # exam api views
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Exam, Category, ExamAttempt, Question, Answer, UserAnswer, Bookmark
from .serializers import (
    ExamSerializer, CategorySerializer, 
    ExamDetailSerializer, QuestionSerializer,
    AnswerSerializer, ExamAttemptSerializer,
    UserAnswerSerializer
)
class CategoryListAPIView(ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
class ExamListAPIView(ListAPIView):
    serializer_class = ExamSerializer
    permission_classes = [AllowAny]
    def get_queryset(self):
        filter_slug = self.request.query_params.get('filter', 'all')
        if filter_slug == 'all':
            return Exam.objects.all()
        return Exam.objects.filter(category__slug=filter_slug)
class ExamDetailAPIView(RetrieveAPIView):
    queryset = Exam.objects.all()
    serializer_class = ExamDetailSerializer
    lookup_field = 'slug'
    lookup_url_kwarg = 'exam_slug'
    permission_classes = [IsAuthenticated]
class StartExamAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, exam_slug):
        exam = get_object_or_404(Exam, slug=exam_slug)
        
        # Check for existing incomplete attempt
        attempt = ExamAttempt.objects.filter(
            user=request.user,
            exam=exam,
            completed_at__isnull=True
        ).first()
        
        if not attempt:
            attempt = ExamAttempt.objects.create(
                user=request.user,
                exam=exam
            )
        
        return Response({
            "attempt_id": attempt.id,
            "message": "Exam started",
            "first_question_url": reverse(
                'exams:api_exam_question',
                kwargs={
                    'exam_slug': exam.slug,
                    'level': 'beginner',
                    'set_number': 1,
                    'question_order': 1
                },
                request=request
            )
        })
    

class ExamQuestionAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, exam_slug, level, set_number, question_order):
        exam = get_object_or_404(Exam, slug=exam_slug)
        question = get_object_or_404(
            Question.objects.filter(
                exam=exam,
                level=level,
                set_number=set_number
            ).order_by('order'),
            order=question_order
        )
        
        attempt = ExamAttempt.objects.filter(
            user=request.user,
            exam=exam,
            completed_at__isnull=True
        ).first()
        
        if not attempt:
            return Response(
                {"error": "No active exam attempt found"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user_answer = UserAnswer.objects.get(attempt=attempt, question=question)
            selected_answer = user_answer.selected_answer_id
        except UserAnswer.DoesNotExist:
            selected_answer = None
        
        answers = AnswerSerializer(question.answers.all(), many=True).data
        question_data = QuestionSerializer(question).data
        
        return Response({
            "question": question_data,
            "answers": answers,
            "selected_answer": selected_answer,
            "current_question": question_order,
            "total_questions": question.exam.questions.count()
        })
    def post(self, request, exam_slug, level, set_number, question_order):
        exam = get_object_or_404(Exam, slug=exam_slug)
        question = get_object_or_404(
            Question.objects.filter(
                exam=exam,
                level=level,
                set_number=set_number
            ).order_by('order'),
            order=question_order
        )
        
        attempt = ExamAttempt.objects.filter(
            user=request.user,
            exam=exam,
            completed_at__isnull=True
        ).first()
        
        if not attempt:
            return Response(
                {"error": "No active exam attempt found"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        answer_id = request.data.get('selected_answer')
        if not answer_id:
            return Response(
                {"error": "Please select an answer"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            selected_answer = Answer.objects.get(id=answer_id, question=question)
        except Answer.DoesNotExist:
            return Response(
                {"error": "Invalid answer selection"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Save or update user answer
        UserAnswer.objects.update_or_create(
            attempt=attempt,
            question=question,
            defaults={
                'selected_answer': selected_answer,
                'is_correct': selected_answer.is_correct
            }
        )
        
        # Check if there's a next question
        next_question = Question.objects.filter(
            exam=exam,
            level=level,
            set_number=set_number,
            order__gt=question_order
        ).order_by('order').first()
        
        if next_question:
            return Response({
                "next_question_url": reverse(
                    'exams:api_exam_question',
                    kwargs={
                        'exam_slug': exam.slug,
                        'level': level,
                        'set_number': set_number,
                        'question_order': next_question.order
                    },
                    request=request
                )
            })
        else:
            # Finish the exam
            total_questions = Question.objects.filter(
                exam=exam,
                level=level,
                set_number=set_number
            ).count()
            
            correct_answers = UserAnswer.objects.filter(
                attempt=attempt,
                is_correct=True
            ).count()
            
            attempt.score = round(correct_answers / total_questions, 2)
            attempt.completed_at = timezone.now()
            attempt.save()
            
            return Response({
                "result_url": reverse(
                    'exams:api_exam_result',
                    kwargs={'attempt_id': attempt.id},
                    request=request
                ),
                "message": "Exam completed"
            })
class ExamResultAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, attempt_id):
        attempt = get_object_or_404(ExamAttempt, id=attempt_id, user=request.user)
        user_answers = UserAnswer.objects.filter(
            attempt=attempt
        ).select_related('question', 'selected_answer')
        
        results = []
        correct_count = 0
        
        for ua in user_answers:
            correct_answer = ua.question.answers.filter(is_correct=True).first()
            results.append({
                "question": ua.question.question_text,
                "selected_answer": ua.selected_answer.answer_text if ua.selected_answer else None,
                "correct_answer": correct_answer.answer_text if correct_answer else None,
                "is_correct": ua.is_correct
            })
            if ua.is_correct:
                correct_count += 1
        
        return Response({
            "exam": attempt.exam.title,
            "score": attempt.score,
            "correct_answers": correct_count,
            "total_questions": user_answers.count(),
            "results": results,
            "completed_at": attempt.completed_at
        })
    
# Mock Interview API views                                                              # mock interview api views
# views.py
from rest_framework.generics import (
    ListCreateAPIView, RetrieveUpdateDestroyAPIView, 
    ListAPIView, RetrieveAPIView
)
from rest_framework.exceptions import PermissionDenied
from .models import Applicant, Interviewer
from .serializers import (
    InterviewSerializer, InterviewerSerializer,
    InterviewFeedbackSerializer, RescheduleInterviewSerializer
)
from datetime import datetime, timedelta
import uuid
class InterviewListCreateAPIView(ListCreateAPIView):
    serializer_class = InterviewSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        # Users can only see their own interviews
        return Applicant.objects.filter(user=self.request.user)
    def perform_create(self, serializer):
        # Validate interview date is in future
        interview_date = serializer.validated_data.get('interview_date')
        if interview_date and interview_date < datetime.now().date():
            raise ValidationError("Interview date must be in the future")
        
        # Generate interview ID and link
        interview_id = uuid.uuid4()
        interview_link = f"{settings.BASE_URL}/interview/{interview_id}/join/"
        
        # Save with user and generated fields
        interview = serializer.save(
            user=self.request.user,
            interview_id=interview_id,
            interview_link=interview_link,
            status='scheduled'
        )
        
        # Send confirmation email
        send_interview_confirmation(interview)
class InterviewDetailAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = InterviewSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        return Applicant.objects.filter(user=self.request.user)
    def perform_update(self, serializer):
        instance = serializer.save()
        
        # If rescheduling, send notification
        if 'interview_date' in serializer.validated_data or 'interview_time' in serializer.validated_data:
            send_reschedule_email(instance)
    
    def perform_destroy(self, instance):
        # Don't actually delete, just cancel
        instance.status = 'canceled'
        instance.save()
        send_cancellation_email(instance)
class InterviewFeedbackAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        interview = get_object_or_404(Applicant, pk=pk)
        
        # Check if user owns the interview or is the interviewer
        if interview.user != request.user and interview.interviewer != request.user:
            raise PermissionDenied("You don't have permission to provide feedback for this interview")
        
        serializer = InterviewFeedbackSerializer(interview, data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        updated_interview = serializer.save(status='completed')
        send_feedback_email(updated_interview)
        
        return Response(InterviewSerializer(updated_interview).data)
    
class RescheduleInterviewAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk):
        interview = get_object_or_404(Applicant, pk=pk, user=request.user)
        
        serializer = RescheduleInterviewSerializer(interview, data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate new date is in future
        new_date = serializer.validated_data.get('interview_date', interview.interview_date)
        if new_date < datetime.now().date():
            return Response(
                {"error": "Interview date must be in the future"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        updated_interview = serializer.save(confirmed=False)
        send_reschedule_email(updated_interview)
        
        return Response(InterviewSerializer(updated_interview).data)
    
class InterviewerListAPIView(ListAPIView):
    queryset = Interviewer.objects.filter(is_active=True)
    serializer_class = InterviewerSerializer
    permission_classes = [IsAuthenticated]
    def get_queryset(self):
        # Only show interviewers available in the next 7 days
        return super().get_queryset().filter(
            assigned_applicants__interview_date__gte=datetime.now().date(),
            assigned_applicants__interview_date__lte=datetime.now().date() + timedelta(days=7)
        ).annotate(
            available_slots=models.Count('assigned_applicants')
        ).filter(
            available_slots__lt=models.F('max_interviews_per_day')
        )
class InterviewerDashboardAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        if not request.user.groups.filter(name='Interviewers').exists():
            raise PermissionDenied("Only interviewers can access this dashboard")
        
        interviewer = get_object_or_404(Interviewer, user=request.user)
        
        # Get interviews assigned to this interviewer
        assigned_interviews = Applicant.objects.filter(
            interviewer=request.user,
            status='scheduled'
        ).order_by('interview_date')
        
        # Get completed interviews
        completed_interviews = Applicant.objects.filter(
            interviewer=request.user,
            status='completed'
        ).order_by('-completed_date')
        
        # Get upcoming interviews (next 7 days)
        upcoming_interviews = assigned_interviews.filter(
            interview_date__range=[
                timezone.now().date(),
                timezone.now().date() + timedelta(days=7)
            ]
        )
        
        return Response({
            "assigned_interviews": InterviewSerializer(assigned_interviews, many=True).data,
            "completed_interviews": InterviewSerializer(completed_interviews, many=True).data,
            "upcoming_interviews": InterviewSerializer(upcoming_interviews, many=True).data,
            "interviewer": InterviewerSerializer(interviewer).data
        })
        
#  dashboard api views                                                                      # dashboard api views
# views.py
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_student_dashboard(request):
    user = request.user
    profile = Profile.objects.get(user=user)
    attempts = ExamAttempt.objects.filter(user=user).order_by('-completed_at')
    interviews = Applicant.objects.filter(user=user)
    
    # Exam stats
    category_stats = ExamAttempt.objects.filter(user=user).values('exam__category__name').annotate(
        total=Count('id'),
        avg_score=Avg('score')
    ).order_by('exam__category__name')
    
    # Interview stats
    interview_stats = interviews.aggregate(
        total_interviews=Count('id'),
        completed_interviews=Count('id', filter=Q(status='completed')),
        avg_rating=Avg('rating')
    )
    
    # Latest activity
    latest_attempt = attempts.first()
    upcoming_interview = interviews.filter(
        interview_date__gte=timezone.now().date(),
        status='scheduled'
    ).order_by('interview_date').first()
    
    return Response({
        "profile": ProfileSerializer(profile).data,
        "exam_stats": {
            "total_exams": attempts.count(),
            "avg_score": attempts.aggregate(avg=Avg('score'))['avg'] or 0,
            "category_stats": list(category_stats),
            "latest_attempt": ExamAttemptSerializer(latest_attempt).data if latest_attempt else None
        },
        "interview_stats": interview_stats,
        "upcoming_interview": InterviewSerializer(upcoming_interview).data if upcoming_interview else None,
        "recent_activity": {
            "exams": ExamAttemptSerializer(attempts[:3], many=True).data,
            "interviews": InterviewSerializer(interviews.order_by('-interview_date')[:3], many=True).data
        }
    })


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import Exam, Category
from .serializers import ExamSerializer, CategorySerializer

@api_view(['GET'])
@permission_classes([AllowAny])
def api_browse_exams(request):
    """
    List all exams, optionally filter by category or level.
    """
    category_slug = request.GET.get('category')
    level = request.GET.get('level')
    exams = Exam.objects.all()
    if category_slug:
        exams = exams.filter(category__slug=category_slug)
    if level:
        exams = exams.filter(level__iexact=level)
    serializer = ExamSerializer(exams, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def api_how_it_works(request):
    """
    Returns information about how the platform works.
    """
    data = {
        "steps": [
            "1. Browse and select an exam category.",
            "2. Choose your skill level and set.",
            "3. Attempt the exam questions.",
            "4. Submit your answers and view results.",
            "5. Track your progress on your dashboard."
        ],
        "note": "You can also schedule mock interviews for real-world practice."
    }
    return Response(data)

@api_view(['GET'])
@permission_classes([AllowAny])
def api_all_categories(request):
    """
    List all exam categories.
    """
    categories = Category.objects.all()
    serializer = CategorySerializer(categories, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def api_programming_exams(request):
    """
    List all programming exams.
    """
    exams = Exam.objects.filter(category__slug='programming')
    serializer = ExamSerializer(exams, many=True)
    return Response(serializer.data)

@api_view(['GET'])
@permission_classes([AllowAny])
def api_webpage_exams(request):
    """
    List all webpage exams.
    """
    exams = Exam.objects.filter(category__slug='webpage')
    serializer = ExamSerializer(exams, many=True)
    return Response(serializer.data)


class ExamResultAnswersAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, attempt_id):
        user_answers = UserAnswer.objects.filter(attempt_id=attempt_id, attempt__user=request.user)
        data = UserAnswerSerializer(user_answers, many=True).data
        return Response(data)

class PerformanceByTypeAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, attempt_id):
        # Example logic, adjust as needed
        user_answers = UserAnswer.objects.filter(attempt_id=attempt_id, attempt__user=request.user)
        types = ['Multiple Choice', 'True/False', 'Scenario']
        result = []
        for t in types:
            answers = user_answers.filter(question__type=t)
            percent = int(100 * answers.filter(is_correct=True).count() / answers.count()) if answers.exists() else 0
            result.append({"type": t, "percent": percent})
        return Response(result)

class BookmarkQuestionAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        question_id = request.data.get('question_id')
        Bookmark.objects.get_or_create(user=request.user, question_id=question_id)
        return Response({"status": "bookmarked"})
    

class RetakeExamAPIView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, exam_slug):
        exam = Exam.objects.get(slug=exam_slug)
        attempt = ExamAttempt.objects.create(user=request.user, exam=exam)
        return Response({"attempt_id": attempt.id})
    

# study guide , your progress, and sample quesions buttons in exam detail page

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Exam

def study_guide(request):
    exam_slug = request.GET.get('exam')
    exam = None
    if exam_slug:
        exam = Exam.objects.filter(slug=exam_slug).select_related('category').first()
        if exam is None:
            return exam_not_available(
                request,
                'This study guide is not available',
                'The exam connected to this guide may have been removed or is not currently published. Browse the available exams to choose another subject.',
            )
    return render(request, 'exams/study_guide.html', {'exam': exam})

from django.db.models import Avg, Count, Max, Q

@login_required
def user_analytics(request):
    completed = ExamAttempt.objects.filter(
        user=request.user, completed_at__isnull=False,
    ).select_related('exam', 'exam__category')
    scored = completed.exclude(score__isnull=True)
    summary = scored.aggregate(
        total_attempts=Count('id'),
        average_score=Avg('score'),
        best_score=Max('score'),
    )
    total_attempts = summary['total_attempts'] or 0
    average_score = summary['average_score']
    best_score = summary['best_score']
    recent_attempts = completed.order_by('-completed_at')[:8]
    exam_breakdown = scored.values(
        'exam__title', 'exam__slug', 'exam__category__name',
    ).annotate(
        attempt_count=Count('id'),
        average_score=Avg('score'),
        latest_attempt=Max('completed_at'),
    ).order_by('-latest_attempt')[:6]
    review_areas = list(
        UserAnswer.objects.filter(
            attempt__user=request.user,
            attempt__completed_at__isnull=False,
        ).values(
            'question__category__name', 'question__level',
        ).annotate(
            answer_count=Count('id'),
            correct_count=Count('id', filter=Q(is_correct=True)),
        ).order_by('question__category__name', 'question__level')
    )
    for area in review_areas:
        area['accuracy'] = round(area['correct_count'] * 100 / area['answer_count']) if area['answer_count'] else 0
    review_areas.sort(key=lambda area: (area['accuracy'], -area['answer_count']))
    return render(request, 'exams/user_analytics.html', {
        'total_attempts': total_attempts,
        'average_score': average_score,
        'best_score': best_score,
        'recent_attempts': recent_attempts,
        'exam_breakdown': exam_breakdown,
        'review_areas': review_areas[:5],
    })

def sample_questions(request, exam_slug):
    exam = Exam.objects.filter(slug=exam_slug).first()
    if exam is None:
        return exam_not_available(
            request,
            'Sample questions are not available',
            'This exam may have been removed or is not currently published. Browse the available exams to find practice that is ready now.',
        )
    # Example: Get 3 sample questions (replace with real logic)
    samples = [
        {"question": "What is the output of print(2 ** 3)?", "answer": "8"},
        {"question": "Which keyword is used to define a function in Python?", "answer": "def"},
        {"question": "What does HTML stand for?", "answer": "HyperText Markup Language"},
    ]
    return render(request, 'exams/sample_questions.html', {'exam': exam, 'samples': samples})

 
 # api_views for  study guide , your progress, and sample quesions buttons in exam detail page

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import NotFound
from .models import Exam
from .serializers import StudyGuideSerializer, UserProgressSerializer, SampleQuestionSerializer

class StudyGuideAPI(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        slug = request.query_params.get('slug')
        if not slug:
            raise NotFound("Missing 'slug' query parameter.")
        
        try:
            exam = Exam.objects.get(slug=slug)
        except Exam.DoesNotExist:
            raise NotFound("Exam not found.")

        serializer = StudyGuideSerializer(exam)
        return Response(serializer.data)

class UserProgressAPI(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        # Replace with real logic
        progress = 60
        serializer = UserProgressSerializer({'progress': progress})
        return Response(serializer.data)

class SampleQuestionsAPI(APIView):
    permission_classes = [AllowAny]
    def get(self, request, exam_slug):
        # Replace with real logic
        samples = [
            {"question": "What is the output of print(2 ** 3)?", "answer": "8"},
            {"question": "Which keyword is used to define a function in Python?", "answer": "def"},
            {"question": "What does HTML stand for?", "answer": "HyperText Markup Language"},
        ]
        serializer = SampleQuestionSerializer(samples, many=True)
        return Response(serializer.data)
