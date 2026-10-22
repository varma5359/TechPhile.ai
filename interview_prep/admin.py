import calendar
import mimetypes
from pathlib import Path

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Max
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import PaymentReview, PaymentSubmission, PremiumAccessPeriod, PremiumOrder, PreparationSet


class PaymentDecisionForm(forms.Form):
    """Capture an administrator's payment decision and internal review note."""

    decision = forms.ChoiceField(
        choices=PaymentReview.Decision.choices,
        widget=forms.RadioSelect,
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 4}),
        help_text='Explain the decision. A note is required when rejecting a claim.',
    )

    def clean(self):
        """Require an explanation when a payment claim is rejected."""
        cleaned_data = super().clean()
        if cleaned_data.get('decision') == PaymentReview.Decision.REJECTED and not cleaned_data.get('notes', '').strip():
            self.add_error('notes', 'Add a reason before rejecting this payment.')
        return cleaned_data


def one_month_after(value):
    """Return the same local calendar time one month after a datetime."""
    month = value.month % 12 + 1
    year = value.year + (1 if value.month == 12 else 0)
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


@admin.register(PaymentSubmission)
class PaymentSubmissionAdmin(admin.ModelAdmin):
    """Provide a read only queue and a permission checked review workflow."""

    list_display = (
        'order_reference',
        'owner_email',
        'amount',
        'currency',
        'transaction_reference',
        'order_status',
        'submitted_at',
    )
    list_filter = ('order__status', 'submitted_at')
    search_fields = ('transaction_reference', 'order__public_reference', 'order__user__email')
    readonly_fields = ('order', 'transaction_reference', 'receipt_file', 'submitted_at')
    date_hierarchy = 'submitted_at'
    ordering = ('submitted_at',)
    list_select_related = ('order', 'order__user')

    def get_urls(self):
        """Add staff protected review and private receipt download pages."""
        custom_urls = [
            path(
                '<int:object_id>/review/',
                self.admin_site.admin_view(self.review_view),
                name='interview_prep_paymentsubmission_review',
            ),
            path(
                '<int:object_id>/receipt/',
                self.admin_site.admin_view(self.receipt_view),
                name='interview_prep_paymentsubmission_receipt',
            ),
        ]
        return custom_urls + super().get_urls()

    def get_list_display(self, request):
        """Show the review link only to staff with the explicit review permission."""
        display = list(super().get_list_display(request))
        if request.user.has_perm('interview_prep.approve_payment'):
            display.append('review_action')
        return display

    @admin.display(description='Order reference', ordering='order__public_reference')
    def order_reference(self, obj):
        return obj.order.public_reference

    @admin.display(description='Learner', ordering='order__user__email')
    def owner_email(self, obj):
        return obj.order.user.email

    @admin.display(description='Amount')
    def amount(self, obj):
        return obj.order.amount

    @admin.display(description='Currency')
    def currency(self, obj):
        return obj.order.currency

    @admin.display(description='Order status', ordering='order__status')
    def order_status(self, obj):
        return obj.order.get_status_display()

    @admin.display(description='Review')
    def review_action(self, obj):
        url = reverse(
            'admin:interview_prep_paymentsubmission_review',
            args=[obj.pk],
        )
        return format_html('<a class="button" href="{}">Review payment</a>', url)

    def has_add_permission(self, request):
        """Prevent staff from fabricating learner payment submissions in admin."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Keep payment claims available as an audit record."""
        return False

    def review_view(self, request, object_id):
        """Review a claim and atomically update its order and access period."""
        if not request.user.has_perm('interview_prep.approve_payment'):
            raise PermissionDenied

        submission = get_object_or_404(
            PaymentSubmission.objects.select_related('order', 'order__user', 'review'),
            pk=object_id,
        )
        form = PaymentDecisionForm(data=request.POST if request.method == 'POST' else None)
        can_review = (
            submission.order.status == PremiumOrder.Status.SUBMITTED
            and not hasattr(submission, 'review')
            and submission.order.user_id != request.user.pk
        )

        if request.method == 'POST' and form.is_valid():
            try:
                with transaction.atomic():
                    locked_submission = PaymentSubmission.objects.select_related('order').get(pk=object_id)
                    locked_order = PremiumOrder.objects.select_for_update().get(pk=locked_submission.order_id)

                    if locked_order.status != PremiumOrder.Status.SUBMITTED:
                        form.add_error(None, 'This order is no longer awaiting review.')
                    elif PaymentReview.objects.filter(submission=locked_submission).exists():
                        form.add_error(None, 'A decision has already been recorded for this submission.')
                    elif locked_order.user_id == request.user.pk:
                        form.add_error(None, 'You cannot review or approve your own order.')
                    else:
                        decision = form.cleaned_data['decision']
                        PaymentReview.objects.create(
                            submission=locked_submission,
                            reviewer=request.user,
                            decision=decision,
                            notes=form.cleaned_data['notes'].strip(),
                        )
                        locked_order.status = decision
                        locked_order.save(update_fields=['status', 'updated_at'])

                        if decision == PaymentReview.Decision.APPROVED:
                            now = timezone.now()
                            latest_end = PremiumAccessPeriod.objects.filter(
                                order__user=locked_order.user,
                                order__status=PremiumOrder.Status.APPROVED,
                                ends_at__gt=now,
                            ).aggregate(latest=Max('ends_at'))['latest']
                            starts_at = max(now, latest_end) if latest_end else now
                            PremiumAccessPeriod.objects.create(
                                order=locked_order,
                                starts_at=starts_at,
                                ends_at=one_month_after(starts_at),
                            )

                        messages.success(request, f'Payment {decision} and review recorded.')
                        return redirect('admin:interview_prep_paymentsubmission_changelist')
            except PaymentSubmission.DoesNotExist as exc:
                raise Http404 from exc

        submission.refresh_from_db()
        context = {
            **self.admin_site.each_context(request),
            'opts': self.model._meta,
            'title': 'Review Premium payment',
            'submission': submission,
            'form': form,
            'can_review': can_review,
            'receipt_url': reverse(
                'admin:interview_prep_paymentsubmission_receipt',
                args=[submission.pk],
            ) if submission.receipt_file else None,
        }
        return render(request, 'admin/interview_prep/payment_review.html', context)

    def receipt_view(self, request, object_id):
        """Deliver a private receipt as an attachment to authorized reviewers."""
        if not request.user.has_perm('interview_prep.approve_payment'):
            raise PermissionDenied

        submission = get_object_or_404(PaymentSubmission, pk=object_id)
        if not submission.receipt_file:
            raise Http404

        filename = Path(submission.receipt_file.name).name
        content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        response = FileResponse(
            submission.receipt_file.open('rb'),
            as_attachment=True,
            filename=filename,
            content_type=content_type,
        )
        response['Cache-Control'] = 'private, no-store'
        response['X-Content-Type-Options'] = 'nosniff'
        return response


