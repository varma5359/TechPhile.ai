from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
import subprocess
import tempfile
import os
import sys
from .models import Problem, Submission, UserProfile
import requests
from django.conf import settings




def home(request):
    """Home page view"""
    recent_problems = Problem.objects.all()[:6]
    return render(request, 'coding_temp/coding/home.html', {'recent_problems': recent_problems})

def problem_list(request):
    """Problem listing page"""
    problems = Problem.objects.all().order_by('-id')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        problems = problems.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__icontains=search_query)
        )
    
    # Filter by difficulty
    difficulty = request.GET.get('difficulty', '')
    if difficulty:
        problems = problems.filter(difficulty=difficulty)
    
    # Annotate each problem with user status and time taken
    user_status = {}
    if request.user.is_authenticated:
        user_subs = Submission.objects.filter(user=request.user)
        for sub in user_subs.order_by('problem', '-submitted_at'):
            if sub.problem_id not in user_status:
                if sub.status == 'Accepted':
                    user_status[sub.problem_id] = {
                        'status': 'Complete',
                        'time_taken': round(sub.execution_time / 1000, 2) if sub.execution_time else None  # seconds
                    }
                else:
                    user_status[sub.problem_id] = {
                        'status': 'Pending',
                        'time_taken': round(sub.execution_time / 1000, 2) if sub.execution_time else None
                    }
    # Pagination
    paginator = Paginator(problems, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Attach status and time_taken to each problem
    for problem in page_obj:
        if request.user.is_authenticated and problem.id in user_status:
            problem.user_status = user_status[problem.id]['status']
            problem.time_taken = user_status[problem.id]['time_taken']
        else:
            problem.user_status = 'Not Started'
            problem.time_taken = None

    return render(request, 'coding_temp/coding/problem_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'difficulty': difficulty
    })


def problem_detail(request, slug):
    problem = get_object_or_404(Problem, slug=slug)
    show_solution = False
    failed_attempts = 0
    has_solved = False
    
    if request.user.is_authenticated:
        failed_attempts = Submission.objects.filter(
            user=request.user,
            problem=problem,
        ).exclude(status='Accepted').count()
        
        has_solved = Submission.objects.filter(
            user=request.user,
            problem=problem,
            status='Accepted'
        ).exists()
        
        show_solution = failed_attempts >= 3 and not has_solved
    
    return render(request, 'coding_temp/coding/problem_detail.html', {
        'problem': problem,
        'show_solution': show_solution,
        'failed_attempts': failed_attempts,
        'has_solved': has_solved,
        
    })


from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import Problem

def problem_solution(request, problem_id):
    logger.info(f"Request received for problem {problem_id}")
    problem = get_object_or_404(Problem, id=problem_id)
    language = request.GET.get('language', 'python').lower()
    logger.info(f"Language requested: {language}")
    # Get the solution for the requested language
    solution = None
    if language == 'python':
        solution = problem.python_solution
    elif language == 'javascript':
        solution = problem.javascript_solution
    elif language == 'java':
        solution = problem.java_solution
    elif language == 'cpp':
        solution = problem.cpp_solution
    elif language == 'c':
        solution = problem.c_solution
    
    if solution:
        return JsonResponse({
            'solution': solution,
            'language': language
        })
    else:
        return JsonResponse({
            'error': 'Solution not available for this language',
            'available_languages': ['python', 'javascript', 'java', 'cpp', 'c']
        }, status=404)  

@login_required
@require_POST
def submit_code(request):

    """Handle code submission using Judge0"""
    try:
        data = json.loads(request.body)
        problem_id = data.get('problem_id')
        code = data.get('code')
        language = data.get('language')
        
        problem = get_object_or_404(Problem, id=problem_id)
        
        # Create submission
        submission = Submission.objects.create(
            user=request.user,
            problem=problem,
            code=code,
            language=language,
            status='Pending'
        )
        # Execute code using Judge0
        result = execute_code(code, language, problem.sample_input, problem.sample_output)
        logger.info(f"after result",result)

        # Safely convert values before saving
        try:
            execution_time = float(result.get('execution_time', 0))
        except (TypeError, ValueError):
            execution_time = 0
            
        try:
            memory_used = int(result.get('memory_used', 0))
        except (TypeError, ValueError):
            memory_used = 0
        
        # Update submission
        submission.status = result['status']
        submission.execution_time = execution_time
        submission.memory_used = memory_used
        submission.save()
        
        # Calculate attempt status for THIS LANGUAGE after submission
        failed_attempts = Submission.objects.filter(
            user=request.user,
            problem=problem,
            language=language  # Added language filter
        ).exclude(status='Accepted').count()
        
        has_solved = Submission.objects.filter(
            user=request.user,
            problem=problem,
            language=language,  # Added language filter
            status='Accepted'
        ).exists()
        
        show_solution = failed_attempts >= 3 and not has_solved
        
        # Update profile on success
        if result['status'] == 'Accepted':
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            if not Submission.objects.filter(
                user=request.user, 
                problem=problem,
                language=language,  # Added language filter
                status='Accepted'
            ).exclude(id=submission.id).exists():
                profile.total_solved += 1
                if problem.difficulty == 'Easy':
                    profile.easy_solved += 1
                elif problem.difficulty == 'Medium':
                    profile.medium_solved += 1
                else:
                    profile.hard_solved += 1
                profile.save()
        
        return JsonResponse({
            'status': 'success',
            'submission_id': submission.id,
            'result': result,
            'show_solution': show_solution,
            'attempts': failed_attempts,
            'has_solved': has_solved,
            'language': language  # Include language in response
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error', 
            'message': str(e)
        })
    
