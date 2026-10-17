from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('explore_courses', views.home, name='explore-courses'),
    path('creativity-intelligence/', views.creativity_intelligence, name='creativity_intelligence'),
    path('topic/<int:topic_id>/', views.topic_detail, name='topic_detail'),
    path('problem/<int:problem_id>/', views.problem_detail, name='problem_detail'),
    path('submit-code/', views.submit_code, name='submit_code'),
    path('leaderboard/', views.leaderboard, name='leaderboard'),
    path('datasets/', views.datasets, name='datasets'),


]