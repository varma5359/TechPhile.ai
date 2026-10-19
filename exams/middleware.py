from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone


class ProfilePreferencesMiddleware:
    """Apply the signed-in learner's saved time zone and expose preferences."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        profile = None
        if getattr(request, 'user', None) and request.user.is_authenticated:
            try:
                profile = request.user.profile
            except ObjectDoesNotExist:
                # Keep requests available if a legacy account has no profile.
                profile = None

        request.profile_preferences = profile
        if profile:
            try:
                timezone.activate(ZoneInfo(profile.timezone))
            except (ZoneInfoNotFoundError, TypeError, ValueError):
                timezone.deactivate()
        else:
            timezone.deactivate()

        return self.get_response(request)


class URLDebugMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print(f"\nIncoming request: {request.path}")
        response = self.get_response(request)
        return response
