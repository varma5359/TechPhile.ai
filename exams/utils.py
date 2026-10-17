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

from django.contrib.sessions.models import Session
from django.utils import timezone

def get_active_sessions(user):
    sessions = Session.objects.filter(expire_date__gte=timezone.now())
    user_sessions = []
    for session in sessions:
        data = session.get_decoded()
        if data.get('_auth_user_id') == str(user.id):
            user_sessions.append(session)
    return user_sessions