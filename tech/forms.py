from django import forms
from .models import Contact

from django import forms
from .models import Contact

class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['name', 'email', 'phone', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Your full name',
                'class': 'form-control'
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': 'Your email address',
                'class': 'form-control'
            }),
            'phone': forms.TextInput(attrs={
                'placeholder': 'Phone number (optional)',
                'class': 'form-control'
            }),
            'subject': forms.Select(attrs={
                'class': 'form-control'
            }),
            'message': forms.Textarea(attrs={
                'placeholder': 'Your message...',
                'class': 'form-control',
                'rows': 5
            }),
        }

    def __init__(self, *args, **kwargs):
        super(ContactForm, self).__init__(*args, **kwargs)
        # Add placeholder option to subject dropdown
        self.fields['subject'].choices = [('', 'Select your inquiry type')] + list(self.fields['subject'].choices)

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name or len(name) < 3:
            raise forms.ValidationError("Please enter your full name (at least 3 characters).")
        return name

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise forms.ValidationError("Email is required.")
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone and not phone.isdigit():
            raise forms.ValidationError("Phone number should contain only digits.")
        return phone

    def clean_subject(self):
        subject = self.cleaned_data.get('subject')
        if not subject:
            raise forms.ValidationError("Select your inquiry type.")
        return subject

    def clean_message(self):
        message = self.cleaned_data.get('message')
        if not message or len(message) < 10:
            raise forms.ValidationError("Message should be at least 10 characters long.")
        return message
