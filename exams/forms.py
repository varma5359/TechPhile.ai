from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm  # Add this import
from .models import Applicant, ExamAttempt, UserAnswer, Interviewer

class ExamAttemptForm(forms.ModelForm):
    class Meta:
        model = ExamAttempt
        fields = []
from django import forms
from .models import UserAnswer

class UserAnswerForm(forms.ModelForm):
    class Meta:
        model = UserAnswer
        fields = ['selected_answer']
        widgets = {
            'selected_answer': forms.RadioSelect()
        }

    def __init__(self, *args, question=None, **kwargs):
        super().__init__(*args, **kwargs)
        if question:
            # Restrict choices to only answers for this question
            self.fields['selected_answer'].queryset = question.answers.all()
            # Customize how answers are displayed
            self.fields['selected_answer'].label_from_instance = lambda obj: obj.answer_text
            self.fields['selected_answer'].empty_label = None

from django import forms
from .models import Profile
from careers.models import CareerRole


class CareerLearningPreferencesForm(forms.ModelForm):
    """Validated learner choices, kept separate from account/profile basics."""

    class Meta:
        model = Profile
        fields = ['career_role', 'experience_band', 'learning_path']
        widgets = {
            'career_role': forms.Select(attrs={'class': 'form-select'}),
            'experience_band': forms.Select(attrs={'class': 'form-select'}),
            'learning_path': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['career_role'].queryset = CareerRole.objects.filter(is_published=True)
        self.fields['career_role'].required = False
        self.fields['experience_band'].required = False
        self.fields['learning_path'].required = False

from django import forms
from django.contrib.auth.forms import PasswordChangeForm
import re
from .models import Profile


MAX_PROFILE_PHOTO_BYTES = 2 * 1024 * 1024


class ProfilePhotoField(forms.ImageField):
    """Accept only actual JPEG/PNG images within the settings page limit."""

    def to_python(self, data):
        if data and getattr(data, 'size', 0) > MAX_PROFILE_PHOTO_BYTES:
            raise forms.ValidationError('Profile photos must be 2 MB or smaller.')
        image = super().to_python(data)
        if image:
            image_format = getattr(getattr(image, 'image', None), 'format', None)
            if image_format not in {'JPEG', 'PNG'}:
                raise forms.ValidationError('Upload a valid JPG or PNG image.')
        return image

class ProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    photo = ProfilePhotoField(
        required=False,
        widget=forms.FileInput(attrs={
            'accept': '.jpg,.jpeg,.png,image/jpeg,image/png',
            'class': 'form-control',
        }),
    )
    
    class Meta:
        model = Profile
        fields = ['photo', 'phone', 'first_name', 'last_name']
        widgets = {
            'phone': forms.TextInput(attrs={
                'placeholder': '+91XXXXXXXXXX', 'class': 'form-control',
                'autocomplete': 'tel',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name

    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').strip()
        if not phone:
            return ''
        if not re.fullmatch(r'\+?[0-9().\s-]+', phone):
            raise forms.ValidationError('Use digits and standard phone separators only.')
        digit_count = sum(character.isdigit() for character in phone)
        if not 7 <= digit_count <= 15:
            raise forms.ValidationError('Enter a phone number with 7 to 15 digits.')
        return phone
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            profile.save()
            user = profile.user
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.save()
        return profile


class ProfilePhotoForm(forms.ModelForm):
    photo = ProfilePhotoField(required=False)

    class Meta:
        model = Profile
        fields = ['photo']
        widgets = {'photo': forms.FileInput(attrs={'class': 'form-control'})}

class CustomPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        label="Current Password",
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password'}),
        strip=False,
    )
    new_password1 = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        strip=False,
    )
    new_password2 = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        strip=False,
    )

class NotificationSettingsForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            'exam_notifications',
            'interview_notifications',
            'promotional_emails',
            'push_reminders',
            'important_alerts'
        ]
        widgets = {
            'exam_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input me-2'}),
            'interview_notifications': forms.CheckboxInput(attrs={'class': 'form-check-input me-2'}),
            'promotional_emails': forms.CheckboxInput(attrs={'class': 'form-check-input me-2'}),
            'push_reminders': forms.CheckboxInput(attrs={'class': 'form-check-input me-2'}),
            'important_alerts': forms.CheckboxInput(attrs={'class': 'form-check-input me-2'}),
        }

from django import forms
from .models import Profile

