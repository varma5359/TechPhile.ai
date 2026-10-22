import json
import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import (
    PaymentReview,
    PaymentSubmission,
    PremiumAccessPeriod,
    PremiumOrder,
    PreparationSet,
    SavedQuestion,
)
from .openai_generator import PreparationProviderError, generate_preparation
from .services import (
    MONTHLY_PREPARATION_SET_LIMIT,
    PreparationSetLimitReached,
    PremiumPreparationRequired,
    get_preparation_access,
    get_saved_questions,
    mark_question_completed,
    save_generated_preparation_set,
    toggle_saved_question,
)


class PremiumAccessServiceTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.learner = user_model.objects.create_user(
            username='learner',
            email='learner@example.com',
            password='test-password',
        )
        self.other_learner = user_model.objects.create_user(
            username='other',
            email='other@example.com',
            password='test-password',
        )
        self.order = PremiumOrder.objects.create(
            user=self.learner,
            amount=Decimal('49.00'),
            status=PremiumOrder.Status.APPROVED,
        )
        now = timezone.now()
        self.period = PremiumAccessPeriod.objects.create(
            order=self.order,
            starts_at=now - timedelta(minutes=1),
            ends_at=now + timedelta(days=29),
        )
        self.questions = [
            {'id': 'q-1', 'question': 'Describe a challenging project.'},
            {'id': 'q-2', 'question': 'How do you approach debugging?'},
        ]

    def save_set(self, reference=None, company='Acme'):
        return save_generated_preparation_set(
            user=self.learner,
            request_reference=reference or uuid.uuid4(),
            company_name=company,
            job_title='Software Engineer',
            job_description='Build and maintain software systems.',
            generated_content={'questions': self.questions},
        )

    def test_free_account_has_no_premium_set_slots(self):
        access = get_preparation_access(self.other_learner)
        self.assertEqual(access['plan'], 'free')
        self.assertFalse(access['premium_active'])
        self.assertEqual(access['sets_remaining'], 0)
        with self.assertRaises(PremiumPreparationRequired):
            save_generated_preparation_set(
                self.other_learner,
                uuid.uuid4(),
                'Acme',
                'Engineer',
                'A role description.',
                {'questions': self.questions},
            )

    def test_premium_limit_is_two_sets_across_companies_and_retry_is_idempotent(self):
        first_reference = uuid.uuid4()
        first = self.save_set(first_reference, company='Company One')
        retry = self.save_set(first_reference, company='Different Company')
        self.assertEqual(retry.pk, first.pk)
        self.save_set(company='Company Two')

        access = get_preparation_access(self.learner)
        self.assertEqual(access['sets_used'], MONTHLY_PREPARATION_SET_LIMIT)
        self.assertEqual(access['sets_remaining'], 0)
        with self.assertRaises(PreparationSetLimitReached):
            self.save_set(company='Company Three')

    def test_expired_or_rejected_access_does_not_allow_set_creation(self):
        self.period.ends_at = timezone.now() - timedelta(seconds=1)
        self.period.save(update_fields=['ends_at'])
        with self.assertRaises(PremiumPreparationRequired):
            self.save_set()

    def test_generation_requires_complete_questions_with_unique_ids(self):
        with self.assertRaisesMessage(ValidationError, 'Each generated question needs'):
            save_generated_preparation_set(
                self.learner,
                uuid.uuid4(),
                'Acme',
                'Engineer',
                'A role description.',
                {'questions': [{'id': 'q-1', 'question': ' '}]},
            )
        with self.assertRaisesMessage(ValidationError, 'Generated question IDs must be unique'):
            save_generated_preparation_set(
                self.learner,
                uuid.uuid4(),
                'Acme',
                'Engineer',
                'A role description.',
                {'questions': [self.questions[0], self.questions[0]]},
            )

    def test_progress_and_saved_questions_require_set_owner_and_question_membership(self):
        preparation = self.save_set()
        self.assertTrue(toggle_saved_question(self.learner, preparation.pk, 'q-1'))
        self.assertFalse(toggle_saved_question(self.learner, preparation.pk, 'q-1'))
        self.assertEqual(get_saved_questions(self.learner).count(), 0)
        self.assertEqual(mark_question_completed(self.learner, preparation.pk, 'q-2'), 1)
        preparation.refresh_from_db()
        self.assertEqual(preparation.completed_question_ids, ['q-2'])

        with self.assertRaises(PremiumPreparationRequired):
            toggle_saved_question(self.other_learner, preparation.pk, 'q-1')
        with self.assertRaisesMessage(ValidationError, 'not part of this preparation set'):
            mark_question_completed(self.learner, preparation.pk, 'forged-question')

    def test_saved_questions_are_scoped_to_owner_and_active_period(self):
        preparation = self.save_set()
        SavedQuestion.objects.create(
            preparation_set=preparation,
            question_id='q-1',
            question_text='Describe a challenging project.',
        )
        self.assertEqual(get_saved_questions(self.learner).count(), 1)
        self.assertEqual(get_saved_questions(self.other_learner).count(), 0)
        self.period.ends_at = timezone.now() - timedelta(seconds=1)
        self.period.save(update_fields=['ends_at'])
        self.assertEqual(get_saved_questions(self.learner).count(), 0)


class PremiumPaymentWorkflowTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.learner = user_model.objects.create_user(
            username='payer',
            email='payer@example.com',
            password='test-password',
        )
        self.reviewer = user_model.objects.create_user(
            username='reviewer',
            email='reviewer@example.com',
            password='test-password',
            is_staff=True,
        )
        self.reviewer.user_permissions.add(
            Permission.objects.get(
                content_type__app_label='interview_prep',
                codename='approve_payment',
            ),
            Permission.objects.get(
                content_type__app_label='interview_prep',
                codename='view_paymentsubmission',
            ),
        )

    @override_settings(INTERVIEW_PREP_PAYMENTS_ENABLED=False)
    def test_payment_order_creation_is_closed_until_configured(self):
        self.client.force_login(self.learner)
        response = self.client.post(reverse('interview_prep:start_order'))
        self.assertRedirects(response, reverse('interview_prep:monthly_plan'))
        self.assertEqual(PremiumOrder.objects.count(), 0)

    def test_order_and_payment_submission_are_private_to_owner(self):
        order = PremiumOrder.create_monthly(self.learner)
        self.client.force_login(get_user_model().objects.create_user(
            username='intruder', password='test-password',
        ))
        response = self.client.get(reverse(
            'interview_prep:order_detail',
            args=[order.public_reference],
        ))
        self.assertEqual(response.status_code, 404)

    def test_admin_approval_grants_monthly_access_and_records_reviewer(self):
        order = PremiumOrder.objects.create(
            user=self.learner,
            amount=Decimal('49.00'),
            status=PremiumOrder.Status.SUBMITTED,
        )
        submission = PaymentSubmission.objects.create(
            order=order,
            transaction_reference='  abc123456  ',
        )
        self.assertEqual(submission.transaction_reference, 'ABC123456')

        self.client.force_login(self.reviewer)
        response = self.client.post(
            reverse('admin:interview_prep_paymentsubmission_review', args=[submission.pk]),
            {'decision': PaymentReview.Decision.APPROVED, 'notes': 'Verified in merchant account.'},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('admin:interview_prep_paymentsubmission_changelist'))
        order.refresh_from_db()
        self.assertEqual(order.status, PremiumOrder.Status.APPROVED)
        review = PaymentReview.objects.get(submission=submission)
        self.assertEqual(review.reviewer, self.reviewer)
        period = PremiumAccessPeriod.objects.get(order=order)
        self.assertGreater(period.ends_at, period.starts_at)
        self.assertAlmostEqual((period.ends_at - period.starts_at).days, 30, delta=1)

    def test_admin_cannot_approve_own_payment_or_reject_without_reason(self):
        order = PremiumOrder.objects.create(
            user=self.reviewer,
            amount=Decimal('49.00'),
            status=PremiumOrder.Status.SUBMITTED,
        )
        submission = PaymentSubmission.objects.create(
            order=order,
            transaction_reference='self123456',
        )
        self.client.force_login(self.reviewer)
        response = self.client.post(
            reverse('admin:interview_prep_paymentsubmission_review', args=[submission.pk]),
            {'decision': PaymentReview.Decision.APPROVED, 'notes': ''},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This submission cannot be reviewed by your account.')
        self.assertFalse(PaymentReview.objects.filter(submission=submission).exists())

        other_order = PremiumOrder.objects.create(
            user=self.learner,
            amount=Decimal('49.00'),
            status=PremiumOrder.Status.SUBMITTED,
        )
        other_submission = PaymentSubmission.objects.create(
            order=other_order,
            transaction_reference='reject123456',
        )
        response = self.client.post(
            reverse('admin:interview_prep_paymentsubmission_review', args=[other_submission.pk]),
            {'decision': PaymentReview.Decision.REJECTED, 'notes': ''},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Add a reason before rejecting this payment.')
        self.assertFalse(PaymentReview.objects.filter(submission=other_submission).exists())

    def test_staff_without_payment_permission_cannot_review(self):
        staff = get_user_model().objects.create_user(
            username='unprivileged-staff',
            password='test-password',
            is_staff=True,
        )
        order = PremiumOrder.objects.create(
            user=self.learner,
            amount=Decimal('49.00'),
            status=PremiumOrder.Status.SUBMITTED,
        )
        submission = PaymentSubmission.objects.create(
            order=order,
            transaction_reference='noaccess123',
        )
        self.client.force_login(staff)
        response = self.client.get(
            reverse('admin:interview_prep_paymentsubmission_review', args=[submission.pk]),
        )
        self.assertEqual(response.status_code, 403)


class OpenAIGenerationTests(TestCase):
    def response(self, output):
        result = Mock()
        result.raise_for_status.return_value = None
        result.json.return_value = {
            'status': 'completed',
            'output': [{
                'type': 'message',
                'content': [{'type': 'output_text', 'text': json.dumps(output)}],
            }],
            'usage': {'input_tokens': 400, 'output_tokens': 200},
        }
        return result

    def mock_full_pipeline(self, post):
        counter = {'question': 0}

        def respond(*args, **kwargs):
            dynamic = json.loads(kwargs['json']['input'])
            if 'resume_text' in dynamic:
                result = {
                    'analysis': 'The resume shows API delivery experience against the supplied role requirements.',
                    'resume_facts': [{'id': 'resume-a', 'fact': 'Built a Django API.', 'competencies': ['Programming and APIs']}],
                    'jd_requirements': [{'id': 'req-a', 'requirement': 'Build Python APIs.', 'mandatory': True, 'category': 'Programming and APIs'}],
                    'skill_gaps': [{'gap': 'Deployment depth needs review.', 'requirement_ref': 'req-a', 'resume_fact_refs': ['resume-a']}],
                }
            else:
                result = {'questions': []}
                category_counts = dynamic['competency_blueprint']['per_round']['category_counts']
                category_sequence = []
                remaining = dict(category_counts)
                while any(remaining.values()):
                    for category in dynamic['allowed_categories']:
                        if remaining.get(category, 0):
                            category_sequence.append(category)
                            remaining[category] -= 1
                category_start = dynamic['batch_start_index']
                for number, kind in enumerate(dynamic['question_types_in_order']):
                    counter['question'] += 1
                    result['questions'].append({
                        'question': f'Question {counter["question"]}: explain your approach to this role scenario?',
                        'category': category_sequence[category_start + number],
                        'question_type': kind,
                        'answer_guidance': 'Use a relevant example and explain the trade-offs.',
                        'explanation': 'Assesses role-related reasoning and communication.',
                        'evidence_refs': [
                            next((ref for ref in dynamic['valid_evidence_ids'] if ref.startswith('RES-')), dynamic['valid_evidence_ids'][0])
                            if kind == 'personalized' else dynamic['valid_evidence_ids'][0]
                        ],
                    })
            return self.response(result)

        post.side_effect = respond

    @override_settings(INTERVIEW_PREP_AI_PROVIDER='openai', INTERVIEW_PREP_OPENAI_API_KEY='test-key', INTERVIEW_PREP_OPENAI_MODEL='test-model')
    @patch('interview_prep.openai_generator.requests.post')
    def test_openai_pipeline_uses_separate_analysis_and_question_batches(self, post):
        self.mock_full_pipeline(post)
        generated = generate_preparation(
            'Private resume content', 'Role requirements', 'Acme', 'Engineer',
            role_family='general-software-engineering', seniority='entry',
        )

        self.assertEqual(len(generated['rounds']), 2)
        self.assertEqual([len(row['questions']) for row in generated['rounds']], [30, 30])
        self.assertEqual(generated['rounds'][0]['questions'][0]['id'], 'r1-q01')
        self.assertEqual(generated['rounds'][1]['questions'][0]['id'], 'r2-q01')
        self.assertEqual(generated['generation_metrics']['input_tokens'], 3600)
        self.assertEqual(post.call_count, 9)
        for call in post.call_args_list:
            kwargs = call.kwargs
            self.assertEqual(call.args[0], 'https://api.openai.com/v1/responses')
            self.assertEqual(kwargs['headers']['Authorization'], 'Bearer test-key')
            self.assertIs(kwargs['json']['store'], False)
            self.assertEqual(kwargs['json']['model'], 'test-model')
            self.assertEqual(kwargs['json']['text']['format']['type'], 'json_schema')

    @override_settings(INTERVIEW_PREP_AI_PROVIDER='groq', INTERVIEW_PREP_GROQ_API_KEY='groq-test-key', INTERVIEW_PREP_GROQ_MODEL='openai/gpt-oss-20b')
    @patch('interview_prep.openai_generator.requests.post')
    def test_groq_uses_compatible_responses_endpoint_without_openai_storage_flag(self, post):
        self.mock_full_pipeline(post)
        result = generate_preparation('resume', 'requirements', '', 'Engineer')
        self.assertEqual(len(result['rounds']), 2)
        self.assertEqual(post.call_count, 9)
        for call in post.call_args_list:
            self.assertEqual(call.args[0], 'https://api.groq.com/openai/v1/responses')
            self.assertEqual(call.kwargs['headers']['Authorization'], 'Bearer groq-test-key')
            self.assertNotIn('store', call.kwargs['json'])

    @override_settings(INTERVIEW_PREP_AI_PROVIDER='openai', INTERVIEW_PREP_OPENAI_API_KEY='')
    def test_missing_api_key_does_not_call_provider(self):
        with patch('interview_prep.openai_generator.requests.post') as post:
            with self.assertRaises(PreparationProviderError):
                generate_preparation('resume', 'job description', 'Acme', 'Engineer')
        post.assert_not_called()

    def setUp(self):
        user_model = get_user_model()
        self.learner = user_model.objects.create_user(
            username='generator-learner',
            password='test-password',
        )
        order = PremiumOrder.objects.create(
            user=self.learner,
            amount=Decimal('49.00'),
            status=PremiumOrder.Status.APPROVED,
        )
        now = timezone.now()
        PremiumAccessPeriod.objects.create(
            order=order,
            starts_at=now - timedelta(minutes=1),
            ends_at=now + timedelta(days=29),
        )

    @override_settings(INTERVIEW_PREP_OPENAI_API_KEY='test-key')
    @patch('interview_prep.views.generate_preparation')
    def test_generation_requires_explicit_provider_consent(self, generate):
        self.client.force_login(self.learner)
        response = self.client.post(reverse('interview_prep:create_preparation'), {
            'request_reference': uuid.uuid4(),
            'company_name': 'Acme',
            'job_title': 'Engineer',
            'role_family': 'general-software-engineering',
            'seniority': 'entry',
            'job_description': 'Build backend services.',
            'resume_text': 'Resume contents.',
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors['consent_to_ai_provider'])
        generate.assert_not_called()

    @override_settings(INTERVIEW_PREP_OPENAI_API_KEY='test-key')
    @patch('interview_prep.views.generate_preparation')
    def test_generation_persists_results_but_never_persists_resume_text(self, generate):
        generated = {
            'analysis': 'Relevant backend experience.',
            'skill_gaps': ['Cloud deployment'],
            'questions': [{
                'id': f'q-{index}',
                'category': 'Backend',
                'question': f'Question {index}?',
                'answer_guidance': 'Use a real example.',
                'explanation': 'Checks practical experience.',
            } for index in range(8)],
        }
        generate.return_value = generated
        reference = uuid.uuid4()
        self.client.force_login(self.learner)
        response = self.client.post(reverse('interview_prep:create_preparation'), {
            'request_reference': reference,
            'company_name': 'Acme',
            'job_title': 'Engineer',
            'role_family': 'general-software-engineering',
            'seniority': 'entry',
            'job_description': 'Build backend services.',
            'resume_text': 'Unique private resume text.',
            'consent_to_ai_provider': 'on',
        })

        preparation = PreparationSet.objects.get(owner=self.learner)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse(
            'interview_prep:preparation_detail', args=[preparation.pk],
        ))
        self.assertEqual(preparation.generated_content, generated)
        self.assertNotIn('Unique private resume text.', preparation.job_description)
        self.assertEqual(preparation.request_reference, reference)

    @override_settings(INTERVIEW_PREP_OPENAI_API_KEY='test-key')
    @patch('interview_prep.views.generate_preparation')
    def test_identical_input_reuses_completed_preparation_without_another_provider_call(self, generate):
        generate.return_value = {
            'analysis': 'Relevant experience.',
            'skill_gaps': [],
            'questions': [{'id': 'q-1', 'question': 'Explain your API design.'}],
        }
        self.client.force_login(self.learner)
        form_data = {
            'company_name': 'Acme',
            'job_title': 'Engineer',
            'role_family': 'general-software-engineering',
            'seniority': 'entry',
            'job_description': 'Build APIs.',
            'resume_text': 'Built APIs with Django.',
            'consent_to_ai_provider': 'on',
        }
        first = self.client.post(reverse('interview_prep:create_preparation'), {
            **form_data, 'request_reference': uuid.uuid4(),
        })
        second = self.client.post(reverse('interview_prep:create_preparation'), {
            **form_data, 'request_reference': uuid.uuid4(),
        })
        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 302)
        self.assertEqual(PreparationSet.objects.filter(owner=self.learner).count(), 1)
        self.assertEqual(generate.call_count, 1)

    @override_settings(INTERVIEW_PREP_OPENAI_API_KEY='test-key')
    @patch('interview_prep.views.generate_preparation')
    def test_monthly_limit_blocks_provider_call(self, generate):
        from .services import save_generated_preparation_set

        content = {'questions': [{'id': 'q1', 'question': 'A question?'}]}
        for _ in range(2):
            save_generated_preparation_set(
                self.learner,
                uuid.uuid4(),
                'Acme',
                'Engineer',
                'Build software.',
                content,
            )

        self.client.force_login(self.learner)
        response = self.client.post(reverse('interview_prep:create_preparation'), {
            'request_reference': uuid.uuid4(),
            'company_name': 'Third company',
            'job_title': 'Engineer',
            'role_family': 'general-software-engineering',
            'seniority': 'entry',
            'job_description': 'Build software.',
            'resume_text': 'Resume contents.',
            'consent_to_ai_provider': 'on',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'used both preparation sets')
        generate.assert_not_called()

