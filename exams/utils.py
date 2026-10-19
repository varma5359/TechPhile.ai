from django.core.mail import send_mail
from django.conf import settings


def send_interview_cancellation_email(applicant):
    subject = "Interview Cancelled"
    message = f"Dear {applicant.first_name},\n\nYour interview scheduled on {applicant.interview_date} at {applicant.interview_time} has been cancelled.\n\nRegards,\nTechphile Team"
    recipient_list = [applicant.email]
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list)


def send_interview_reschedule_email(applicant):
    subject = "Interview Rescheduled"
    message = f"Dear {applicant.first_name},\n\nYour interview has been rescheduled to {applicant.interview_date} at {applicant.interview_time}.\n\nRegards,\nTechphile Team"
    recipient_list = [applicant.email]
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient_list)

import hashlib
import hmac

from django.conf import settings
from django.contrib.sessions.models import Session
from django.utils import timezone


def _profile_session_token(user, session_key):
    """Create a non-reversible, user-scoped identifier for a session row."""
    value = f'profile-session:{user.pk}:{session_key}'.encode()
    secret = settings.SECRET_KEY.encode()
    return hmac.new(secret, value, hashlib.sha256).hexdigest()


def get_active_sessions(user, current_session_key=None):
    """Return this user's live DB sessions without exposing session keys or metadata."""
    sessions = Session.objects.filter(expire_date__gte=timezone.now()).only(
        'session_key', 'session_data', 'expire_date')
    user_sessions = []
    for session in sessions.iterator():
        data = session.get_decoded()
        if data.get('_auth_user_id') != str(user.pk):
            continue
        user_sessions.append({
            'id': _profile_session_token(user, session.session_key),
            'expires_at': session.expire_date,
            'is_current': session.session_key == current_session_key,
        })
    return user_sessions


def terminate_active_session(user, session_token, current_session_key=None):
    """Delete only a matching non-current session owned by the authenticated user."""
    if not isinstance(session_token, str) or len(session_token) != 64:
        return False

    sessions = Session.objects.filter(expire_date__gte=timezone.now()).only(
        'session_key', 'session_data', 'expire_date')
    for session in sessions.iterator():
        data = session.get_decoded()
        if data.get('_auth_user_id') != str(user.pk):
            continue
        if session.session_key == current_session_key:
            continue
        expected = _profile_session_token(user, session.session_key)
        if hmac.compare_digest(session_token, expected):
            session.delete()
            return True
    return False
