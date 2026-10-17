# (file intentionally left blank)
# Do NOT run this file directly with `python populate_creativity_data.py`.
# Instead, run it inside Django shell:
#   python manage.py shell
#   >>> exec(open('populate_creativity_data.py').read())
# Or, convert this script to a Django management command for best practice.

import os
from django.contrib.auth import get_user_model
from core.models import Topic, Dataset, Problem  
from django.core.files import File


User = get_user_model()

# ---- Create a dummy user (optional) ----
admin_user, _ = User.objects.get_or_create(
    username='admin',
    defaults={'email': 'admin@techphile.in', 'is_staff': True, 'is_superuser': True}
)

# ---- Delete all existing topics, datasets, and problems ----
Topic.objects.all().delete()
Dataset.objects.all().delete()
Problem.objects.all().delete()

print("All Topic, Dataset, and Problem records deleted.")

# ---- Create AI/ML Topics ----
topics = [
    {"name": "Machine Learning", "icon": "📊", "color": "#1abc9c"},
    {"name": "Deep Learning", "icon": "🧠", "color": "#9b59b6"},
    {"name": "Computer Vision", "icon": "📷", "color": "#e67e22"},
    {"name": "NLP", "icon": "💬", "color": "#3498db"},
    {"name": "Generative AI", "icon": "🎨", "color": "#f39c12"},
]

topic_objs = {}
for t in topics:
    obj, _ = Topic.objects.get_or_create(
        name=t["name"],
        defaults={
            "description": f"This topic covers {t['name']} problems.",
            "icon": t["icon"],
            "color": t["color"],
        }
    )
    topic_objs[t["name"]] = obj

# ---- Create Datasets ----
dataset_dir = os.path.join('datasets')  # make sure datasets folder exists
os.makedirs(dataset_dir, exist_ok=True)

# Dataset: Titanic
titanic_data = """PassengerId,Survived,Pclass,Name,Sex,Age
1,0,3,Braund,male,22
2,1,1,Cumings,female,38
3,1,3,Heikkinen,female,26
4,1,1,Futrelle,female,35
5,0,3,Allen,male,35
"""
titanic_path = os.path.join(dataset_dir, 'titanic.csv')
with open(titanic_path, 'w') as f:
    f.write(titanic_data)

# Create dataset entry
with open(titanic_path, 'rb') as f:
    titanic_dataset, _ = Dataset.objects.get_or_create(
        name="Titanic Dataset",
        defaults={
            "filename": "titanic.csv",
            "description": "Survival data from Titanic shipwreck.",
            "file": File(f, name="titanic.csv"),
            "uploaded_by": admin_user,
            "is_public": True,
            "mime_type": "text/csv",
            "file_size": os.path.getsize(titanic_path)
        }
    )

# ---- Create Problems ----
Problem.objects.get_or_create(
    title="Display Top 5 Rows of Titanic Dataset",
    topic=topic_objs["Machine Learning"],
    dataset=titanic_dataset,
    difficulty='beginner',
    description="Load the Titanic dataset and print the top 5 rows using Pandas.",
    starter_code='''import pandas as pd\ndf = pd.read_csv('/datasets/titanic.csv')\nprint(df.head())''',
    expected_output='''| PassengerId | Survived | Pclass | Name      | Sex    | Age |\n|------------|----------|--------|-----------|--------|-----|\n| 1          | 0        | 3      | Braund    | male   | 22  |\n| 2          | 1        | 1      | Cumings   | female | 38  |\n| 3          | 1        | 3      | Heikkinen | female | 26  |\n| 4          | 1        | 1      | Futrelle  | female | 35  |\n| 5          | 0        | 3      | Allen     | male   | 35  |''',
    solution='''import pandas as pd\ndf = pd.read_csv('/datasets/titanic.csv')\nprint(df.head())''',
    points=100,
    created_by=admin_user
)


