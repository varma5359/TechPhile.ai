# serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import re

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    password2 = serializers.CharField(write_only=True, style={'input_type': 'password'})
    
    class Meta:
        model = User
        fields = ('email', 'username', 'password', 'password2')
        extra_kwargs = {
            'email': {'required': True},
            'username': {'required': True}
        }
    
    def validate_email(self, value):
        value = value.lower()
        if not value.endswith('@gmail.com'):
            raise ValidationError("Only Gmail addresses are allowed.")
        
        if User.objects.filter(email=value).exists():
            raise ValidationError("This email is already registered.")
        return value
    
    def validate_password(self, value):
        # Password must start with capital letter
        if not value[0].isupper():
            raise ValidationError("Password must start with a capital letter.")
        
        # Must contain at least one digit
        if not any(char.isdigit() for char in value):
            raise ValidationError("Password must contain at least one digit.")
        
        # Must contain at least one special character
        special_chars = r"[~\!@#\$%\^&\*\(\)_\+{}\":;'\[\]]"
        if not re.search(special_chars, value):
            raise ValidationError("Password must contain at least one special character.")
        
        # Minimum length 8 characters
        if len(value) < 8:
            raise ValidationError("Password must be at least 8 characters long.")
        
        return value
    
    def validate(self, data):
        if data['password'] != data['password2']:
            raise ValidationError({"password2": "Passwords don't match."})
        return data
    
    def create(self, validated_data):
        # Use email as username
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            is_active=False  # User needs to verify email first
        )
        
        self.send_verification_email(user)
        return user
    
    def send_verification_email(self, user):
        current_site = settings.BASE_URL
        mail_subject = 'Activate your account'
        
        # Generate verification token
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        
        verification_link = f"{current_site}/api/auth/verify-email/{uid}/{token}/"
        
        context = {
            'user': user,
            'verification_link': verification_link,
            'site_url': current_site,
        }
        
        # Render email content
        html_message = render_to_string('registration/verification_email.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=mail_subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(style={'input_type': 'password'})
    
    def validate(self, data):
        email = data.get('email').lower()
        password = data.get('password')
        
        if not email.endswith('@gmail.com'):
            raise ValidationError("Only Gmail addresses are allowed.")
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValidationError("Invalid email or password.")
        
        if not user.check_password(password):
            raise ValidationError("Invalid email or password.")
        
        if not user.is_active:
            raise ValidationError("Account not verified. Please check your email.")
        
        data['user'] = user
        return data
    



    # serializers.py (add these to your existing file)
from rest_framework import serializers
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.conf import settings
from django.utils.translation import gettext as _

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password_reset_form_class = PasswordResetForm

    def validate_email(self, value):
        value = value.lower()
        if not value.endswith('@gmail.com'):
            raise serializers.ValidationError("Only Gmail addresses are allowed.")
        return value

    def save(self):
        request = self.context.get('request')
        opts = {
            'use_https': request.is_secure(),
            'from_email': getattr(settings, 'DEFAULT_FROM_EMAIL'),
            'email_template_name': 'registration/password_reset_email.html',
            'subject_template_name': 'registration/password_reset_subject.txt',
            'request': request,
        }
        self.reset_form = self.password_reset_form_class(data=self.initial_data)
        if self.reset_form.is_valid():
            self.reset_form.save(**opts)

class PasswordResetConfirmSerializer(serializers.Serializer):
    new_password1 = serializers.CharField(max_length=128)
    new_password2 = serializers.CharField(max_length=128)
    uid = serializers.CharField()
    token = serializers.CharField()
    set_password_form_class = SetPasswordForm

    def validate(self, attrs):
        try:
            # Validate the password
            if attrs['new_password1'] != attrs['new_password2']:
                raise serializers.ValidationError(_("The two password fields didn't match."))
            
            # Custom password validation
            password = attrs['new_password1']
            if not password[0].isupper():
                raise serializers.ValidationError("Password must start with a capital letter.")
            if not any(char.isdigit() for char in password):
                raise serializers.ValidationError("Password must contain at least one digit.")
            special_chars = r"[~\!@#\$%\^&\*\(\)_\+{}\":;'\[\]]"
            if not re.search(special_chars, password):
                raise serializers.ValidationError("Password must contain at least one special character.")
            if len(password) < 8:
                raise serializers.ValidationError("Password must be at least 8 characters long.")

            self.set_password_form = self.set_password_form_class(
                user=self.context['user'],
                data=attrs
            )
            if not self.set_password_form.is_valid():
                raise serializers.ValidationError(self.set_password_form.errors)
        except KeyError:
            pass
        
        return attrs

    def save(self):
        return self.set_password_form.save()
    
