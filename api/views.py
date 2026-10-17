# api/views.py
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import login, logout
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
from .serializers import UserRegistrationSerializer, UserLoginSerializer
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny

class UserRegistrationAPIView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response({
            "message": "Registration successful! Please check your email for verification.",
            "email": user.email
        }, status=status.HTTP_201_CREATED)

class UserLoginAPIView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        login(request, user)
        
        # Create or get token for the user
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            "message": "Login successful",
            "token": token.key,
            "user": {
                "email": user.email,
                "username": user.username
            }
        }, status=status.HTTP_200_OK)

class UserLogoutAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        # Delete the token if using token authentication
        if hasattr(request.user, 'auth_token'):
            request.user.auth_token.delete()
        
        logout(request)
        return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)

class VerifyEmailAPIView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, uidb64, token):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        
        if user and default_token_generator.check_token(user, token):
            if not user.is_active:
                user.is_active = True
                user.save()
                return Response({"message": "Email verified successfully! You can now log in."},
                              status=status.HTTP_200_OK)
            return Response({"message": "Your email was already verified."},
                          status=status.HTTP_200_OK)
        
        return Response({"error": "Invalid verification link."},
                      status=status.HTTP_400_BAD_REQUEST)
    


# views.py (add these to your existing file)
from django.contrib.auth.views import PasswordResetConfirmView
from rest_framework.generics import GenericAPIView
from .serializers import PasswordResetSerializer, PasswordResetConfirmSerializer
from django.contrib.auth import get_user_model
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.utils.translation import gettext as _

User = get_user_model()

class PasswordResetView(GenericAPIView):
    serializer_class = PasswordResetSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": _("Password reset e-mail has been sent.")},
            status=status.HTTP_200_OK,
        )

class PasswordResetConfirmView(GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer

    def get_user(self, uidb64):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        return user

    def dispatch(self, *args, **kwargs):
        self.user = self.get_user(kwargs['uidb64'])
        if not default_token_generator.check_token(self.user, kwargs['token']):
            return Response(
                {"detail": _("Password reset link is invalid.")},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.context['user'] = self.user
        serializer.save()
        return Response(
            {"detail": _("Password has been reset with the new password.")},
            status=status.HTTP_200_OK,
        )