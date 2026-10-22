from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


@deconstructible
class PrivateReceiptStorage(FileSystemStorage):
    """Store payment receipts outside the public media directory."""

    def __init__(self, **kwargs):
        kwargs.setdefault('location', settings.PRIVATE_UPLOAD_ROOT)
        kwargs.setdefault('base_url', None)
        super().__init__(**kwargs)

    def url(self, name):
        """Prevent receipt files from being served through a public URL."""
        raise ValueError('Payment receipts are private and have no public URL.')