@login_required
def get_attempt_status(request, problem_id):
    language = request.GET.get('language', 'python')
    problem = get_object_or_404(Problem, id=problem_id)
    
    # Get counts in a single query for better performance
    attempts = Submission.objects.filter(
        user=request.user,
        problem=problem,
        language=language
    ).aggregate(
        failed_attempts=Count('id', filter=~Q(status='Accepted')),
        has_solved=Count('id', filter=Q(status='Accepted'))
    )
    
    return JsonResponse({
        'show_solution': attempts['failed_attempts'] >= 3 and not attempts['has_solved'],
        'attempts': attempts['failed_attempts'],
        'has_solved': attempts['has_solved'] > 0,
        'language': language
    })

@login_required
def get_solution(request, problem_id):
    language = request.GET.get('language', 'python')
    problem = get_object_or_404(Problem, id=problem_id)
    
    # Get language-specific solution
    solution = problem.get_solution_for_language(language)
    
    return JsonResponse({
        'solution': solution or 'No solution available for this language',
        'language': language
    })


def execute_code(code, language, sample_input, expected_output):
    """Execute code using Judge0 API"""
    try:
        # Map your language names to Judge0 language IDs
        LANGUAGE_IDS = {
            'python': 71,
            'javascript': 63,
            'java': 62,
            'cpp': 54,
            'c': 50
        }
        
        language_id = LANGUAGE_IDS.get(language.lower())
        if not language_id:
            return {
                'status': 'Unsupported Language',
                'output': f'{language} is not supported',
                'execution_time': 0
            }
        # Java-specific preprocessing
        if language.lower() == 'java':
            # Ensure the code contains a Main class
            if 'class Main' not in code:
                return {
                    'status': 'Compilation Error',
                    'output': 'Java code must contain "public class Main"',
                    'execution_time': 0
                }
        
        
        # Prepare submission data
        submission_data = {
            "source_code": code,
            "language_id": language_id,
            "stdin": sample_input,
            "expected_output": expected_output,
            "cpu_time_limit": 5,  # 5 seconds
            "memory_limit": 256000,  # 256MB
        }
        
        # Submit to Judge0
        response = requests.post(
            f"{settings.JUDGE0_API_URL}/submissions?base64_encoded=false&wait=true",
            json=submission_data,
            headers=settings.JUDGE0_HEADERS
        )
       
        response.raise_for_status()
        result = response.json()
        
        # Map Judge0 status codes to your status strings
        status_mapping = {
            3: "Accepted",  # Accepted
            4: "Wrong Answer",  # Wrong Answer
            5: "Time Limit Exceeded",
            6: "Compilation Error",
            7: "Runtime Error",
            8: "Memory Limit Exceeded",
            9: "Output Limit Exceeded",
        }
        
        status = status_mapping.get(result.get("status", {}).get("id", 7), "Runtime Error")
        
        # Safely convert time to float
        try:
            execution_time = float(result.get("time", 0)) * 1000  # Convert to milliseconds
        except (TypeError, ValueError):
            execution_time = 0
        
        # Safely convert memory to int
        try:
            memory_used = int(result.get("memory", 0))
        except (TypeError, ValueError):
            memory_used = 0
        
        return {
            'status': status,
            'output': result.get("stdout", "") or result.get("stderr", "No output"),
            'expected': expected_output,
            'execution_time': execution_time,
            'memory_used': memory_used,
        }
        
    except requests.exceptions.RequestException as e:
        return {
            'status': 'API Error',
            'output': f'Failed to connect to Judge0: {str(e)}',
            'execution_time': 0,
            'memory_used': 0
        }
    except Exception as e:
        return {
            'status': 'Runtime Error',
            'output': f'Unexpected error: {str(e)}',
            'execution_time': 0,
            'memory_used': 0
        }


