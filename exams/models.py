
# Exam and Quiz Section
    # Category, Exam, Question, Answer ,ExamAttempt, UserAnswer, Bookmark

#Interview Management Section
    #Interviewer, Applicant

#User Profile & Preferences
     # Profile with theme, language, notification preferences, etc.


from django.db import models  # Add this import
from datetime import timezone
from django.conf import settings
from django.urls import reverse
from jsonschema import ValidationError
from django.contrib.auth.models import User  # Ensure this is imported correctly
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Categories"
    
    def __str__(self):
        return self.name


class Exam(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    description = models.TextField()
    is_popular = models.BooleanField(default=False)
    is_new = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['category', 'title']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            # Remove spaces and special characters from slug
            self.slug = slugify(self.title).replace(' ', '-')
        super().save(*args, **kwargs)

class Question(models.Model):
    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    QUESTION_TYPE_CHOICES = [
        ('mcq', 'Multiple Choice'),
        ('tf', 'True/False'),
        ('code', 'Coding Question'),

    ]
    title = models.CharField(max_length=255, default="Untitled")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='questions')
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions', null=True, blank=True)
    question_text = models.TextField()
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPE_CHOICES, default='mcq')
    marks = models.PositiveIntegerField(default=1)
    explanation = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='beginner')
    set_number = models.PositiveIntegerField(default=1)  # Set within level
    
    class Meta:
        ordering = ['category', 'level', 'set_number', 'order','title']
        unique_together = ['category', 'level', 'set_number', 'order','title']
    
    def __str__(self):
        return f"{self.category.name} - {self.get_level_display()} - Set {self.set_number}: Q{self.order}"

class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    answer_text = models.TextField()
    is_correct = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.answer_text[:50]}... ({'Correct' if self.is_correct else 'Incorrect'})"

class ExamAttempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.exam.title}"
    
    @property
    def duration(self):
        if self.completed_at and self.started_at:
            delta = self.completed_at - self.started_at
            # Convert to minutes and seconds
            minutes = delta.seconds // 60
            seconds = delta.seconds % 60
            return f"{minutes}m {seconds}s"
        return "Not completed"

class UserAnswer(models.Model):
    attempt = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE, related_name='user_answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_answer = models.ForeignKey(Answer, on_delete=models.CASCADE, null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Answer to Q{self.question.order} in {self.attempt}"

class Interviewer(models.Model):
    name = models.CharField(max_length=100, default='Unnamed Interviewer')
    specialization = models.CharField(max_length=100)
    max_interviews_per_day = models.PositiveIntegerField(default=3)
    is_active = models.BooleanField(default=True)
    bio = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.specialization})"
    

from django.db import models
from django.contrib.auth.models import User

class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey('Question', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'question')



# application of interview models 
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db import models

