from django.db import migrations, models


EXPERIENCE_CHOICES = [
    ('all', 'General — any experience'),
    ('fresher', 'Fresher — no professional experience'),
    ('under_1', 'Less than 1 year'),
    ('1_2', '1–2 years'),
    ('3_5', '3–5 years'),
    ('over_5', 'More than 5 years'),
]


class Migration(migrations.Migration):
    dependencies = [('careers', '0005_independent_learning_levels')]

    operations = [
        migrations.AddField(
            model_name='learningday',
            name='experience_band',
            field=models.CharField(
                choices=EXPERIENCE_CHOICES, default='all', max_length=20,
                help_text='General content is used only when no exact-band content exists for this day.',
            ),
        ),
        migrations.AddField(
            model_name='milestoneexam',
            name='experience_band',
            field=models.CharField(
                choices=EXPERIENCE_CHOICES, default='all', max_length=20,
                help_text='General milestone content is the fallback when no exact-band milestone exists.',
            ),
        ),
        migrations.RemoveConstraint(model_name='learningday', name='unique_day_per_role_level'),
        migrations.RemoveConstraint(model_name='milestoneexam', name='unique_milestone_per_role_level'),
        migrations.AddConstraint(
            model_name='learningday',
            constraint=models.UniqueConstraint(
                fields=('role', 'level', 'experience_band', 'day_number'),
                name='unique_day_role_path_experience_number',
            ),
        ),
        migrations.AddConstraint(
            model_name='milestoneexam',
            constraint=models.UniqueConstraint(
                fields=('role', 'level', 'experience_band', 'number'),
                name='unique_milestone_role_path_experience_number',
            ),
        ),
        migrations.AlterModelOptions(
            name='learningday', options={'ordering': ['role', 'level', 'experience_band', 'day_number']},
        ),
        migrations.AlterModelOptions(
            name='milestoneexam', options={'ordering': ['role', 'level', 'experience_band', 'number']},
        ),
    ]