@login_required
def dashboard(request):
    """User dashboard"""
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    recent_submissions = Submission.objects.filter(user=request.user).order_by('-submitted_at')[:10]
    
    return render(request, 'coding_temp/coding/dashboard.html', {
        'profile': profile,
        'recent_submissions': recent_submissions
    })

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import UserProfile
import logging

logger = logging.getLogger(__name__)

@login_required
def leaderboard(request):
    logger.debug("Entering leaderboard view")
    """Leaderboard page with current user rank always visible"""

    try:
        # Get current user's profile first (with select_related for efficiency)
        current_user_profile = UserProfile.objects.select_related('user').get(user=request.user)
        
        # Get all profiles ordered by total_solved descending (only needed fields)
        all_profiles = list(UserProfile.objects.all()
                          .order_by('-total_solved')
                          .only('user__username', 'total_solved', 'easy_solved', 
                               'medium_solved', 'hard_solved', 'avatar'))
        
        # Add rank to each profile (1-based index)
        for index, profile in enumerate(all_profiles):
            profile.rank = index + 1

        # Get top 50 profiles
        top_50_profiles = all_profiles[:50]

        # Find current user's rank
        current_user_rank = next((p.rank for p in all_profiles if p.id == current_user_profile.id), None)
        
        user_in_top_50 = current_user_profile.id in {p.id for p in top_50_profiles}

    except UserProfile.DoesNotExist:
        # Handle case where profile doesn't exist
        current_user_profile = None
        current_user_rank = None
        user_in_top_50 = False
        top_50_profiles = list(UserProfile.objects.all()
                             .order_by('-total_solved')
                             .only('user__username', 'total_solved', 'easy_solved',
                                  'medium_solved', 'hard_solved', 'avatar')[:50])
        for index, profile in enumerate(top_50_profiles):
            profile.rank = index + 1

    context = {
        'profiles': top_50_profiles,
        'current_user_profile': current_user_profile,
        'current_user_rank': current_user_rank,
        'user_in_top_50': user_in_top_50,
    }

    return render(request, 'coding_temp/coding/leaderboard.html', context)


from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.contrib.auth.models import User
from .models import Problem, Submission, UserProfile
from .serializers import (
    ProblemSerializer,
    SubmissionSerializer,
    UserProfileSerializer,
    CodeExecutionSerializer
)
from django.conf import settings
import requests
import json

class ProblemViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Problem.objects.all()
    serializer_class = ProblemSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @action(detail=True, methods=['get'])
    def submissions(self, request, pk=None):
        problem = self.get_object()
        submissions = problem.submission_set.all()
        serializer = SubmissionSerializer(submissions, many=True)
        return Response(serializer.data)

class SubmissionViewSet(viewsets.ModelViewSet):
    serializer_class = SubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Submission.objects.filter(user=self.request.user).order_by('-submitted_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class UserProfileViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @action(detail=True, methods=['get'])
    def submissions(self, request, pk=None):
        user_profile = self.get_object()
        submissions = Submission.objects.filter(user=user_profile.user)
        serializer = SubmissionSerializer(submissions, many=True)
        return Response(serializer.data)

def execute_code_api(request):
    if request.method == 'POST':
        serializer = CodeExecutionSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            result = execute_code(
                code=data['code'],
                language=data['language'],
                sample_input=data.get('input', ''),
                expected_output=data.get('expected_output', '')
            )
            return Response(result, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)






# def register_view(request):
#     """User registration"""
#     if request.method == 'POST':
#         username = request.POST.get('username')
#         email = request.POST.get('email')
#         password = request.POST.get('password')
#         confirm_password = request.POST.get('confirm_password')
        
#         if password != confirm_password:
#             messages.error(request, 'Passwords do not match')
#             return render(request, 'coding/register.html')
        
#         if User.objects.filter(username=username).exists():
#             messages.error(request, 'Username already exists')
#             return render(request, 'coding/register.html')
        
#         if User.objects.filter(email=email).exists():
#             messages.error(request, 'Email already exists')
#             return render(request, 'coding/register.html')
        
#         user = User.objects.create_user(username=username, email=email, password=password)
#         UserProfile.objects.create(user=user)
        
#         messages.success(request, 'Registration successful! Please login.')
#         return redirect('login')
    
#     return render(request, 'coding/register.html')

# def login_view(request):
#     """User login"""
#     if request.method == 'POST':
#         username = request.POST.get('username')
#         password = request.POST.get('password')
        
#         user = authenticate(request, username=username, password=password)
#         if user is not None:
#             login(request, user)
#             return redirect('dashboard')
#         else:
#             messages.error(request, 'Invalid username or password')
    
#     return render(request, 'coding/login.html')

# def logout_view(request):
#     """User logout"""
#     logout(request)
#     return redirect('home')