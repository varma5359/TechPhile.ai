from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from coding.models import UserProfile
from exams.models import Profile  # Import from exam app

@receiver(post_save, sender=User)
def create_user_profiles(sender, instance, created, **kwargs):
    if created and not Profile.objects.filter(user=instance).exists():
        UserProfile.objects.create(user=instance)
        Profile.objects.create(user=instance)