class Applicant(models.Model):
    interviewer = models.ForeignKey(
        Interviewer, 
        on_delete=models.SET_NULL,  
        null=True,                  
        blank=True,                 
    )
    assigned_date = models.DateTimeField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    INTERVIEW_TYPE_CHOICES = [
        ('technical', 'Technical'),
        ('hr', 'HR'),
        ('aptitude', 'Aptitude'),
    ]
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ]
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled'),
    ]

    EXPERIENCE_CHOICES = [
        ('Fresher', 'Fresher (0 years)'),
        ('1-2', '1-2 years'),
        ('3-5', '3-5 years'),
        ('5+', '5+ years'),
    ]

    HEARD_CHOICES = [
        ('LinkedIn', 'LinkedIn'),
        ('Instagram', 'Instagram'),
        ('Facebook', 'Facebook'),
        ('Twitter', 'Twitter (X)'),
        ('Friend', 'Friend/Colleague'),
        ('Google', 'Google Search'),
        ('Other', 'Other'),
    ]

    QUALIFICATION_CHOICES = [
        ('B.Tech/B.E.', 'B.Tech/B.E.'),
        ('M.Tech/M.E.', 'M.Tech/M.E.'),
        ('BCA', 'BCA'),
        ('MCA', 'MCA'),
        ('B.Sc', 'B.Sc'),
        ('M.Sc', 'M.Sc'),
        ('Diploma', 'Diploma'),
        ('Other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    email = models.EmailField()
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    phone = models.CharField(max_length=15)
    year_of_passout = models.CharField(max_length=4)
    qualification = models.CharField(max_length=30)
    skills = models.TextField()
    additional_skills = models.TextField(blank=True, null=True)
    experience = models.CharField(max_length=10)
    heard_from = models.CharField(max_length=20)
    resume = models.FileField(upload_to='resumes/')
    interview_date = models.DateField(null=True, blank=True)
    interview_time = models.CharField(max_length=50, null=True, blank=True)
    interview_link = models.URLField(null=True, blank=True)
    interview_id = models.UUIDField(unique=True, null=True, blank=True)
    confirmed = models.BooleanField(default=False)
    reminder_sent = models.BooleanField(default=False)
    interview_type = models.CharField(max_length=20, choices=INTERVIEW_TYPE_CHOICES, default='technical')
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    rating = models.FloatField(default=0.0)
    feedback = models.TextField(blank=True, null=True, help_text="Detailed feedback from the interviewer")
    # Removed evaluator_name as interviewer already provides the necessary information
    evaluator_notes = models.TextField(blank=True, null=True, help_text="Private notes for evaluators")
    evaluator_name = models.CharField(max_length=100, null=True, blank=True)
    technical_rating = models.FloatField(
        blank=True, null=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Technical skills rating (1-5)"
    )
    communication_rating = models.FloatField(
        blank=True, null=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Communication skills rating (1-5)"
    )
    problem_solving_rating = models.FloatField(
        blank=True, null=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Problem solving rating (1-5)"
    )

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
    
    @property
    def skills_list(self):
        return [skill.strip() for skill in self.skills.split(',')]
    
    def get_absolute_url(self):
        return reverse('view_interview', kwargs={'pk': self.pk})
    
    def clean(self):
        if self.interview_date and self.interview_date < timezone.now().date():
            raise ValidationError("Interview date cannot be in the past.")
    
    class Meta:
        ordering = ['-interview_date', '-interview_time']




from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.urls import reverse
import pytz
from careers.choices import EXPERIENCE_CHOICES, LEVEL_CHOICES

User = get_user_model()

def user_directory_path(instance, filename):
    username = instance.user.username
    return f'profile_photos/{username}/{filename}'

class Profile(models.Model):
    THEME_CHOICES = [
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('system', 'System Default')
    ]
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('hi', 'Hindi'),
        ('es', 'Spanish')
    ]
    DASHBOARD_VIEW_CHOICES = [
        ('default', 'Default View'),
        ('compact', 'Compact View'),
        ('detailed', 'Detailed View')
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    career_role = models.ForeignKey(
        'careers.CareerRole', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='learner_profiles',
    )
    experience_band = models.CharField(
        max_length=20, choices=EXPERIENCE_CHOICES, blank=True, default='',
    )
    learning_path = models.CharField(
        max_length=20, choices=LEVEL_CHOICES, blank=True, default='',
        help_text='Leave blank to use the experience-based recommendation until a path is selected.',
    )
    photo = models.ImageField(upload_to=user_directory_path, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)

    # Notification Preferences
    exam_notifications = models.BooleanField(default=True)
    interview_notifications = models.BooleanField(default=True)
    promotional_emails = models.BooleanField(default=False)
    push_reminders = models.BooleanField(default=True)
    important_alerts = models.BooleanField(default=True)

    # System Preferences
    timezone = models.CharField(max_length=100, choices=[(tz, tz) for tz in pytz.common_timezones], default='UTC')
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='en')
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='light')
    dashboard_view = models.CharField(max_length=10, choices=DASHBOARD_VIEW_CHOICES, default='default')

    # Timestamps
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def apply_theme(self):
        """Returns the effective theme considering system preference"""
        if self.theme == 'system':
            return 'light'  # Or add logic for system detection
        return self.theme

    def get_dashboard_settings(self):
        """Returns dashboard display preferences"""
        return {
            'view': self.dashboard_view,
            'compact': self.dashboard_view == 'compact',
            'detailed': self.dashboard_view == 'detailed'
        }

    def update_preferences(self, **kwargs):
        """Update multiple preferences at once"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        self.save()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()



class InterviewFeedback(models.Model):
    RECOMMENDATION_CHOICES = [
        ('strong_no', 'Strong No Hire'),
        ('no', 'No Hire'),
        ('neutral', 'Neutral'),
        ('yes', 'Hire'),
        ('strong_yes', 'Strong Hire'),
    ]

    interview = models.OneToOneField(Applicant,on_delete=models.CASCADE,related_name='interview_feedback')
    evaluator = models.ForeignKey(Interviewer,on_delete=models.SET_NULL,null=True,related_name='given_feedbacks')
    technical_rating = models.FloatField(validators=[MinValueValidator(1), MaxValueValidator(5)],help_text="Technical skills rating (1-5)")
    communication_rating = models.FloatField(validators=[MinValueValidator(1), MaxValueValidator(5)],help_text="Communication skills rating (1-5)")
    problem_solving_rating = models.FloatField(validators=[MinValueValidator(1), MaxValueValidator(5)],help_text="Problem solving rating (1-5)")
    feedback = models.TextField(help_text="Detailed feedback for the candidate")
    evaluator_notes = models.TextField(blank=True,null=True,help_text="Private notes for hiring team")
    recommendation = models.CharField(max_length=20,choices=RECOMMENDATION_CHOICES,help_text="Overall hiring recommendation")
    strengths = models.TextField(help_text="Key strengths observed")
    areas_for_improvement = models.TextField(help_text="Areas needing development")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Interview Feedbacks"
        ordering = ['-created_at']

    def __str__(self):
        return f"Feedback for {self.interview} by {self.evaluator}"

    @property
    def overall_score(self):
        return round((
            self.technical_rating + 
            self.communication_rating + 
            self.problem_solving_rating
        ) / 3, 1)

    def save(self, *args, **kwargs):
        # Update the related Applicant model when feedback is saved
        super().save(*args, **kwargs)
        self.interview.technical_rating = self.technical_rating
        self.interview.communication_rating = self.communication_rating
        self.interview.problem_solving_rating = self.problem_solving_rating
        self.interview.feedback = self.feedback
        self.interview.status = 'completed'
        self.interview.save()
