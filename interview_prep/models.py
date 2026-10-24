import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from .private_storage import PrivateReceiptStorage


class PremiumOrder(models.Model):
    """A server-priced monthly Premium order for one learner account."""

    class Status(models.TextChoices):
        PENDING_PAYMENT = 'pending_payment', 'Pending payment'
        SUBMITTED = 'submitted', 'Submitted for verification'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        CANCELLED = 'cancelled', 'Cancelled'

    public_reference = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='interview_prep_orders',
    )
    plan_code = models.CharField(
        max_length=32,
        default='premium_monthly',
        editable=False,
    )
    amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    currency = models.CharField(
        max_length=3,
        default=settings.INTERVIEW_PREP_CURRENCY,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gte=0),
                name='interview_prep_order_amount_nonnegative',
            ),
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(plan_code='free_trial'),
                name='interview_prep_one_free_trial_per_user',
            ),
        ]

    def __str__(self):
        return f'{self.public_reference} — {self.user}'

    @classmethod
    def create_monthly(cls, user):
        """Create an order using the monthly price configured on the server."""
        return cls.objects.create(
            user=user,
            plan_code='premium_monthly',
            amount=settings.INTERVIEW_PREP_MONTHLY_PRICE,
            currency=settings.INTERVIEW_PREP_CURRENCY,
        )


class PaymentSubmission(models.Model):
    """A learner's UPI payment claim awaiting independent verification."""

    order = models.ForeignKey(
        PremiumOrder,
        on_delete=models.PROTECT,
        related_name='payment_submissions',
    )
    transaction_reference = models.CharField(max_length=128, unique=True)
    receipt_file = models.FileField(
        upload_to='interview_prep/receipts/%Y/%m/',
        storage=PrivateReceiptStorage(),
        blank=True,
    )
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']
        permissions = [
            ('approve_payment', 'Can approve or reject Premium payment submissions'),
        ]

    def save(self, *args, **kwargs):
        """Normalize the reference so case variations cannot bypass uniqueness."""
        self.transaction_reference = self.transaction_reference.strip().upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.transaction_reference} — {self.order.public_reference}'


class PaymentReview(models.Model):
    """An immutable administrator decision for a submitted payment claim."""

    class Decision(models.TextChoices):
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    submission = models.OneToOneField(
        PaymentSubmission,
        on_delete=models.PROTECT,
        related_name='review',
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='interview_prep_payment_reviews',
    )
    decision = models.CharField(max_length=10, choices=Decision.choices)
    notes = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ['-reviewed_at']

    def __str__(self):
        return f'{self.get_decision_display()} — {self.submission.order.public_reference}'


class PremiumAccessPeriod(models.Model):
    """A monthly account entitlement granted from an approved order."""

    order = models.OneToOneField(
        PremiumOrder,
        on_delete=models.PROTECT,
        related_name='access_period',
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-starts_at']
        constraints = [
            models.CheckConstraint(
                check=models.Q(ends_at__gt=models.F('starts_at')),
                name='interview_prep_access_period_positive',
            ),
        ]

    @property
    def is_active(self):
        """Return whether this approved order currently grants access."""
        now = timezone.now()
        return (
            self.order.status == PremiumOrder.Status.APPROVED
            and self.starts_at <= now < self.ends_at
        )

    def __str__(self):
        return f'{self.order.user} — {self.starts_at:%Y-%m-%d} to {self.ends_at:%Y-%m-%d}'


class PreparationSet(models.Model):
    """Persist one generated preparation set for its owner and access month."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='interview_preparation_sets',
    )
    access_period = models.ForeignKey(
        PremiumAccessPeriod,
        on_delete=models.PROTECT,
        related_name='preparation_sets',
    )
    request_reference = models.UUIDField(default=uuid.uuid4, editable=False)
    set_number = models.PositiveSmallIntegerField(editable=False)
    company_name = models.CharField(max_length=120)
    job_title = models.CharField(max_length=150)
    role_family = models.CharField(max_length=64, default='general-software-engineering')
    seniority = models.CharField(max_length=16, default='entry')
    job_description = models.TextField()
    input_fingerprint = models.CharField(max_length=64, null=True, blank=True)
    generated_content = models.JSONField()
    completed_question_ids = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'request_reference'],
                name='interview_prep_unique_request_per_owner',
            ),
            models.UniqueConstraint(
                fields=['owner', 'access_period', 'input_fingerprint'],
                name='interview_prep_unique_input_per_period',
            ),
            models.UniqueConstraint(
                fields=['access_period', 'set_number'],
                name='interview_prep_max_two_sets_per_month',
            ),
            models.CheckConstraint(
                check=models.Q(set_number__gte=1, set_number__lte=2),
                name='interview_prep_set_number_one_or_two',
            ),
        ]

    def __str__(self):
        return f'Set {self.set_number} — {self.company_name} / {self.job_title}'


class MarketResearchCache(models.Model):
    """Cache public, dated market research to avoid repeated searches."""

    cache_key = models.CharField(max_length=64, unique=True)
    role_family = models.CharField(max_length=64)
    query = models.CharField(max_length=255)
    results = models.JSONField(default=list)
    provider = models.CharField(max_length=64)
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6, null=True, blank=True)
    fetched_at = models.DateTimeField()
    expires_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fetched_at']


class SavedQuestion(models.Model):
    """Keep a private snapshot of a question saved for later revision."""

    preparation_set = models.ForeignKey(
        PreparationSet,
        on_delete=models.CASCADE,
        related_name='saved_questions',
    )
    question_id = models.CharField(max_length=128)
    question_text = models.TextField()
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-saved_at']
        constraints = [
            models.UniqueConstraint(
                fields=['preparation_set', 'question_id'],
                name='interview_prep_unique_saved_question',
            ),
        ]

    def __str__(self):
        return f'{self.question_id} — {self.preparation_set}'
