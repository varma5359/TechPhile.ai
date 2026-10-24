import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def refuse_unsafe_reverse(apps, schema_editor):
    """Stop before reversing schema operations that could discard trial history."""
    alias = schema_editor.connection.alias
    TrialUsage = apps.get_model('interview_prep', 'TrialUsage')
    if TrialUsage.objects.using(alias).exists():
        raise RuntimeError(
            'Migration 0007 cannot be reversed while TrialUsage history exists. '
            'Keep this migration applied; do not delete trial records to force rollback.'
        )

    PreparationSet = apps.get_model('interview_prep', 'PreparationSet')
    if PreparationSet.objects.using(alias).filter(access_period__isnull=True).exists():
        raise RuntimeError(
            'Migration 0007 cannot be reversed while preparations have no access period.'
        )


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('interview_prep', '0006_free_trial_orders'),
    ]

    operations = [
        migrations.AlterField(
            model_name='preparationset',
            name='access_period',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='preparation_sets',
                to='interview_prep.premiumaccessperiod',
            ),
        ),
        migrations.CreateModel(
            name='TrialUsage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('feature_code', models.CharField(default='interview_prep', max_length=64)),
                ('idempotency_key', models.UUIDField()),
                ('request_fingerprint', models.CharField(max_length=64)),
                ('started_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('preparation', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='trial_usage', to='interview_prep.preparationset')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='interview_prep_trial_usages', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-started_at'],
                'indexes': [models.Index(fields=['user', 'started_at'], name='ipp_trial_user_started_idx')],
                'constraints': [models.UniqueConstraint(fields=('user', 'feature_code', 'idempotency_key'), name='interview_prep_trial_unique_request')],
            },
        ),
        # Reverse operations run in reverse order, so this guard executes before
        # Django can drop TrialUsage or restore the non-null foreign key.
        migrations.RunPython(migrations.RunPython.noop, reverse_code=refuse_unsafe_reverse),
    ]
