

# models.py
from django.db import models
from django.utils import timezone

class Contact(models.Model):
    SUBJECT_CHOICES = [
        ('general', 'General Question'),
        ('career', 'Career Path Guidance'),
        ('learning', 'Learning Path or Exam Practice'),
        ('support', 'Account or Technical Support'),
        ('interview', 'Interview Preparation'),
        ('partnership', 'Partnership or Business Inquiry'),
        ('feedback', 'Feedback or Suggestion'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    subject = models.CharField(max_length=50, choices=SUBJECT_CHOICES )
    message = models.TextField()
    submitted_at = models.DateTimeField(default=timezone.now)
    is_resolved = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    
    class Meta:
        ordering = ['-submitted_at']
        verbose_name = 'Contact Form Submission'
        verbose_name_plural = 'Contact Form Submissions'
    
    def __str__(self):
        return f"{self.name} - {self.subject} ({self.submitted_at.strftime('%Y-%m-%d')})"
