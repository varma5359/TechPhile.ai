from django.urls import path

from . import views

app_name = 'careers'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('', views.role_list, name='role_list'),
    path('<slug:slug>/', views.role_detail, name='role_detail'),
    path('<slug:slug>/day/<int:day_number>/', views.day_detail, name='day_detail'),
    path('<slug:slug>/day/<int:day_number>/complete-notes/', views.complete_notes, name='complete_notes'),
    path('<slug:slug>/day/<int:day_number>/result/<int:attempt_id>/', views.day_result, name='day_result'),
    path('<slug:slug>/milestone/<int:number>/', views.milestone_detail, name='milestone_detail'),
    path('<slug:slug>/milestone/<int:number>/result/<int:attempt_id>/',
         views.milestone_result, name='milestone_result'),
    path('<slug:slug>/path/<slug:level>/', views.role_detail, name='level_role_detail'),
    path('<slug:slug>/path/<slug:level>/day/<int:day_number>/',
         views.day_detail, name='level_day_detail'),
    path('<slug:slug>/path/<slug:level>/day/<int:day_number>/complete-notes/',
         views.complete_notes, name='level_complete_notes'),
    path('<slug:slug>/path/<slug:level>/day/<int:day_number>/result/<int:attempt_id>/',
         views.day_result, name='level_day_result'),
    path('<slug:slug>/path/<slug:level>/milestone/<int:number>/',
         views.milestone_detail, name='level_milestone_detail'),
    path('<slug:slug>/path/<slug:level>/milestone/<int:number>/result/<int:attempt_id>/',
         views.milestone_result, name='level_milestone_result'),
]
