from django.shortcuts import render

# Create your views here.
import shutil
import time
import cv2
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Q
import json
import subprocess
import tempfile
import os
from .models import Topic, Problem, Dataset, Submissions, UserProgress, Leaderboard


def home(request):
    """Homepage with overview of platform."""
    topics = Topic.objects.all()
    recent_problems = Problem.objects.filter(is_active=True)[:6]
    
    context = {
        'topics': topics,
        'recent_problems': recent_problems,
    }
    
    if request.user.is_authenticated:
        user_progress = UserProgress.objects.filter(user=request.user)
        context['user_progress'] = user_progress
        
        try:
            leaderboard_entry = Leaderboard.objects.get(user=request.user)
            context['user_rank'] = leaderboard_entry.rank
            context['user_score'] = leaderboard_entry.total_score
        except Leaderboard.DoesNotExist:
            context['user_rank'] = None
            context['user_score'] = 0
    
    return render(request, 'coding_temp/core/home.html', context)


def creativity_intelligence(request):
    """Creativity and Intelligence section - main AI/ML coding area."""
    topics = Topic.objects.all()
    
    # Get problems by topic
    problems_by_topic = {}
    for topic in topics:
        problems_by_topic[topic] = Problem.objects.filter(
            topic=topic, 
            is_active=True
        )[:10]  # Limit to 10 per topic for homepage
    
    context = {
        'topics': topics,
        'problems_by_topic': problems_by_topic,
    }
    
    return render(request, 'coding_temp/core/creativity_intelligence.html', context)


def topic_detail(request, topic_id):
    """Show all problems for a specific topic."""
    topic = get_object_or_404(Topic, id=topic_id)
    problems = Problem.objects.filter(topic=topic, is_active=True)
    
    # Get user progress if authenticated
    user_progress = {}
    if request.user.is_authenticated:
        progress_data = UserProgress.objects.filter(
            user=request.user, 
            problem__in=problems
        )
        user_progress = {p.problem_id: p for p in progress_data}
    
    context = {
        'topic': topic,
        'problems': problems,
        'user_progress': user_progress,
    }
    
    return render(request, 'coding_temp/core/topic_detail.html', context)


@login_required
def problem_detail(request, problem_id):
    """Problem solving interface with code editor."""
    problem = get_object_or_404(Problem, id=problem_id, is_active=True)
    
    # Get or create user progress
    progress, created = UserProgress.objects.get_or_create(
        user=request.user,
        problem=problem,
        defaults={'status': 'not_started'}
    )
    
    # Get user's previous submissions
    submissions = Submissions.objects.filter(
        user=request.user,
        problem=problem
    )[:5]  # Last 5 submissions
    
    context = {
        'problem': problem,
        'progress': progress,
        'submissions': submissions,
    }
    
    return render(request, 'coding_temp/core/problem_detail.html', context)


