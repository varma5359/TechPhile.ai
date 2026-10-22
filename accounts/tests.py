from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class LoginFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='login-flow-user',
            email='login-flow@example.com',
            password='Safe-test-password-123!',
        )

    def test_signup_and_login_routes_use_the_same_google_auth_flow(self):
        signup_response = self.client.get(reverse('signup'))
        login_response = self.client.get(reverse('login'))

        self.assertEqual(signup_response.status_code, 200)
        self.assertContains(signup_response, 'Sign in or create your account securely with Google')
        self.assertEqual(login_response.status_code, 200)
        self.assertContains(login_response, 'Sign in or create your account securely with Google')

    def test_successful_login_redirects_to_safe_next_url(self):
        response = self.client.post(
            reverse('login'),
            {
                'email': self.user.email,
                'password': 'Safe-test-password-123!',
                'next': '/coding/problems/',
            },
        )

        self.assertRedirects(
            response,
            '/coding/problems/',
            fetch_redirect_response=False,
        )

    def test_remember_me_controls_session_expiry(self):
        for remember_me, browser_close in (('', True), ('on', False)):
            with self.subTest(remember_me=remember_me):
                client = self.client_class()
                response = client.post(
                    reverse('login'),
                    {
                        'email': self.user.email,
                        'password': 'Safe-test-password-123!',
                        'remember': remember_me,
                    },
                )

                self.assertEqual(response.status_code, 302)
                self.assertEqual(
                    client.session.get_expire_at_browser_close(),
                    browser_close,
                )

    def test_external_next_url_falls_back_to_dashboard(self):
        response = self.client.post(
            reverse('login'),
            {
                'email': self.user.email,
                'password': 'Safe-test-password-123!',
                'next': 'https://example.com/',
            },
        )

        self.assertRedirects(
            response,
            reverse('exams:student_dashboard'),
            fetch_redirect_response=False,
        )

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_signup_creates_inactive_user_and_sends_verification_email(self):
        response = self.client.post(
            reverse('signup'),
            {
                'username': 'registration-flow-user',
                'email': 'registration-flow@example.com',
                'password1': 'Registration-flow-password-123!',
                'password2': 'Registration-flow-password-123!',
            },
        )

        self.assertRedirects(
            response,
            reverse('login'),
            fetch_redirect_response=False,
        )
        user = User.objects.get(username='registration-flow-user')
        self.assertFalse(user.is_active)
        self.assertEqual(len(mail.outbox), 1)

    def test_authenticated_user_visiting_login_is_redirected_to_dashboard(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('login'))

        self.assertRedirects(
            response,
            reverse('exams:student_dashboard'),
            fetch_redirect_response=False,
        )