class PreferencesForm(forms.ModelForm):
    THEME_CHOICES = (
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('system', 'System Default'),
        ('ocean', 'Ocean'),
        ('aurora', 'Aurora'),
        ('sunset', 'Sunset'),
        ('forest', 'Forest'),
        ('sky', 'Sky'),
        ('midnight', 'Midnight'),
        ('rose', 'Rose'),
        ('lavender', 'Lavender'),
        ('mint', 'Mint'),
        ('slate', 'Slate'),
        ('sand', 'Sand'),
        ('plum', 'Plum'),
    )
    theme = forms.ChoiceField(
        choices=THEME_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
    )

    class Meta:
        model = Profile
        fields = ['theme', 'language', 'dashboard_view', 'timezone']
        widgets = {
            'language': forms.Select(attrs={'class': 'form-select'}),
            'dashboard_view': forms.Select(attrs={'class': 'form-select'}),
            'timezone': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Optional: Add Bootstrap classes for better UI
        for field in self.fields.values():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            if isinstance(field.widget, forms.RadioSelect):
                field.widget.attrs['class'] = 'form-check-input'

                

class InterviewStatusForm(forms.ModelForm):
    """
    Form to update the interview evaluation details.
    """
    class Meta:
        model = Applicant
        fields = ['interview_type', 'difficulty', 'status', 'rating', 'evaluator_name']
        widgets = {
            'interview_type': forms.Select(attrs={'class': 'form-select'}),
            'difficulty': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'rating': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 5,
                'step': 0.1
            }),
            'evaluator_name': forms.TextInput(attrs={'class': 'form-control'}),
        }


class RescheduleInterviewForm(forms.ModelForm):
    """
    Form to change the interview date and time for an applicant.
    """
    class Meta:
        model = Applicant
        fields = ['interview_date', 'interview_time']
        widgets = {
            'interview_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'interview_time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-control'
            }),
        }




from django import forms
from .models import Applicant
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
from django.db.models import Count

class InterviewStatusForm(forms.ModelForm):
    class Meta:
        model = Applicant
        fields = ['first_name', 'last_name', 'email', 'phone', 'year_of_passout', 
                 'qualification', 'experience', 'skills', 'additional_skills', 
                 'resume', 'interview_type', 'difficulty']

from django import forms
from .models import InterviewFeedback

class InterviewFeedbackForm(forms.ModelForm):
    class Meta:
        model = InterviewFeedback
        fields = [
            'technical_rating',
            'communication_rating',
            'problem_solving_rating',
            'feedback',
            'evaluator_notes',
            'recommendation',
            'strengths',
            'areas_for_improvement'
        ]
        widgets = {
            'technical_rating': forms.NumberInput(attrs={'min': 1,'max': 5,'step': 0.5,'class': 'form-control'}),
            'communication_rating': forms.NumberInput(attrs={'min': 1,'max': 5,'step': 0.5,'class': 'form-control' }),
            'problem_solving_rating': forms.NumberInput(attrs={'min': 1,'max': 5,'step': 0.5,'class': 'form-control' }),
            'feedback': forms.Textarea(attrs={'rows': 5,'class': 'form-control','placeholder': 'Detailed feedback for the candidate...'}),
            'evaluator_notes': forms.Textarea(attrs={'rows': 3,'class': 'form-control','placeholder': 'Private notes for hiring team...' }),
            'strengths': forms.Textarea(attrs={ 'rows': 3, 'class': 'form-control', 'placeholder': 'Key strengths observed...'}),
            'areas_for_improvement': forms.Textarea(attrs={'rows': 3,'class': 'form-control','placeholder': 'Areas needing development...' }),
        }

class RescheduleInterviewForm(forms.ModelForm):
    class Meta:
        model = Applicant
        fields = ['interview_date', 'interview_time']
        
    def clean_interview_date(self):
        date = self.cleaned_data.get('interview_date')
        if date and date < (timezone.now().date() + timedelta(days=1)):
            raise forms.ValidationError("Interview must be scheduled at least 24 hours in advance.")
        return date
    


class AssignInterviewerForm(forms.ModelForm):
    class Meta:
        model = Applicant
        fields = ['interviewer']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['interviewer'].label_from_instance = lambda obj: (
            f"{obj.user.get_full_name() or obj.user.username} - {obj.specialization}"
        )
        self.fields['interviewer'].queryset = Interviewer.objects.filter(
            is_active=True
        ).select_related('user')
