# Common setup for all population scripts
import os
from django.contrib.auth import get_user_model
from core.models import Topic, Dataset, Problem
from django.core.files import File
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'techphile_exams.settings')
django.setup()



User = get_user_model()

def get_admin_user():
    admin_user, _ = User.objects.get_or_create(
        username='admin',
        defaults={'email': 'admin@techphile.in', 'is_staff': True, 'is_superuser': True}
    )
    return admin_user

def create_dataset(name, content, filename, description, admin_user):
    dataset_dir = os.path.join('datasets')
    os.makedirs(dataset_dir, exist_ok=True)
    
    filepath = os.path.join(dataset_dir, filename)
    with open(filepath, 'w') as f:
        f.write(content)
    
    with open(filepath, 'rb') as f:
        dataset, _ = Dataset.objects.get_or_create(
            name=name,
            defaults={
                "filename": filename,
                "description": description,
                "file": File(f, name=filename),
                "uploaded_by": admin_user,
                "is_public": True,
                "mime_type": "text/csv",
                "file_size": os.path.getsize(filepath)
            }
        )
    return dataset 