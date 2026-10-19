from django.urls import path

from exams import views
from . import views
from django.contrib.auth import views as auth_views

from .views import CustomPasswordResetView, TermsOfServiceView, PrivacyPolicyView


urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('verify-email/<uidb64>/<token>/', views.verify_email, name='verify_email'),


  
  path('password-reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='registration/password_reset_done.html'
    ), name='password_reset_done'),

path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='password_reset_confirm.html'
    ), name='password_reset_confirm'),
    
path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='password_reset_complete.html'
    ), name='password_reset_complete'),

     path('terms-of-service/', TermsOfServiceView.as_view(), name='terms_of_service'),
    path('privacy-policy/', PrivacyPolicyView.as_view(), name='privacy_policy'),
]
