from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from .forms import EmailSignUpForm, EmailLoginForm
from django.urls import reverse


def _google_auth_page(response):
    """Allow Google Identity Services to communicate with its sign-in popup."""
    response['Cross-Origin-Opener-Policy'] = 'same-origin-allow-popups'
    response['Referrer-Policy'] = 'no-referrer-when-downgrade'
    return response


def signup_view(request):
    if request.method == 'POST':
        form = EmailSignUpForm(request.POST, request=request)
        if form.is_valid():
            user = form.save()  # Assuming this sends activation email
            messages.success(request, "Registration successful! Please activate your account through the email link.")
            return redirect('login')  # This will redirect to login page
    else:
        form = EmailSignUpForm(request=request)
    return _google_auth_page(render(request, 'registration/signup.html', {
        'form': form,
        'google_oauth_client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
    }))


from django.views.decorators.cache import never_cache
from django.contrib.auth import authenticate
@never_cache
def login_view(request):
    dashboard_url = reverse('exams:student_dashboard')
    next_url = request.GET.get('next') or request.POST.get('next') or dashboard_url
    if not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = dashboard_url

    if request.user.is_authenticated:
        return redirect(next_url)

    if request.method == 'POST':
        form = EmailLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email'].lower()
            password = form.cleaned_data['password']  # Make sure you're getting password
            
            try:
                user = User.objects.get(email=email)
                if not user.is_active:
                    messages.error(request, "Account not verified. Please check your email for the activation link.")
                    return redirect('login')
                
                # Authenticate properly with email AND password
                user = authenticate(request, username=user.username, password=password)
                if user is not None:
                    auth_login(request, user)
                    if request.POST.get('remember') != 'on':
                        request.session.set_expiry(0)
                    messages.success(request, f"Welcome back, {user.first_name or user.email}!")
                    return redirect(next_url)
                else:
                    messages.error(request, "Invalid email or password.")
            except User.DoesNotExist:
                messages.error(request, "No account found with this email.")
        else:
            # Show specific form errors
            for field, errors in form.errors.items():
                for error in errors:
                    clean_error = error.replace(f"{field}:", "").replace("__all__:", "").strip()
                    messages.error(request, clean_error)
    else:
        form = EmailLoginForm()

    return _google_auth_page(render(request, 'registration/login.html', {
        'form': form,
        'failed_login': request.method == 'POST',
        'next': next_url,
        'google_oauth_client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
    }))


@require_POST
def google_sign_in(request):
    """Verify a Google Identity credential and sign in or create the user."""
    client_id = settings.GOOGLE_OAUTH_CLIENT_ID
    if not client_id:
        return JsonResponse({'error': 'Google sign-in is not configured yet.'}, status=503)

    credential = request.POST.get('credential', '')
    if not credential:
        return JsonResponse({'error': 'Google did not return a sign-in credential.'}, status=400)

    try:
        from google.auth.transport.requests import Request as GoogleRequest
        from google.oauth2 import id_token

        claims = id_token.verify_oauth2_token(credential, GoogleRequest(), audience=client_id)
        email = (claims.get('email') or '').strip().lower()
        if not email or claims.get('email_verified') is not True:
            return JsonResponse({'error': 'Use a Google account with a verified email address.'}, status=400)
    except Exception:
        return JsonResponse({'error': 'Google sign-in could not be verified. Please try again.'}, status=400)

    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        base_username = email.split('@', 1)[0].lower()
        username = base_username
        suffix = 1
        while User.objects.filter(username__iexact=username).exists():
            username = f'{base_username}{suffix}'
            suffix += 1
        user = User.objects.create_user(username=username, email=email)

    # A verified Google identity proves control of this email. It can safely
    # complete an older pending email-activation registration for that address.
    if not user.is_active:
        user.is_active = True
        user.save(update_fields=['is_active'])

    auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    if request.POST.get('remember') != 'on':
        request.session.set_expiry(0)

    next_url = request.POST.get('next') or reverse('exams:student_dashboard')
    if not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = reverse('exams:student_dashboard')
    return JsonResponse({'redirect_url': next_url})
    

from django.views.decorators.cache import never_cache
@never_cache
def logout_view(request):
    auth_logout(request)
    return redirect('home')

def verify_email(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    
    if user and default_token_generator.check_token(user, token):
        if not user.is_active:
            user.is_active = True
            user.save()
            messages.success(request, "Email verified successfully! You can now log in.")
        else:
            messages.info(request, "Your email was already verified.")
        return redirect('login')
    
    messages.error(request, "Invalid verification link.")
    return redirect('signup')


from django.views.generic import TemplateView

class TermsOfServiceView(TemplateView):
    template_name = 'registration/terms_of_service.html'

class PrivacyPolicyView(TemplateView):
    template_name = 'registration/privacy_policy.html'



from django.contrib.auth.views import (
    PasswordResetView, 
    PasswordResetDoneView, 
    PasswordResetConfirmView,
    PasswordResetCompleteView
)
from django.views.generic import TemplateView
from django.urls import reverse_lazy
from django.conf import settings

class CustomPasswordResetView(PasswordResetView):
    from_email = settings.DEFAULT_FROM_EMAIL
    email_template_name = 'registration/password_reset_email.html'
    template_name = 'registration/password_reset_form.html'
    subject_template_name = 'registration/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')
    html_email_template_name = 'registration/password_reset_email.html'  # For HTML emails
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['company_name'] = settings.COMPANY_NAME
        context['contact_email'] = settings.CONTACT_EMAIL
        return context
