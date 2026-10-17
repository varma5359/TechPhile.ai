from django.urls import path, include
from rest_framework import routers
from . import views
from .views import (
    ProblemViewSet, 
    SubmissionViewSet,
    UserProfileViewSet,
    execute_code_api,
)

# Regular web URLs (unchanged from your original)
urlpatterns = [

    path('coding-problems', views.home, name='home_page_coding'),
    path('problems/', views.problem_list, name='problem_list'),
    path('problems/<slug:slug>/', views.problem_detail, name='problem_detail'),
    path('submit/', views.submit_code, name='submit_code'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('api/problem/<int:problem_id>/solution/', views.problem_solution, name='problem_solution'),
]

# API URLs (new additions)
router = routers.DefaultRouter()
router.register(r'api/problems', ProblemViewSet, basename='api-problem')
router.register(r'api/submissions', SubmissionViewSet, basename='api-submission')
router.register(r'api/users', UserProfileViewSet, basename='api-userprofile')

urlpatterns += [
    path('', include(router.urls)),
    path('api/execute/', execute_code_api, name='api-execute'),
    path('api/auth/', include('rest_framework.urls', namespace='rest_framework')),
]