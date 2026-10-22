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
    checkpoint_preparation_draft,
    claim_preparation_draft,
    create_preparation_draft,
    get_preparation_access,
    get_saved_questions,
    mark_preparation_draft_interrupted,
    mark_question_completed,
    preparation_is_draft,
    save_generated_preparation_set,
    toggle_saved_question,
)


def _rich_answer(direct, blocks, interview_answer, practice, checks=None, mistake='', takeaway=''):
    return {
        'direct_answer': direct,
        'sections': [{'title': 'Worked explanation', 'blocks': blocks}] if blocks else [],
        'interview_ready_answer': interview_answer,
        'interviewer_evaluation': {
            'what_interviewer_checks': checks or ['Question-specific reasoning.'],
            'common_mistake': mistake,
            'key_takeaway': takeaway,
        },
        'practice_activity': practice,
    }


def _answer_block(kind, *, title='', text='', items=None, headers=None, rows=None, code='', language='text'):
    return {
        'type': kind, 'title': title, 'text': text,
        'items': items or [], 'headers': headers or [], 'rows': rows or [],
        'code': code, 'language': language,
    }


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

    def test_checkpointed_draft_survives_failure_and_can_be_completed_in_place(self):
        reference = uuid.uuid4()
        draft = create_preparation_draft(
            self.learner, reference, 'Acme', 'Analyst', 'Analyze sales data.',
            input_fingerprint='draft-fingerprint',
        )
        access = get_preparation_access(self.learner)
        self.assertEqual(access['sets_completed'], 0)
        self.assertEqual(access['drafts_reserved'], 1)
        self.assertEqual(access['sets_remaining'], 1)
        self.assertTrue(claim_preparation_draft(draft.pk))
        self.assertFalse(claim_preparation_draft(draft.pk))
        questions = [{'id': 'r1-q01', 'question': 'How do you validate a sales metric?'}]
        checkpoint_preparation_draft(draft.pk, 1, questions, completed=1, total=60)
        mark_preparation_draft_interrupted(draft.pk, 'Final quality check failed')
        draft.refresh_from_db()

        self.assertTrue(preparation_is_draft(draft))
        self.assertEqual(draft.generated_content['rounds'][0]['questions'], questions)
        self.assertEqual(draft.generated_content['_generation_progress']['completed'], 1)
        self.assertTrue(draft.generated_content['_generation_retry_all'])
        self.assertEqual(draft.generated_content['_generation_fallback_rounds'][0]['questions'], questions)
        self.assertNotIn('resume_text', draft.generated_content)
        self.assertTrue(claim_preparation_draft(draft.pk))

        completed = save_generated_preparation_set(
            self.learner, reference, 'Acme', 'Analyst', 'Analyze sales data.',
            {'analysis': 'Role analysis.', 'questions': self.questions},
            input_fingerprint='draft-fingerprint',
        )
        self.assertEqual(completed.pk, draft.pk)
        self.assertFalse(preparation_is_draft(completed))
        self.assertEqual(PreparationSet.objects.filter(owner=self.learner).count(), 1)

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
    def response(self, output, chat=False):
        result = Mock()
        result.raise_for_status.return_value = None
        if chat:
            result.json.return_value = {
                'choices': [{'message': {'content': json.dumps(output)}}],
                'usage': {'prompt_tokens': 400, 'completion_tokens': 200},
            }
        else:
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
            is_chat = args[0].endswith('/chat/completions')
            dynamic = json.loads(
                kwargs['json']['messages'][1]['content'] if is_chat else kwargs['json']['input']
            )
            dynamic.pop('required_output_schema', None)
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
                    question_number = (counter['question'] - 1) % 60 + 1
                    category = category_sequence[category_start + number]
                    result['questions'].append({
                        'question': f'Task{question_number} evaluation for {category}?',
                        'assessment_focus': f'task{question_number} evaluation',
                        'category': category,
                        'question_type': kind,
                    'answer_content': _rich_answer(
                        'Compare the evidence before choosing a response.', [],
                        'I would compare the relevant evidence, explain the decision, and verify the result.',
                        'Name the evidence you would inspect first.',
                    ),
                        'explanation': 'Assesses role-related reasoning and communication.',
                        'evidence_refs': [
                            next((ref for ref in dynamic['valid_evidence_ids'] if ref.startswith('RES-')), dynamic['valid_evidence_ids'][0])
                            if kind == 'personalized' else dynamic['valid_evidence_ids'][0]
                        ],
                    })
            return self.response(result, chat=is_chat)

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
        self.assertEqual(generated['generation_metrics']['input_tokens'], 6000)
        self.assertEqual(post.call_count, 15)
        for call in post.call_args_list:
            kwargs = call.kwargs
            self.assertEqual(call.args[0], 'https://api.openai.com/v1/responses')
            self.assertEqual(kwargs['headers']['Authorization'], 'Bearer test-key')
            self.assertIs(kwargs['json']['store'], False)
            self.assertEqual(kwargs['json']['model'], 'test-model')
            self.assertEqual(kwargs['json']['text']['format']['type'], 'json_schema')

    @override_settings(INTERVIEW_PREP_AI_PROVIDER='openai', INTERVIEW_PREP_OPENAI_API_KEY='test-key', INTERVIEW_PREP_OPENAI_MODEL='test-model')
    @patch('interview_prep.openai_generator.requests.post')
    def test_second_preparation_may_reuse_core_questions_from_same_jd(self, post):
        self.mock_full_pipeline(post)
        first = generate_preparation(
            'Same resume', 'Same analyst JD', 'Company A', 'Data Analyst',
            role_family='data-analytics', seniority='entry',
        )
        earlier_questions = [
            question
            for question_round in first['rounds']
            for question in question_round['questions']
        ]

        second = generate_preparation(
            'Same resume', 'Same analyst JD', 'Company B', 'Data Analyst',
            role_family='data-analytics', seniority='entry',
            previous_questions=earlier_questions,
        )

        first_text = [question['question'] for row in first['rounds'] for question in row['questions']]
        second_text = [question['question'] for row in second['rounds'] for question in row['questions']]
        self.assertEqual(first_text, second_text)
        self.assertEqual(len(second['rounds']), 2)
        self.assertEqual(post.call_count, 30)

    @override_settings(INTERVIEW_PREP_AI_PROVIDER='groq', INTERVIEW_PREP_GROQ_API_KEY='groq-test-key', INTERVIEW_PREP_GROQ_MODEL='openai/gpt-oss-20b')
    @patch('interview_prep.openai_generator.requests.post')
    def test_groq_uses_compatible_responses_endpoint_without_openai_storage_flag(self, post):
        self.mock_full_pipeline(post)
        result = generate_preparation('resume', 'requirements', '', 'Engineer')
        self.assertEqual(len(result['rounds']), 2)
        self.assertEqual(post.call_count, 15)
        self.assertEqual(post.call_args_list[0].args[0], 'https://api.groq.com/openai/v1/responses')
        self.assertTrue(all(call.args[0] == 'https://api.groq.com/openai/v1/chat/completions' for call in post.call_args_list[1:]))
        for call in post.call_args_list:
            self.assertEqual(call.kwargs['headers']['Authorization'], 'Bearer groq-test-key')
            self.assertNotIn('store', call.kwargs['json'])

    @override_settings(INTERVIEW_PREP_AI_PROVIDER='groq', INTERVIEW_PREP_GROQ_API_KEY='groq-test-key', INTERVIEW_PREP_GROQ_MODEL='openai/gpt-oss-20b')
    @patch('interview_prep.openai_generator.requests.post')
    def test_full_draft_validation_failure_retries_question_batches(self, post):
        self.mock_full_pipeline(post)
        result = generate_preparation(
            'resume', 'requirements', '', 'Engineer',
            resume_content={
                '_generation_retry_all': True,
                'rounds': [
                    {'round_number': 1, 'questions': [{'id': f'r1-q{i:02d}'} for i in range(1, 31)]},
                    {'round_number': 2, 'questions': [{'id': f'r2-q{i:02d}'} for i in range(1, 31)]},
                ],
            },
        )
        self.assertEqual(len(result['rounds']), 2)
        self.assertEqual(post.call_count, 15)

    @override_settings(INTERVIEW_PREP_AI_PROVIDER='openai', INTERVIEW_PREP_OPENAI_API_KEY='')
    def test_missing_api_key_does_not_call_provider(self):
        with patch('interview_prep.openai_generator.requests.post') as post:
            with self.assertRaises(PreparationProviderError):
                generate_preparation('resume', 'job description', 'Acme', 'Engineer')
        post.assert_not_called()

    @override_settings(INTERVIEW_PREP_AI_PROVIDER='openai', INTERVIEW_PREP_OPENAI_API_KEY='test-key', INTERVIEW_PREP_OPENAI_MODEL='test-model')
    @patch('interview_prep.openai_generator.validate_intelligence_output', return_value=['quality check failed'])
    @patch('interview_prep.openai_generator.requests.post')
    def test_final_validation_error_uses_interviewer_language(self, post, _validate):
        self.mock_full_pipeline(post)
        with self.assertRaises(PreparationProviderError) as raised:
            generate_preparation('resume', 'requirements', '', 'Engineer')
        self.assertIn('Your interviewer could not complete the final quality check.', str(raised.exception))
        self.assertNotIn('AI', str(raised.exception))

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

    def test_question_page_shows_saved_answer_and_keeps_practice_actions(self):
        preparation = PreparationSet.objects.create(
            owner=self.learner,
            access_period=PremiumAccessPeriod.objects.get(order__user=self.learner),
            set_number=1,
            company_name='Acme',
            job_title='Data Analyst',
            role_family='data-analytics',
            seniority='entry',
            job_description='Analyze reliable business data.',
            generated_content={'rounds': []},
        )
        preparation.generated_content = {
            'rounds': [{
                'round_number': 1,
                'title': 'Practice round 1',
                'questions': [{
                    'id': 'r1-q1',
                    'category': 'Data quality',
                    'question': 'How would you find missing records?',
                    'answer_content': {'direct_answer': 'Malformed content is ignored.'},
                    'answer_guidance': '**Check the source and target counts.** Compare keys to identify which records are missing.',
                    'explanation': 'Checks data validation and debugging.',
                    'evidence_refs': ['JD-01'],
                }],
            }],
        }
        preparation.save(update_fields=['generated_content'])
        self.client.force_login(self.learner)

        response = self.client.get(reverse('interview_prep:preparation_questions', args=[preparation.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Compare keys to identify which records are missing.')
        self.assertContains(response, 'Save for later')
        self.assertContains(response, 'Mark practised')
        self.assertNotContains(response, 'Option A')
        self.assertNotContains(response, 'I would first clarify')

    def test_representative_structured_answers_render_distinct_formats(self):
        pipeline_answer = _rich_answer(
            'Find the first pipeline stage where the sales total diverges, then verify the cause before changing the transformation.',
            [
                _answer_block('flow', title='Investigation workflow', items=[
                    'Confirm revenue definition and reporting window',
                    'Compare source, staging, and warehouse totals',
                    'Inspect changed joins and date filters',
                    'Reconcile the correction and add a regression check',
                ]),
                _answer_block('example', title='What the difference can tell you', text='If the source still totals ₹10 lakh but staging falls to ₹7 lakh, inspect the transformation between those stages before changing the dashboard.'),
                _answer_block('table', title='Illustrative sales example',
                              headers=['Metric', 'Before update', 'After update'],
                              rows=[['Reported revenue', '₹10 lakh', '₹7 lakh'], ['Difference', '—', '−₹3 lakh']]),
            ],
            'I would compare the metric definition and reporting period first, then trace totals through the pipeline. If revenue fell from ₹10 lakh to ₹7 lakh after a deployment, I would inspect the changed joins, filters, and intermediate totals to locate the first divergence. I would reconcile the correction to source transactions and add a check for future runs.',
            'Name the pipeline stage where the total first changes and the evidence that proves it.',
            takeaway='Locate the first divergence; do not assume the dashboard is the source of the defect.',
        )
        records_answer = _rich_answer(
            'Use stable business keys and event-time checks to detect missing, duplicate, and late records separately.',
            [_answer_block('bullets', title='Checks by failure type', items=[
                'Missing: anti-join expected source keys against loaded target keys.',
                'Duplicates: group by the business key and flag counts greater than one.',
                'Late arrivals: compare event time with ingestion time and the agreed lateness window.',
            ]), _answer_block('steps', title='Turn checks into monitoring', items=[
                'Set an expected count or freshness threshold for each source.',
                'Run checks before publishing the reporting table.',
                'Alert with the affected partition and route it to an owner.',
            ])],
            'I would compare source and target keys to detect missing rows, group by the business key to find duplicates, and monitor the gap between event time and ingestion time for late arrivals. Each check should alert with a threshold that reflects the source and business process.',
            'Write down one query or rule for each of the three failure types.',
            takeaway='Missing, duplicated, and late records need different checks.',
        )
        sql_answer = _rich_answer(
            'Group rows by the reporting dimension, then aggregate the measure at the same grain as the business question.',
            [
                _answer_block('code', title='Illustrative SQL', language='sql', code='''SELECT region, SUM(revenue) AS total_revenue
FROM sales
WHERE order_date >= '2026-01-01' AND order_date < '2026-02-01'
GROUP BY region
ORDER BY total_revenue DESC;
-- <script>alert(1)</script>'''),
                _answer_block('table', title='Example input', headers=['region', 'revenue'], rows=[['West', '120'], ['West', '80'], ['East', '150']]),
                _answer_block('table', title='Expected output', headers=['region', 'total_revenue'], rows=[['West', '200'], ['East', '150']]),
                _answer_block('paragraph', text='GROUP BY creates one result row per region; SUM adds the revenue values within each region.'),
            ],
            'I would group sales by region and sum revenue for a clearly defined reporting period. The query returns West = 200 and East = 150, assuming each row is one valid sale and revenue is already in the reporting currency.',
            'Calculate the two regional totals by hand, then explain why the date range uses an exclusive end date.',
            takeaway='Choose the grouping grain and date window to match the metric definition.',
        )
        priority_answer = _rich_answer(
            'Protect model validity first, address critical data-quality risks next, and time-box feature work according to its expected value and dependencies.',
            [_answer_block('table', title='Prioritization under a short deadline',
                           headers=['Work', 'Decision criterion', 'Near-term action'],
                           rows=[
                               ['Model validation', 'Release risk and decision impact', 'Run a minimum holdout and leakage check before release.'],
                               ['Data quality', 'Severity and affected records', 'Block on defects that invalidate labels or evaluation.'],
                               ['Feature engineering', 'Expected lift and effort', 'Time-box one high-value feature after the checks.'],
                           ]), _answer_block('callout', title='Why this order?', text='A feature improvement is not useful if leakage or incorrect labels make the evaluation untrustworthy.')],
            'I would first protect the validity of the model decision by checking the holdout and leakage. In parallel, I would fix data defects that could invalidate that evaluation. I would defer broad feature work and time-box only a high-value feature whose dependencies are ready, then communicate what remains untested.',
            'Given a two-hour deadline, state what you would do first, what you would defer, and what risk you would report.',
            checks=['Risk-based prioritization', 'Understanding of validation dependencies'],
            mistake='Spending the time on feature work before confirming that the evaluation data is trustworthy.',
            takeaway='Do not optimize a model result until you know the data and evaluation are valid.',
        )
        examples = [
            ('Investigate an unexpected sales metric change', 'Data pipelines', pipeline_answer),
            ('Detect missing, duplicated, or late records', 'Data quality', records_answer),
            ('Explain a SQL aggregation result', 'SQL', sql_answer),
            ('Prioritize data quality, feature engineering, and model validation', 'Machine learning', priority_answer),
        ]
        questions = [{
            'id': f'r1-q{index:02d}', 'question': title, 'category': category,
            'question_type': 'standardized', 'answer_content': answer,
            'explanation': f'Assesses the reasoning needed for {category}.', 'evidence_refs': ['JD-01'],
        } for index, (title, category, answer) in enumerate(examples, start=1)]
        preparation = PreparationSet.objects.create(
            owner=self.learner,
            access_period=PremiumAccessPeriod.objects.get(order__user=self.learner),
            set_number=1,
            company_name='Acme', job_title='Data Analyst', role_family='data-analytics',
            seniority='mid', job_description='Analyze business data.',
            completed_question_ids=['r1-q01'],
            generated_content={'rounds': [{'round_number': 1, 'title': 'Practice round 1', 'questions': questions}]},
        )
        self.client.force_login(self.learner)

        response = self.client.get(reverse('interview_prep:preparation_questions', args=[preparation.pk]))
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        for expected in ('sales total diverges', 'business keys', 'SUM(revenue)', 'time-box only a high-value feature'):
            self.assertContains(response, expected)
        self.assertGreaterEqual(html.count('<table'), 4)
        self.assertIn('<pre><code>', html)
        self.assertIn('ipp-answer-flow', html)
        self.assertIn('ipp-answer-example', html)
        self.assertIn('ipp-answer-list', html)
        self.assertIn('Why this order?', html)
        self.assertIn('Save for later', html)
        self.assertIn('Mark practised', html)
        self.assertIn('1 of 4 practised', html)
        self.assertIn('data-question-jump', html)
        self.assertNotIn('<code><script>', html)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', html)
        self.assertNotContains(response, 'Option A')

    def test_question_page_shows_unavailable_state_without_fabricating_an_answer(self):
        preparation = PreparationSet.objects.create(
            owner=self.learner,
            access_period=PremiumAccessPeriod.objects.get(order__user=self.learner),
            set_number=1,
            company_name='Acme',
            job_title='Data Analyst',
            role_family='data-analytics',
            seniority='entry',
            job_description='Analyze reliable business data.',
            generated_content={'rounds': []},
        )
        preparation.generated_content = {
            'rounds': [{
                'round_number': 1,
                'title': 'Practice round 1',
                'questions': [{
                    'id': 'r1-q1',
                    'category': 'Data quality',
                    'question': 'What checks would detect duplicate records?',
                    'answer_guidance': '',
                    'explanation': 'Checks data validation.',
                    'evidence_refs': ['JD-01'],
                }],
            }],
        }
        preparation.save(update_fields=['generated_content'])
        self.client.force_login(self.learner)

        response = self.client.get(reverse('interview_prep:preparation_questions', args=[preparation.pk]))

        self.assertContains(response, 'Answer unavailable')
        self.assertContains(response, 'detect duplicate records')
        self.assertNotContains(response, 'Option A')
        self.assertNotContains(response, 'I would first clarify')

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
        self.assertNotContains(response, 'AI service')
        self.assertNotContains(response, 'â€™')
        generate.assert_not_called()

    @override_settings(INTERVIEW_PREP_OPENAI_API_KEY='test-key')
    @patch('interview_prep.views.generate_preparation')
    def test_stream_failure_keeps_batch_and_retry_resumes_same_draft(self, generate):
        reference = uuid.uuid4()
        ready_question = {'id': 'r1-q01', 'question': 'How would you reconcile a sales total?'}

        def fail_after_batch(**kwargs):
            kwargs['progress_callback']({
                'phase': 'questions', 'completed': 1, 'total': 60,
                'round_number': 1, 'round_questions': [ready_question],
                'validated_questions': [ready_question],
                'preview_questions': [ready_question['question']],
            })
            raise PreparationProviderError('Temporary provider interruption.')

        recovered_content = {
            'analysis': 'Sales analysis experience.', 'questions': [
                {'id': 'r1-q01', 'question': ready_question['question']},
            ],
        }
        generate.side_effect = fail_after_batch
        self.client.force_login(self.learner)
        form_data = {
            'request_reference': reference,
            'company_name': 'Acme', 'job_title': 'Analyst',
            'role_family': 'data-analytics', 'seniority': 'entry',
            'job_description': 'Analyze business sales.',
            'resume_text': 'Built sales dashboards.',
            'consent_to_ai_provider': 'on',
        }
        first_response = self.client.post(
            reverse('interview_prep:create_preparation'), form_data,
            HTTP_ACCEPT='text/event-stream',
        )
        first_events = b''.join(first_response.streaming_content).decode()
        draft = PreparationSet.objects.get(owner=self.learner)
        self.assertIn('"type": "error"', first_events)
        self.assertIn('"draft_url":', first_events)
        self.assertIn('How would you reconcile a sales total?', first_events, first_events)
        self.assertTrue(preparation_is_draft(draft))
        self.assertEqual(draft.generated_content['rounds'][0]['questions'], [ready_question], first_events)

        form_data['resume_draft_id'] = draft.pk
        generate.side_effect = None
        generate.return_value = recovered_content
        retry_response = self.client.post(reverse('interview_prep:create_preparation'), form_data)
        self.assertEqual(retry_response.status_code, 302)
        self.assertEqual(PreparationSet.objects.filter(owner=self.learner).count(), 1)
        self.assertEqual(generate.call_args.kwargs['resume_content']['rounds'][0]['questions'], [ready_question])

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
    def test_streaming_generation_reports_validated_progress_then_redirects(self, generate):
        generated = {
            'analysis': 'Relevant backend experience.',
            'skill_gaps': [],
            'questions': [{'id': 'q-1', 'category': 'Backend', 'question': 'How would you design this API?'}],
        }

        def generate_with_progress(**kwargs):
            kwargs['progress_callback']({'phase': 'questions', 'completed': 1, 'total': 60, 'message': 'Validated 1 of 60 questions'})
            return generated

        generate.side_effect = generate_with_progress
        reference = uuid.uuid4()
        self.client.force_login(self.learner)
        response = self.client.post(
            reverse('interview_prep:create_preparation'),
            {
                'request_reference': reference,
                'company_name': 'Acme',
                'job_title': 'Engineer',
                'role_family': 'general-software-engineering',
                'seniority': 'entry',
                'job_description': 'Build backend services.',
                'resume_text': 'Built APIs with Django.',
                'consent_to_ai_provider': 'on',
            },
            HTTP_ACCEPT='text/event-stream',
        )

        events = b''.join(response.streaming_content).decode()
        preparation = PreparationSet.objects.get(owner=self.learner)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/event-stream')
        self.assertIn('Validated 1 of 60 questions', events)
        self.assertIn('"type": "complete"', events)
        self.assertIn(reverse('interview_prep:preparation_detail', args=[preparation.pk]), events)
        generate.assert_called_once()

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