@csrf_exempt
@login_required
def submit_code(request):
    """Handle code submission and execution."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST method required'}, status=405)
    
    try:
        data = json.loads(request.body)
        problem_id = data.get('problem_id')
        code = data.get('code', '')
        
        problem = get_object_or_404(Problem, id=problem_id, is_active=True)
        
        # Create submission record
        submission = Submissions.objects.create(
            user=request.user,
            problem=problem,
            code=code,
            status='submitted'
        )
        
        # Execute the code
        try:
            result = execute_python_code(code, problem)
            submission.output = result['output']
            submission.execution_time = result['execution_time']
            
            # Check if solution is correct
            if result['success']:
                submission.status = 'correct'
                submission.score = problem.points
                
                # Update user progress
                progress, created = UserProgress.objects.get_or_create(
                    user=request.user,
                    problem=problem,
                    defaults={'status': 'attempted', 'attempts': 0}
                )
                
                progress.attempts += 1
                progress.status = 'completed'
                progress.best_score = max(progress.best_score, submission.score)
                progress.completed_at = timezone.now()
                progress.last_attempt_at = timezone.now()
                progress.save()
                
                # Update leaderboard
                update_leaderboard(request.user)
                
            else:
                submission.status = 'incorrect'
                
                # Update attempts
                progress, created = UserProgress.objects.get_or_create(
                    user=request.user,
                    problem=problem,
                    defaults={'status': 'attempted', 'attempts': 0}
                )
                progress.attempts += 1
                progress.status = 'attempted'
                progress.last_attempt_at = timezone.now()
                progress.save()
                
        except Exception as e:
            submission.status = 'error'
            submission.output = f"Execution error: {str(e)}"
            result = {
                'success': False,
                'output': submission.output,
                'execution_time': 0
            }
        
        submission.save()
        
        return JsonResponse({
            'success': result['success'],
            'output': result['output'],
            'execution_time': result['execution_time'],
            'status': submission.status,
            'score': submission.score
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def execute_python_code(code, problem):
    """Execute Python code safely."""
    try:
        # Create a temporary file for the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        # Execute the code with timeout
        import time
        start_time = time.time()
        
        result = subprocess.run(
            ['python', temp_file],
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )
        
        end_time = time.time()
        execution_time = int((end_time - start_time) * 1000)  # Convert to milliseconds
        
        # Clean up
        os.unlink(temp_file)
        
        if result.returncode == 0:
            output = result.stdout.strip()
            success = True
            # Normalize output for comparison
            def normalize(text):
                return ' '.join(text.lower().split())
            
           # Improved output checking
            if problem.expected_output:
                normalized_expected = normalize(problem.expected_output)
                normalized_actual = normalize(output)
                success = normalized_actual == normalized_expected
            
            return {
               'success': success,
               'output': output,
               'execution_time': execution_time
        }
       

        else:
            return {
                'success': False,
                'output': result.stderr.strip(),
                'execution_time': execution_time
            }
            
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'output': 'Code execution timed out (30 seconds)',
            'execution_time': 30000
        }
    except Exception as e:
        return {
            'success': False,
            'output': f'Execution error: {str(e)}',
            'execution_time': 0
        }
    
@property
def is_dataset_problem(self):
    return self.dataset is not None


def update_leaderboard(user):
    """Update user's leaderboard entry."""
    progress_entries = UserProgress.objects.filter(
        user=user, 
        status='completed'
    )
    
    total_score = sum(p.best_score for p in progress_entries)
    problems_solved = progress_entries.count()
    
    leaderboard, created = Leaderboard.objects.get_or_create(
        user=user,
        defaults={
            'total_score': total_score,
            'problems_solved': problems_solved
        }
    )
    
    if not created:
        leaderboard.total_score = total_score
        leaderboard.problems_solved = problems_solved
        leaderboard.save()
    
    # Update ranks
    leaderboards = Leaderboard.objects.order_by('-total_score')
    for rank, lb in enumerate(leaderboards, 1):
        lb.rank = rank
        lb.save()


def leaderboard(request):
    """Show leaderboard."""
    top_users = Leaderboard.objects.all()[:50]  # Top 50 users
    
    context = {
        'top_users': top_users,
    }
    
    return render(request, 'coding_temp/core/leaderboard.html', context)


def datasets(request):
    """Show available datasets."""
    public_datasets = Dataset.objects.filter(is_public=True)
    
    context = {
        'datasets': public_datasets,
    }
    
    return render(request, 'coding_temp/core/datasets.html', context)


# Authentication views

# Authentication views
# class CustomLoginView(auth_views.LoginView):
#     template_name = 'core/login.html'
    
#     def get_success_url(self):
#         return self.get_redirect_url() or '/'


# class CustomLogoutView(auth_views.LogoutView):
#     next_page = '/'

    
# NOTE for frontend developers:
# If you see "Failed to execute 'insertBefore' on 'Node': The node before which the new node is to be inserted is not a child of this node.",
# check your JS code that manipulates the DOM for output/results. Always verify the reference node is a child of the parent before using insertBefore.