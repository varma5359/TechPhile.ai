from django.urls import path

from . import views


app_name = 'interview_prep'

urlpatterns = [
    path('', views.monthly_plan, name='monthly_plan'),
    path('prepare/', views.create_preparation, name='create_preparation'),
    path('preparations/<int:preparation_id>/', views.preparation_detail, name='preparation_detail'),
    path('preparations/<int:preparation_id>/questions/', views.preparation_questions, name='preparation_questions'),
    path(
        'preparations/<int:preparation_id>/questions/<str:action>/',
        views.preparation_question_action,
        name='preparation_question_action',
    ),
    path('orders/start/', views.start_order, name='start_order'),
    path('orders/<uuid:public_reference>/', views.order_detail, name='order_detail'),
]
