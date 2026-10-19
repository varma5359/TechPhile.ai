from django.urls import path

from . import views

app_name = 'careers'

urlpatterns = [
    path('', views.role_list, name='role_list'),
    path('<slug:slug>/', views.role_detail, name='role_detail'),
    path('<slug:slug>/day/<int:day_number>/', views.day_detail, name='day_detail'),
    path('<slug:slug>/day/<int:day_number>/result/<int:attempt_id>/', views.day_result, name='day_result'),
    path('<slug:slug>/milestone/<int:number>/', views.milestone_detail, name='milestone_detail'),
    path('<slug:slug>/milestone/<int:number>/result/<int:attempt_id>/',
         views.milestone_result, name='milestone_result'),
]
