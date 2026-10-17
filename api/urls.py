# urls.py (update your existing file)
from django.urls import path
from .views import (
    UserRegistrationAPIView,
    UserLoginAPIView,
    UserLogoutAPIView,
    VerifyEmailAPIView,
    PasswordResetView,
    PasswordResetConfirmView
)

urlpatterns = [
    path('register/', UserRegistrationAPIView.as_view(), name='api_register'),
    path('login/', UserLoginAPIView.as_view(), name='api_login'),
    path('logout/', UserLogoutAPIView.as_view(), name='api_logout'),
    path('verify-email/<uidb64>/<token>/', VerifyEmailAPIView.as_view(), name='api_verify_email'),
    
    # Password reset URLs
    path('password-reset/', PasswordResetView.as_view(), name='api_password_reset'),
    path('password-reset-confirm/<uidb64>/<token>/', 
         PasswordResetConfirmView.as_view(), 
         name='api_password_reset_confirm'),


         
]