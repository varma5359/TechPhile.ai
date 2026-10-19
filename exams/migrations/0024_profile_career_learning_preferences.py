from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('careers', '0006_experience_targeted_curriculum'),
        ('exams', '0023_alter_profile_timezone'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile', name='career_role',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name='learner_profiles', to='careers.careerrole',
            ),
        ),
        migrations.AddField(
            model_name='profile', name='experience_band',
            field=models.CharField(
                blank=True, choices=[
                    ('fresher', 'Fresher — no professional experience'),
                    ('under_1', 'Less than 1 year'), ('1_2', '1–2 years'),
                    ('3_5', '3–5 years'), ('over_5', 'More than 5 years'),
                ], default='', max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='profile', name='learning_path',
            field=models.CharField(
                blank=True, choices=[('beginner', 'Fresher'), ('experienced', 'Experienced')],
                default='', help_text='Leave blank to use the experience-based recommendation until a path is selected.',
                max_length=20,
            ),
        ),
    ]
