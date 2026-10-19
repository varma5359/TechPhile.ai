from django.conf import settings


def features(request):
    """Expose the FEATURE_FLAGS setting to templates as ``features``."""
    return {'features': getattr(settings, 'FEATURE_FLAGS', {})}
