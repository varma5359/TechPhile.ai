from pathlib import PurePath

from django import forms
from .role_profiles import SENIORITY_LEVELS, profile_choices
from PIL import Image, UnidentifiedImageError


class PaymentSubmissionForm(forms.Form):
    """Collect a payment reference and an optional private receipt file."""

    transaction_reference = forms.CharField(
        label='UPI transaction or UTR reference',
        max_length=128,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'autocomplete': 'off',
            'placeholder': 'Enter the reference shown in your UPI app',
        }),
    )
    receipt_file = forms.FileField(
        label='Receipt screenshot or PDF',
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.png,.jpg,.jpeg,.pdf',
        }),
    )

    def clean_transaction_reference(self):
        """Normalize the submitted reference before checking uniqueness."""
        return self.cleaned_data['transaction_reference'].strip().upper()

    def clean_receipt_file(self):
        """Accept only small PNG, JPEG, or PDF receipts with matching contents."""
        receipt = self.cleaned_data.get('receipt_file')
        if not receipt:
            return receipt

        if receipt.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Receipt files must be 5 MB or smaller.')

        extension = PurePath(receipt.name).suffix.lower()
        if extension in {'.jpg', '.jpeg', '.png'}:
            try:
                image = Image.open(receipt)
                if image.format not in {'JPEG', 'PNG'}:
                    raise forms.ValidationError('Upload a PNG or JPEG image, or a PDF.')
                if image.width * image.height > 20_000_000:
                    raise forms.ValidationError('The uploaded image dimensions are too large.')
                image.verify()
            except (Image.DecompressionBombError, UnidentifiedImageError, OSError, ValueError):
                raise forms.ValidationError('The uploaded image could not be verified.')
            finally:
                receipt.seek(0)
        elif extension == '.pdf':
            header = receipt.read(5)
            receipt.seek(0)
            if header != b'%PDF-':
                raise forms.ValidationError('The uploaded file is not a valid PDF receipt.')
        else:
            raise forms.ValidationError('Upload a PNG or JPEG image, or a PDF.')

        return receipt


class PreparationRequestForm(forms.Form):
    """Collect text input while requiring consent to AI provider processing."""

    request_reference = forms.UUIDField(widget=forms.HiddenInput())
    company_name = forms.CharField(
        max_length=120,
        required=False,
        label='Company (optional)',
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'organization'}),
    )
    job_title = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'organization-title'}),
    )
    role_family = forms.ChoiceField(
        choices=profile_choices(),
        initial='general-software-engineering',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    seniority = forms.ChoiceField(
        choices=[(key, value['label']) for key, value in SENIORITY_LEVELS.items()],
        initial='entry',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    job_description = forms.CharField(
        max_length=25000,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 9}),
    )
    resume_text = forms.CharField(
        help_text='Paste readable resume text, including work, projects, skills, education, and transferable experience. Image-only or very short text may not provide enough evidence.',
        max_length=25000,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 12}),
    )
    consent_to_ai_provider = forms.BooleanField(
        label='I agree to send this resume text and job description to the configured AI provider for analysis.',
        required=True,
    )
