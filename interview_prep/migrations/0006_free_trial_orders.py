from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('interview_prep', '0005_marketresearchcache_cost_usd'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='premiumorder',
            name='interview_prep_order_amount_positive',
        ),
        migrations.AlterField(
            model_name='premiumorder',
            name='amount',
            field=models.DecimalField(
                decimal_places=2,
                max_digits=8,
                validators=[MinValueValidator(0)],
            ),
        ),
        migrations.AddConstraint(
            model_name='premiumorder',
            constraint=models.CheckConstraint(
                check=models.Q(('amount__gte', 0)),
                name='interview_prep_order_amount_nonnegative',
            ),
        ),
        migrations.AddConstraint(
            model_name='premiumorder',
            constraint=models.UniqueConstraint(
                condition=models.Q(('plan_code', 'free_trial')),
                fields=('user',),
                name='interview_prep_one_free_trial_per_user',
            ),
        ),
    ]
