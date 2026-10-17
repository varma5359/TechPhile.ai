from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)

class EmailSignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, label='Email')
    
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['password1'].help_text = "Minimum 8 characters"
        self.fields['email'].widget.attrs.update({'autocomplete': 'email'})
        logger.debug("EmailSignUpForm initialized with request: %s", self.request is not None)

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        existing_user = User.objects.filter(email=email).first()
    
        if existing_user:
            if existing_user.is_active:
                logger.warning("Registration attempt with existing active email: %s", email)
                raise ValidationError("This email is already registered.")
            else:
                logger.info("Inactive user exists with this email: %s. Allowing re-registration.", email)
                # Optional: Delete or update the old inactive user here
                existing_user.delete()  # ← Be cautious with this line!
        
        return email
    def clean_username(self):
        username = self.cleaned_data['username'].lower()
        existing_user = User.objects.filter(username=username).first()
    
        if existing_user:
            if existing_user.is_active:
                raise ValidationError("This username is already taken.")
            else:
                logger.info("Inactive user exists with this username: %s. Allowing reuse.", username)
                existing_user.delete()  # Or handle differently
        
        return username
    

    def save(self, commit=True):
        logger.debug("Entering save method with commit=%s", commit)
        
        user = super().save(commit=False)
        user.username = self.cleaned_data['username'].lower()
        user.first_name = self.cleaned_data['username']  # Add this line        user.email = self.cleaned_data['email']
        user.is_active = False
        
        logger.debug(
            "User created (not saved yet): username=%s, email=%s, is_active=%s",
            user.username,
            user.email,
            user.is_active
        )

        if commit:
            try:
                user.save()
                logger.info("User saved successfully, ID: %s", user.id)
                
                # Ensure request is available before sending email
                if not hasattr(self, 'request'):
                    logger.error("No request object available for email sending")
                    raise ValueError("Request object is missing")
                
                self.send_verification_email(user)
                logger.info("Verification email sent to %s", user.email)
            except Exception as e:
                logger.error("Error during user save/email send: %s", str(e))
                raise

        return user

    def send_verification_email(self, user):
        logger.debug("Preparing verification email for %s", user.email)
        
        try:
            current_site = get_current_site(self.request)
            mail_subject = 'Activate your TechPhile.ai account'
            
            # Generate verification token
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            
            verification_link = f"{settings.BASE_URL}{reverse('verify_email', kwargs={'uidb64': uid, 'token': token})}"
            
            logger.debug("Verification link generated: %s", verification_link)
            
            context = {
                'user': user,
                'verification_link': verification_link,
                'site_url': settings.BASE_URL,
            }
            
            # Render email content
            html_message = render_to_string('registration/verification_email.html', context)
            plain_message = strip_tags(html_message)
            
            logger.debug("Sending email to %s", user.email)
            
            send_mail(
                subject=mail_subject,
                message=plain_message,
                from_email='Activate@techphile.in',
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info("Verification email successfully sent to %s", user.email)
        except Exception as e:
            logger.error("Failed to send verification email: %s", str(e))
            raise

class EmailLoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'autocomplete': 'email'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')
        
        if email and password:
            email = email.lower()
            try:
                user = User.objects.get(email=email)
                if not user.is_active:
                    logger.warning("Login attempt for unverified account: %s", email)
                    raise ValidationError(
                        "Account not verified. Please check your email for verification link."
                    )
                if not user.check_password(password):
                    logger.warning("Failed login attempt for email: %s", email)
                    raise ValidationError("Invalid email or password.")
            except User.DoesNotExist:
                logger.warning("Login attempt with non-existent email: %s", email)
                raise ValidationError("Invalid email or password.")
        return cleaned_data