class ReadOnlyModelAdmin(admin.ModelAdmin):
    """Expose payment audit records without allowing edits or deletion."""

    def get_readonly_fields(self, request, obj=None):
        """Make every model field read only in the Django admin."""
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        """Create audit records only from the controlled review workflow."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Preserve historical payment and entitlement records."""
        return False


@admin.register(PremiumOrder)
class PremiumOrderAdmin(ReadOnlyModelAdmin):
    list_display = ('public_reference', 'user', 'amount', 'currency', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('public_reference', 'user__email', 'user__username')
    list_select_related = ('user',)


@admin.register(PaymentReview)
class PaymentReviewAdmin(ReadOnlyModelAdmin):
    list_display = ('submission', 'decision', 'reviewer', 'reviewed_at')
    list_filter = ('decision', 'reviewed_at')
    search_fields = ('submission__transaction_reference', 'submission__order__public_reference')
    list_select_related = ('reviewer', 'submission', 'submission__order')


@admin.register(PremiumAccessPeriod)
class PremiumAccessPeriodAdmin(ReadOnlyModelAdmin):
    list_display = ('order', 'starts_at', 'ends_at', 'created_at')
    list_filter = ('starts_at', 'ends_at')
    search_fields = ('order__public_reference', 'order__user__email')
    list_select_related = ('order', 'order__user')


@admin.register(PreparationSet)
class PreparationSetAdmin(admin.ModelAdmin):
    """Let authorized staff inspect set metadata and remove test sets safely."""

    list_display = (
        'set_number', 'owner', 'company_name', 'job_title', 'role_family',
        'completed_count', 'created_at',
    )
    list_filter = ('role_family', 'seniority', 'created_at')
    search_fields = ('owner__username', 'owner__email', 'company_name', 'job_title')
    list_select_related = ('owner', 'access_period', 'access_period__order')
    date_hierarchy = 'created_at'
    fields = (
        'owner', 'access_period', 'set_number', 'company_name', 'job_title',
        'role_family', 'seniority', 'completed_count', 'created_at', 'updated_at',
    )
    readonly_fields = fields
    ordering = ('-created_at',)

    @admin.display(description='Questions practised')
    def completed_count(self, obj):
        return len(obj.completed_question_ids or [])

    def has_add_permission(self, request):
        """Preparation sets must be created by the learner generation flow."""
        return False
