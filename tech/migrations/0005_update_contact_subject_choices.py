from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tech', '0004_alter_contact_subject'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contact',
            name='subject',
            field=models.CharField(
                choices=[
                    ('general', 'General Question'),
                    ('career', 'Career Path Guidance'),
                    ('learning', 'Learning Path or Exam Practice'),
                    ('support', 'Account or Technical Support'),
                    ('interview', 'Interview Preparation'),
                    ('partnership', 'Partnership or Business Inquiry'),
                    ('feedback', 'Feedback or Suggestion'),
                    ('other', 'Other'),
                ],
                max_length=50,
            ),
        ),
    ]
