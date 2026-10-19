from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from careers.choices import LEVEL_BEGINNER
from careers.models import CareerRole, DayAttempt, LearningDay
from .utils import get_active_sessions, terminate_active_session


User = get_user_model()


def make_image(image_format='PNG', name=None):
    content = BytesIO()
    Image.new('RGB', (8, 8), color='navy').save(content, format=image_format)
    extension = 'jpg' if image_format == 'JPEG' else image_format.lower()
    return SimpleUploadedFile(name or f'profile.{extension}', content.getvalue(),
                              content_type=f'image/{extension}')


class ProfileSettingsEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='settings-user', email='saved@example.com', password='SafePass123!')
        self.other = User.objects.create_user(
            username='other-user', email='other@example.com', password='SafePass123!')
        self.client.force_login(self.user)

    def test_settings_page_prefills_persisted_values_and_tabs(self):
        profile = self.user.profile
        profile.phone = '+91 9876543210'
        profile.exam_notifications = False
        profile.language = 'hi'
        profile.save()

        response = self.client.get(reverse('exams:profile_settings') + '?tab=notifications')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['active_tab'], 'notifications')
        self.assertContains(response, 'value="+91 9876543210"')
        self.assertContains(response, 'id="id_exam_notifications"')
        self.assertContains(response, 'name="language"')
        self.assertContains(response, 'Automated email and push delivery is not connected')

    def test_basic_profile_update_persists_names_and_phone_but_ignores_email(self):
        response = self.client.post(reverse('exams:update_profile'), {
            'first_name': 'Taylor', 'last_name': 'Learner', 'phone': '+1 (415) 555-0123',
            'email': 'attacker@example.com',
        })

        self.assertRedirects(response, reverse('exams:profile_settings') + '?tab=basic')
        self.user.refresh_from_db()
        self.user.profile.refresh_from_db()
        self.assertEqual((self.user.first_name, self.user.last_name), ('Taylor', 'Learner'))
        self.assertEqual(self.user.email, 'saved@example.com')
        self.assertEqual(self.user.profile.phone, '+1 (415) 555-0123')

    def test_invalid_phone_is_rejected_and_get_is_not_allowed_for_mutation(self):
        self.client.post(reverse('exams:update_profile'), {
            'first_name': 'Changed', 'last_name': 'Name', 'phone': 'call-me',
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, '')
        self.assertEqual(self.client.get(reverse('exams:update_profile')).status_code, 405)

    def test_photo_upload_accepts_jpeg_png_and_removes_via_storage_api(self):
        with TemporaryDirectory() as media_dir:
            with override_settings(MEDIA_ROOT=media_dir):
                response = self.client.post(reverse('exams:update_profile'), {
                    'first_name': '', 'last_name': '', 'phone': '', 'photo': make_image(),
                })
                self.assertEqual(response.status_code, 302)
                self.user.profile.refresh_from_db()
                saved_name = self.user.profile.photo.name
                self.assertTrue(self.user.profile.photo.storage.exists(saved_name))

                response = self.client.post(reverse('exams:delete_profile_photo'))
                self.assertRedirects(response, reverse('exams:profile_settings') + '?tab=basic')
                self.user.profile.refresh_from_db()
                self.assertFalse(self.user.profile.photo)
                self.assertFalse(self.user.profile.photo.storage.exists(saved_name))

    def test_photo_form_rejects_wrong_type_malformed_and_oversized_files(self):
        from .forms import ProfileUpdateForm

        for uploaded in (
            make_image('GIF'),
            SimpleUploadedFile('broken.png', b'not an image', content_type='image/png'),
            SimpleUploadedFile('large.png', b'x' * (2 * 1024 * 1024 + 1), content_type='image/png'),
        ):
            form = ProfileUpdateForm(
                data={'first_name': '', 'last_name': '', 'phone': ''}, files={'photo': uploaded},
                instance=self.user.profile)
            self.assertFalse(form.is_valid(), form.errors)
            self.assertIn('photo', form.errors)

    def test_password_change_checks_current_password_updates_hash_and_keeps_session(self):
        response = self.client.post(reverse('exams:change_password'), {
            'old_password': 'SafePass123!', 'new_password1': 'BetterPass456!',
            'new_password2': 'BetterPass456!',
        })
        self.assertRedirects(response, reverse('exams:profile_settings') + '?tab=security')
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('BetterPass456!'))
        self.assertEqual(self.client.get(reverse('exams:profile_settings')).status_code, 200)

        self.client.post(reverse('exams:change_password'), {
            'old_password': 'wrong', 'new_password1': 'FreshPass789!',
            'new_password2': 'FreshPass789!',
        })
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('BetterPass456!'))
        self.assertEqual(self.client.get(reverse('exams:change_password')).status_code, 405)

    def test_notification_flags_persist_and_return_to_their_tab(self):
        response = self.client.post(reverse('exams:update_notifications'), {
            'exam_notifications': 'on', 'important_alerts': 'on',
        })
        self.assertRedirects(response, reverse('exams:profile_settings') + '?tab=notifications')
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.exam_notifications)
        self.assertFalse(self.user.profile.interview_notifications)
        self.assertFalse(self.user.profile.promotional_emails)
        self.assertFalse(self.user.profile.push_reminders)
        self.assertTrue(self.user.profile.important_alerts)

    def test_preferences_persist_and_invalid_choices_are_rejected(self):
        response = self.client.post(reverse('exams:update_preferences'), {
            'theme': 'dark', 'language': 'hi', 'dashboard_view': 'compact', 'timezone': 'Asia/Kolkata',
        })
        self.assertRedirects(response, reverse('exams:profile_settings') + '?tab=preferences')
        self.user.profile.refresh_from_db()
        self.assertEqual((self.user.profile.theme, self.user.profile.language,
                          self.user.profile.dashboard_view, self.user.profile.timezone),
                         ('dark', 'hi', 'compact', 'Asia/Kolkata'))
        self.client.post(reverse('exams:update_preferences'), {
            'theme': 'neon', 'language': 'xx', 'dashboard_view': 'huge', 'timezone': 'Mars/Olympus',
        })
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.theme, 'dark')

    def test_career_preferences_persist_without_detaching_existing_progress(self):
        role_a = CareerRole.objects.create(title='Settings Role A', summary='First.', is_published=True)
        role_b = CareerRole.objects.create(title='Settings Role B', summary='Second.', is_published=True)
        day = LearningDay.objects.create(role=role_a, day_number=1, title='Existing progress', is_published=True)
        attempt = DayAttempt.objects.create(user=self.user, day=day, correct_marks=1,
                                           total_marks=1, score_percent=100)
        self.client.post(reverse('exams:update_career_preferences'), {
            'career_role': role_b.pk, 'experience_band': '1_2', 'learning_path': LEVEL_BEGINNER,
        })
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.career_role_id, role_b.pk)
        self.assertTrue(DayAttempt.objects.filter(pk=attempt.pk, user=self.user, day=day).exists())
        unpublished = CareerRole.objects.create(
            title='Hidden Settings Role', summary='Unavailable.', is_published=False)
        self.client.post(reverse('exams:update_career_preferences'), {
            'career_role': unpublished.pk, 'experience_band': '1_2', 'learning_path': LEVEL_BEGINNER,
        })
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.career_role_id, role_b.pk)

    def test_session_list_and_revocation_are_user_scoped_and_preserve_current_session(self):
        current_key = self.client.session.session_key
        other_session = SessionStore()
        other_session['_auth_user_id'] = str(self.user.pk)
        other_session['_auth_user_backend'] = 'django.contrib.auth.backends.ModelBackend'
        other_session.save()
        foreign_session = SessionStore()
        foreign_session['_auth_user_id'] = str(self.other.pk)
        foreign_session['_auth_user_backend'] = 'django.contrib.auth.backends.ModelBackend'
        foreign_session.save()

        listed = get_active_sessions(self.user, current_key)
        self.assertEqual(len(listed), 2)
        foreign_token = get_active_sessions(self.other)[0]['id']
        current_token = next(row['id'] for row in listed if row['is_current'])
        self.assertFalse(terminate_active_session(self.user, foreign_token, current_key))
        self.assertFalse(terminate_active_session(self.user, current_token, current_key))
        token = next(row['id'] for row in listed if not row['is_current'])
        response = self.client.post(reverse('exams:terminate_session', args=[token]))
        self.assertRedirects(response, reverse('exams:profile_settings') + '?tab=security')
        remaining = get_active_sessions(self.user, current_key)
        self.assertEqual(len(remaining), 1)
        self.assertTrue(remaining[0]['is_current'])
        self.assertTrue(Session.objects.filter(session_key=foreign_session.session_key).exists())

    def test_settings_require_login_and_csrf_for_mutations(self):
        anonymous = Client()
        response = anonymous.get(reverse('exams:profile_settings'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('exams:profile_settings'), response.url)

        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        response = csrf_client.post(reverse('exams:update_notifications'), {'exam_notifications': 'on'})
        self.assertEqual(response.status_code, 403)

