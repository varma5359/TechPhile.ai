from django.db import migrations, models


def classify_existing_content_as_beginner(apps, schema_editor):
    """Keep every pre-existing path and its history in the Beginner track."""
    LearningDay = apps.get_model('careers', 'LearningDay')
    MilestoneExam = apps.get_model('careers', 'MilestoneExam')
    LearningDay.objects.using(schema_editor.connection.alias).all().update(level='beginner')
    MilestoneExam.objects.using(schema_editor.connection.alias).all().update(level='beginner')


class Migration(migrations.Migration):
    dependencies = [('careers', '0004_dayprogress_notes_completed_and_more')]

    operations = [
        migrations.AddField(
            model_name='learningday', name='level',
            field=models.CharField(choices=[('beginner', 'Fresher'), ('experienced', 'Experienced')],
                                   default='beginner', max_length=20),
        ),
        migrations.AddField(
            model_name='milestoneexam', name='level',
            field=models.CharField(choices=[('beginner', 'Fresher'), ('experienced', 'Experienced')],
                                   default='beginner', max_length=20),
        ),
        migrations.RunPython(classify_existing_content_as_beginner, migrations.RunPython.noop),
        migrations.RemoveConstraint(model_name='learningday', name='unique_day_per_role'),
        migrations.RemoveConstraint(model_name='milestoneexam', name='unique_milestone_per_role'),
        migrations.AddConstraint(
            model_name='learningday',
            constraint=models.UniqueConstraint(fields=('role', 'level', 'day_number'),
                                               name='unique_day_per_role_level'),
        ),
        migrations.AddConstraint(
            model_name='milestoneexam',
            constraint=models.UniqueConstraint(fields=('role', 'level', 'number'),
                                               name='unique_milestone_per_role_level'),
        ),
        migrations.AlterModelOptions(name='learningday', options={'ordering': ['role', 'level', 'day_number']}),
        migrations.AlterModelOptions(name='milestoneexam', options={'ordering': ['role', 'level', 'number']}),
    ]
