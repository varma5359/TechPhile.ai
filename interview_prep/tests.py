import json
import uuid
from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Permission
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
from .forms import PreparationRequestForm
from .openai_generator import PreparationProviderError, generate_preparation
from .role_profiles import get_role_profile
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
    update_preparation_draft_target,
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


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
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
        self.assertEqual(draft.generated_content['_generation_progress']['completed'], 0)
        self.assertEqual(draft.generated_content['_generation_state'], 'temporarily_unavailable')
        self.assertEqual(draft.generated_content['_question_target'], 45)
        self.assertNotIn('_generation_retry_all', draft.generated_content)
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

    def test_question_target_defaults_to_45_and_is_validated_and_saved_on_draft(self):
        self.assertEqual(PreparationRequestForm().fields['question_target'].initial, 45)
        form = PreparationRequestForm({'question_target': 29})
        self.assertFalse(form.is_valid())
        self.assertIn('question_target', form.errors)

        draft = create_preparation_draft(
            self.learner, uuid.uuid4(), 'Acme', 'Analyst', 'Analyze sales data.',
            target_question_count=45,
        )
        draft = update_preparation_draft_target(draft.pk, 40)
        self.assertEqual(draft.generated_content['_question_target'], 40)
        self.assertEqual(draft.generated_content['_generation_progress'], {'completed': 0, 'total': 40})

    def test_expired_access_does_not_allow_set_creation(self):
        self.period.ends_at = timezone.now() - timedelta(seconds=1)
        self.period.save(update_fields=['ends_at'])
        with self.assertRaises(PremiumPreparationRequired):
            self.save_set()

    def test_rejected_order_does_not_grant_access_or_allow_set_creation(self):
        self.order.status = PremiumOrder.Status.REJECTED
        self.order.save(update_fields=['status'])

        access = get_preparation_access(self.learner)
        self.assertFalse(access['premium_active'])
        self.assertEqual(access['sets_remaining'], 0)
        with self.assertRaises(PremiumPreparationRequired):
            self.save_set()
        with self.assertRaises(PremiumPreparationRequired):
            create_preparation_draft(
                self.learner, uuid.uuid4(), 'Acme', 'Analyst', 'Analyze sales data.',
            )

    def test_anonymous_user_cannot_create_draft_through_service_or_view(self):
        with self.assertRaises(PremiumPreparationRequired):
            create_preparation_draft(
                AnonymousUser(), uuid.uuid4(), 'Acme', 'Analyst', 'Analyze sales data.',
            )

        response = self.client.post(reverse('interview_prep:create_preparation'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse('login')))
        self.assertEqual(PreparationSet.objects.count(), 0)

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

    def test_round_based_assignment_rejects_fewer_than_30_valid_unique_questions(self):
        def content_with_count(count):
            questions = [{
                'id': f'r1-q{index:02d}',
                'question': f'How would you verify result {index}?',
                'category': 'Data quality',
                'question_type': 'standardized',
                'question_kind': 'scenario',
                'coding_solution': '',
                'answer_content': {
                    'direct_answer': 'Check the source and compare the result.',
                    'sections': [],
                    'interview_ready_answer': 'I would check the source and compare the result.',
                    'interviewer_evaluation': {
                        'what_interviewer_checks': ['Practical reasoning.'],
                        'common_mistake': '', 'key_takeaway': '',
                    },
                    'practice_activity': '',
                },
                'explanation': 'Assesses practical reasoning.',
                'evidence_refs': ['JD-01'],
            } for index in range(1, count + 1)]
            return {
                'analysis': 'Role fit reviewed.', 'skill_gaps': [],
                'rounds': [{'round_number': 1, 'title': 'Practice round 1', 'questions': questions}],
            }

        with self.assertRaisesMessage(ValidationError, 'valid, unique questions'):
            save_generated_preparation_set(
                self.learner, uuid.uuid4(), 'Acme', 'Analyst', 'Analyze data.',
                content_with_count(29),
            )

    def test_round_based_assignment_requires_solution_for_coding_question(self):
        content = self._valid_round_content_for_count(30)
        content['rounds'][0]['questions'][0].update({
            'question': 'Write a SQL query to select active learners.',
            'question_kind': 'coding',
        })
        with self.assertRaisesMessage(ValidationError, 'valid, unique questions'):
            save_generated_preparation_set(
                self.learner, uuid.uuid4(), 'Acme', 'Analyst', 'Analyze data.', content,
            )

    def test_round_based_assignment_accepts_60_and_rejects_more_than_60_valid_questions(self):
        complete = self._valid_round_content_for_count(60)
        saved = save_generated_preparation_set(
            self.learner, uuid.uuid4(), 'Acme', 'Analyst', 'Analyze data.', complete,
        )
        self.assertEqual(sum(len(row['questions']) for row in saved.generated_content['rounds']), 60)

        with self.assertRaisesMessage(ValidationError, '30 to 60 valid, unique questions'):
            save_generated_preparation_set(
                self.learner, uuid.uuid4(), 'Acme', 'Analyst', 'Analyze data.',
                self._valid_round_content_for_count(61),
            )

    def _valid_round_content_for_count(self, count):
        rounds = []
        for round_number, start in enumerate(range(1, count + 1, 30), start=1):
            questions = [{
                'id': f'r{round_number}-q{index - start + 1:02d}',
                'question': f'How would you verify result {index}?',
                'category': 'Data quality',
                'question_type': 'standardized',
                'question_kind': 'scenario',
                'coding_solution': '',
                'answer_content': {
                    'direct_answer': 'Check the source and compare the result.',
                    'sections': [],
                    'interview_ready_answer': 'I would check the source and compare the result.',
                    'interviewer_evaluation': {
                        'what_interviewer_checks': ['Practical reasoning.'],
                        'common_mistake': '', 'key_takeaway': '',
                    },
                    'practice_activity': '',
                },
                'explanation': 'Assesses practical reasoning.',
                'evidence_refs': ['JD-01'],
            } for index in range(start, min(start + 30, count + 1))]
            rounds.append({
                'round_number': round_number,
                'title': f'Practice round {round_number}',
                'questions': questions,
            })
        return {
            'analysis': 'Role fit reviewed.', 'skill_gaps': [],
            'rounds': rounds,
        }

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


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
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


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
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
        case_contexts = [
            'a late supplier file changes the monthly totals',
            'two departments report different customer counts',
            'a product owner changes the success measure mid-project',
            'an export drops several records after a schema update',
            'a stakeholder disputes the figures in a quarterly review',
            'a scheduled report arrives after its decision deadline',
            'a new feature increases requests to an existing endpoint',
            'a test passes locally but fails in continuous integration',
            'a teammate proposes a faster approach with higher maintenance cost',
            'a dashboard filter hides an important segment of users',
            'an access request includes more permissions than the task needs',
            'a data source changes its date and currency formats',
            'a release is blocked by an intermittent validation failure',
            'a business team needs an explanation before approving a decision',
            'a second system reports a conflicting status for the same order',
            'a planned dependency is unavailable on the delivery date',
            'a query becomes slower as historical records accumulate',
            'a customer reports a result that cannot be reproduced',
            'a review finds that an assumption was never verified',
            'a report must distinguish correlation from a causal explanation',
            'a teammate asks to skip a check to meet a short deadline',
            'an upstream service returns incomplete but valid responses',
            'a metric definition differs between two team documents',
            'a new requirement conflicts with a previously approved design',
            'a small sample gives a different result from the full population',
            'a code change affects an unrelated workflow',
            'a review identifies duplicate records with different identifiers',
            'an incident timeline contains gaps in the available evidence',
            'a user asks for a conclusion before the data is checked',
            'a proposed fix improves one measure but harms another',
            'a privacy review limits which fields can be used',
            'a migrated record no longer matches its source history',
            'a project handoff omits the reason for a key decision',
            'an experiment has uneven participation across groups',
            'an API client retries a request after a timeout',
            'a validation rule rejects a previously accepted input',
            'a stakeholder changes the priority after work has started',
            'a weekly trend shifts after the reporting window changes',
            'a teammate finds a defect during the final review',
            'an alert fires but the underlying service remains available',
            'an unfamiliar dataset has unclear ownership and definitions',
            'a deployment plan has no verified recovery step',
            'two candidate solutions meet the requirement with different trade-offs',
            'a source refresh completes but contains stale values',
            'a user needs an accessible alternative to a visual report',
            'a new constraint changes the safest implementation path',
            'a test dataset omits a boundary condition',
            'an estimate must be updated after a dependency slips',
            'a repeated request creates more than one transaction',
            'a team disagrees about which evidence supports a conclusion',
            'a logging change exposes information that should stay private',
            'a dashboard owner asks to compare incompatible time periods',
            'a code review finds a workaround without an explanatory test',
            'a batch job finishes successfully with fewer rows than expected',
            'a new user group interprets an existing label differently',
            'a specification leaves the expected error behavior unclear',
            'a model output changes after the input distribution shifts',
            'a meeting ends without an owner for the next action',
            'a reconciliation process reports a small unexplained difference',
            'a deadline requires choosing which checks must happen first',
            'a proposed change needs evidence before it can be approved',
        ]

        def respond(*args, **kwargs):
            is_chat = args[0].endswith('/chat/completions')
            dynamic = json.loads(
                kwargs['json']['messages'][1]['content'] if is_chat else kwargs['json']['input']
            )
            dynamic.pop('required_output_schema', None)
            if 'resume_text' in dynamic:
                result = {
                    'analysis': 'The resume shows API delivery experience against the supplied role requirements.',
                    'resume_facts': [{'id': 'resume-a', 'fact': 'Built a Django API.', 'fact_type': 'experience', 'competencies': ['Programming and APIs']}],
                    'jd_requirements': [{'id': 'req-a', 'requirement': 'Build Python APIs.', 'mandatory': True, 'category': 'Programming and APIs'}],
                    'skill_gaps': [{'gap': 'Deployment depth needs review.', 'requirement_ref': 'req-a', 'resume_fact_refs': ['resume-a']}],
                    'career_gaps': [], 'recommended_seniority': 'entry',
                    'seniority_rationale': 'The resume shows project level evidence and no independent employment history.',
                    'uncertain_information': ['The dates for the API project are not clear.'],
                }
            else:
                result = {'questions': []}
                round_number = dynamic.get('current_round', 1)
                category_sequence = dynamic['competency_blueprint']['round_allocations'][round_number - 1]['category_sequence']
                category_start = dynamic['batch_start_index']
                for number, kind in enumerate(dynamic['question_types_in_order']):
                    counter['question'] += 1
                    question_number = dynamic['question_slots'][number]['question_number']
                    category = category_sequence[category_start + number]
                    slot = dynamic['question_slots'][number]
                    angle = slot.get('assessment_angle', f'case {question_number}')
                    coverage_target = slot.get('coverage_target', category)
                    absolute_question_number = category_start + number + 1
                    context_index = ((round_number - 1) * 30 + absolute_question_number - 1) % len(case_contexts)
                    case_context = case_contexts[context_index]
                    question_kind = dynamic['question_slots'][number].get('question_kind') or 'scenario'
                    exercise_skill = next((
                        skill for skill in ('JavaScript', 'TypeScript', 'Python', 'Java', 'SQL', 'C++', 'C#')
                        if skill.casefold() in str(slot.get('interview_focus', '')).casefold()
                    ), 'Python')
                    evidence = slot.get('resume_evidence') or {}
                    evidence_term = str(evidence.get('fact', '')).split()[-1].strip('.,;:') if evidence.get('fact') else ''
                    question_text = (
                        f'Write a {exercise_skill} task to {angle} when {case_context}?'
                        if question_kind in {'coding', 'sql'} and kind == 'standardized'
                        else f'Using your {evidence_term} example, implement a {exercise_skill} task for {case_context}.'
                        if question_kind in {'coding', 'sql'}
                        else
                        f'Using your {evidence_term} example, how would you {angle} when {case_context}?'
                        if kind == 'personalized' and evidence_term
                        else f'How would you {angle} when {case_context}?'
                    )
                    exercise_prompt = {
                        'title': f'{exercise_skill} practical exercise',
                        'language': exercise_skill,
                        'difficulty': dynamic['seniority'].title(),
                        'problem_statement': f'Complete a bounded {exercise_skill} task for the supplied scenario.',
                        'function_signature': '```sql\n-- Write your query here\n```' if question_kind == 'sql' else f'```{exercise_skill.casefold()}\n// Write your solution here\n```',
                        'example_input': '```text\n[]\n```',
                        'expected_output': '```text\n[]\n```',
                        'explanation': 'Return only the requested result and handle the empty input.',
                        'constraints': 'An empty input returns an empty result.',
                        'additional_requirements': '',
                    } if question_kind in {'coding', 'sql'} else {
                        key: '' for key in ('title', 'language', 'difficulty', 'problem_statement', 'function_signature', 'example_input', 'expected_output', 'explanation', 'constraints', 'additional_requirements')
                    }
                    result['questions'].append({
                        'question': question_text,
                        'assessment_focus': f'{coverage_target}: {case_context}',
                        'category': category,
                        'question_type': kind,
                        'question_kind': question_kind,
                        'coding_solution': ('```sql\nSELECT 1;\n```' if question_kind == 'sql' else f'```{exercise_skill.casefold()}\nreturn [];\n```') if question_kind in {'coding', 'sql'} else '',
                        'coding_prompt': exercise_prompt,
                    'answer_content': _rich_answer(
                        'Compare the evidence before choosing a response.', [],
                        'I would compare the relevant evidence, explain the decision, and verify the result.',
                        'Name the evidence you would inspect first.',
                    ),
                        'explanation': 'Assesses role-related reasoning and communication.',
                        'evidence_refs': [
                            evidence.get('id') or next((ref for ref in dynamic['valid_evidence_ids'] if ref.startswith('RES-')), dynamic['valid_evidence_ids'][0])
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

        self.assertEqual([len(row['questions']) for row in generated['rounds']], [30])
        self.assertEqual(generated['rounds'][0]['questions'][0]['id'], 'r1-q01')
        self.assertEqual(sum(len(row['questions']) for row in generated['rounds']), 30)
        self.assertEqual(generated['generation_metrics']['input_tokens'], 3200)
        self.assertEqual(post.call_count, 8)
        for call in post.call_args_list:
            kwargs = call.kwargs
            self.assertEqual(call.args[0], 'https://api.openai.com/v1/responses')
            self.assertEqual(kwargs['headers']['Authorization'], 'Bearer test-key')
            self.assertIs(kwargs['json']['store'], False)
            self.assertEqual(kwargs['json']['model'], 'test-model')
            self.assertEqual(kwargs['json']['text']['format']['type'], 'json_schema')

    @override_settings(INTERVIEW_PREP_AI_PROVIDER='openai', INTERVIEW_PREP_OPENAI_API_KEY='test-key', INTERVIEW_PREP_OPENAI_MODEL='test-model')
    @patch('interview_prep.openai_generator.requests.post')
    def test_unresolved_semantic_duplicate_fails_after_batch_and_single_question_retries(self, post):
        self.mock_full_pipeline(post)
        normal_response = post.side_effect

        def respond(*args, **kwargs):
            is_chat = args[0].endswith('/chat/completions')
            dynamic = json.loads(
                kwargs['json']['messages'][1]['content'] if is_chat else kwargs['json']['input']
            )
            dynamic.pop('required_output_schema', None)
            if 'resume_text' in dynamic:
                return normal_response(*args, **kwargs)
            duplicate_pair = {
                1: ('How would you diagnose a revenue decline after a dashboard update?', 'diagnose revenue decline after update'),
                2: ('What would you investigate when sales fall following a reporting change?', 'diagnose revenue decline after update'),
            }
            distinct_questions = {
                3: ('Which check would catch a missing customer identifier before import?', 'check missing customer identifier'),
                4: ('How would you explain an unfamiliar result to a nontechnical teammate?', 'explain unfamiliar result to teammate'),
                5: ('What test would confirm a saved change still behaves as expected?', 'test saved change behavior'),
            }
            questions = []
            for slot in dynamic['question_slots']:
                number = slot['question_number']
                text, focus = duplicate_pair.get(number, distinct_questions.get(
                    number, (f'How would you handle task {number} in this role?', f'handle distinct task {number}'),
                ))
                question_kind = slot.get('question_kind') or 'scenario'
                is_coding = question_kind in {'coding', 'sql'}
                language = 'SQL' if question_kind == 'sql' else 'Python'
                coding_prompt = {
                    'title': f'{language} revenue analysis exercise',
                    'language': language,
                    'difficulty': 'Entry',
                    'problem_statement': 'Analyze the supplied sales records and return the requested result.',
                    'example_input': 'records = []',
                    'expected_output': '[]',
                    'explanation': 'Return a clear result for the supplied records.',
                } if is_coding else {}
                questions.append({
                    'question': text,
                    'assessment_focus': focus,
                    'category': slot['category'],
                    'question_type': slot['question_type'],
                    'question_kind': question_kind,
                    'coding_solution': (
                        '```sql\nSELECT 1;\n```' if question_kind == 'sql'
                        else '```python\nreturn [];\n```' if question_kind == 'coding'
                        else ''
                    ),
                    'coding_prompt': coding_prompt,
                    'answer_content': _rich_answer(
                        'Check the relevant evidence first.', [],
                        'I would check the relevant evidence and explain my reasoning.',
                        'Name the evidence you would inspect first.',
                    ),
                    'explanation': 'Assesses a role-related decision.',
                    'evidence_refs': [dynamic['valid_evidence_ids'][0]],
                })
            return self.response({'questions': questions}, chat=is_chat)

        post.side_effect = respond
        with self.assertRaises(PreparationProviderError) as raised:
            generate_preparation(
                'Resume with API experience.', 'Build Python APIs.', 'Acme', 'Engineer',
                role_family='general-software-engineering', seniority='entry',
            )
        self.assertIn('too similar', str(raised.exception))
        # Extraction + initial batch + three batch retries + two focused recoveries.
        self.assertEqual(post.call_count, 7)

    @override_settings(INTERVIEW_PREP_AI_PROVIDER='openai', INTERVIEW_PREP_OPENAI_API_KEY='test-key', INTERVIEW_PREP_OPENAI_MODEL='test-model')
    @patch('interview_prep.openai_generator.requests.post')
    def test_selected_targets_30_45_and_60_control_round_sizes(self, post):
        for target in (30, 45, 60):
            with self.subTest(target=target):
                self.mock_full_pipeline(post)
                generated = generate_preparation(
                    'Resume with API experience.', 'Build Python APIs.', 'Acme', 'Engineer',
                    role_family='general-software-engineering', seniority='entry',
                    target_question_count=target,
                )
                self.assertEqual(generated['_question_target'], target)
                self.assertEqual(generated['_generation_state'], 'complete')
                self.assertEqual([len(row['questions']) for row in generated['rounds']],
                                 [min(30, target - start) for start in range(0, target, 30)])
                self.assertEqual(generated['_generation_progress'], {'completed': target, 'total': target})

    @override_settings(INTERVIEW_PREP_AI_PROVIDER='openai', INTERVIEW_PREP_OPENAI_API_KEY='test-key', INTERVIEW_PREP_OPENAI_MODEL='test-model')
    @patch('interview_prep.openai_generator.requests.post')
    def test_target_40_continuation_generates_only_missing_questions_and_keeps_legacy_fallback(self, post):
        self.mock_full_pipeline(post)
        categories = get_role_profile('data-analytics')['categories']
        checkpoint_topics = [
            'input validation', 'API status codes', 'database transactions', 'request parsing',
            'test isolation', 'error messages', 'SQL joins', 'Git history', 'object methods',
            'JSON serialization', 'form validation', 'HTTP authentication', 'query filtering',
            'unit test boundaries', 'logging levels', 'data types', 'API pagination',
            'database indexes', 'exception handling', 'code review', 'role permissions',
            'request timeouts', 'ORM relationships', 'input sanitization',
        ]
        checkpoint_question_texts = [
            'How would you reject malformed fields while giving a user useful validation feedback?',
            'What response should an endpoint return when the requested record does not exist?',
            'When should two related database updates be committed in one transaction?',
            'Which risks would you check before parsing an uploaded request body?',
            'How can a test avoid depending on records created by another test?',
            'What should an API error message reveal, and what should it keep private?',
            'When would an inner join incorrectly remove rows from a business report?',
            'How would you find which change introduced a failing behavior in a branch?',
            'Why can changing a shared object inside a method surprise its caller?',
            'How do you handle an optional field when decoding a JSON payload?',
            'What boundary cases should a form validate before saving a record?',
            'How would you check that an authenticated endpoint enforces permissions?',
            'Which query filters would you apply before returning a large result set?',
            'What makes a unit test too dependent on implementation details?',
            'Which log fields help diagnose a failure without exposing private values?',
            'How should a parser handle an unexpected value without hiding the error?',
            'What would you change to let a client navigate a long API result set?',
            'How can an index help a lookup, and what cost does it add to writes?',
            'When should an exception be handled locally instead of passed upward?',
            'What evidence would you include in a code review for a risky change?',
            'How do role checks differ from checking whether a user is signed in?',
            'How should a client respond when a request times out but may have completed?',
            'What problem does an ORM relationship solve between two stored records?',
            'How would you prevent untrusted input from changing the meaning of a query?',
        ]
        saved_questions = []
        for index in range(24):
            kind = 'standardized' if index < 21 else 'personalized'
            saved_questions.append({
                'id': f'r1-q{index + 1:02d}',
                'question': checkpoint_question_texts[index],
                'assessment_focus': f'check {checkpoint_topics[index]}',
                'category': categories[index % len(categories)],
                'question_type': kind,
                'question_kind': 'scenario',
                'coding_solution': '',
                'answer_content': _rich_answer(
                    'Check the evidence first.', [], 'I would check the relevant evidence and explain my reasoning.',
                    'Name the evidence you would check.',
                ),
                'explanation': 'Assesses a distinct review task.',
                'evidence_refs': ['RES-01'] if kind == 'personalized' else ['JD-01'],
            })
        saved_round = {'round_number': 1, 'title': 'Practice round 1', 'questions': saved_questions}
        extraction = {
            'analysis': 'The confirmed profile supports the target role.',
            'resume_facts': [{'id': 'RES-01', 'fact': 'Built a Django API.', 'fact_type': 'experience', 'competencies': ['Programming and APIs']}],
            'jd_requirements': [{'id': 'JD-01', 'requirement': 'Build reliable reports.', 'mandatory': True,
                                 'category': 'Role fundamentals', 'resume_fact_refs': [],
                                 'match_level': 'not_evidenced', 'match_rationale': 'Not shown.',
                                 'suggestion': 'Add a truthful example.'}],
            'skill_gaps': [], 'career_gaps': [], 'recommended_seniority': 'entry',
            'seniority_rationale': 'Foundational evidence.', 'uncertain_information': [],
        }
        progress = []
        generated = generate_preparation(
            'Saved profile summary.', 'Analyze reliable business data.', '', 'Data Analyst',
            role_family='data-analytics', seniority='entry',
            confirmed_extraction=extraction,
            target_question_count=40,
            resume_content={
                '_question_target': 40,
                '_generation_retry_all': True,
                '_generation_fallback_rounds': [saved_round],
                'rounds': [],
            },
            progress_callback=progress.append,
        )
        self.assertEqual([len(row['questions']) for row in generated['rounds']], [30, 10])
        self.assertEqual(generated['_generation_progress'], {'completed': 40, 'total': 40})
        self.assertEqual([row['question'] for row in generated['rounds'][0]['questions'][:24]],
                         [row['question'] for row in saved_questions])
        recovered_questions = generated['rounds'][0]['questions'][:24]
        self.assertEqual([row['id'] for row in recovered_questions], [row['id'] for row in saved_questions])
        self.assertEqual([row['answer_content'] for row in recovered_questions],
                         [row['answer_content'] for row in saved_questions])
        generated_new = sum(len(row['questions']) for row in generated['rounds']) - 24
        self.assertEqual(generated_new, 16)

    @override_settings(INTERVIEW_PREP_AI_PROVIDER='openai', INTERVIEW_PREP_OPENAI_API_KEY='test-key', INTERVIEW_PREP_OPENAI_MODEL='test-model')
    @patch('interview_prep.openai_generator.research_job_market', return_value={'status': 'not_performed', 'sources': []})
    @patch('interview_prep.openai_generator.requests.post')
    def test_semantic_duplicates_in_a_recovered_checkpoint_block_completion(self, post, _research):
        profile = get_role_profile('general-software-engineering')
        topics = [
            'input validation', 'API status codes', 'database transactions', 'request parsing',
            'test isolation', 'error messages', 'SQL joins', 'Git history', 'object methods',
            'JSON serialization', 'form validation', 'HTTP authentication', 'query filtering',
            'unit test boundaries', 'logging levels', 'data types', 'API pagination',
            'database indexes', 'exception handling', 'code review', 'role permissions',
            'request timeouts', 'ORM relationships', 'input sanitization', 'test fixtures',
            'version control branches', 'response validation', 'deployment configuration',
        ]
        questions = []
        for index in range(30):
            if index == 0:
                text = 'How would you diagnose a revenue decline after a dashboard update?'
                focus = 'diagnose revenue decline after update'
            elif index == 1:
                text = 'What would you investigate when sales fall following a reporting change?'
                focus = 'diagnose revenue decline after update'
            else:
                topic = topics[index - 2]
                text = f'How would you check {topic} before sharing findings?'
                focus = f'check {topic}'
            kind = 'standardized' if index < 21 else 'personalized'
            questions.append({
                'id': f'r1-q{index + 1:02d}',
                'question': text,
                'assessment_focus': focus,
                'category': profile['categories'][index % len(profile['categories'])],
                'question_type': kind,
                'question_kind': 'scenario',
                'coding_solution': '',
                'answer_content': _rich_answer(
                    'Check the relevant evidence first.', [],
                    'I would check the relevant evidence and explain my reasoning.',
                    'Name the evidence you would inspect first.',
                ),
                'explanation': 'Assesses a practical role-related decision.',
                'evidence_refs': ['JD-01'] if kind == 'standardized' else ['RES-01'],
            })
        extraction = {
            'analysis': 'The confirmed profile supports the role.',
            'resume_facts': [{'id': 'RES-01', 'fact': 'Built a Django API.', 'fact_type': 'experience', 'competencies': ['Programming and APIs']}],
            'jd_requirements': [{'id': 'JD-01', 'requirement': 'Build reliable APIs.', 'mandatory': True,
                                 'category': 'Programming and APIs', 'resume_fact_refs': [],
                                 'match_level': 'not_evidenced', 'match_rationale': 'Not shown.',
                                 'suggestion': 'Add a truthful example.'}],
            'skill_gaps': [], 'career_gaps': [], 'recommended_seniority': 'entry',
            'seniority_rationale': 'Foundational evidence.', 'uncertain_information': [],
        }
        checkpoint = {
            '_question_target': 30,
            'rounds': [{'round_number': 1, 'title': 'Practice round 1', 'questions': questions}],
        }
        with self.assertRaises(PreparationProviderError) as raised:
            generate_preparation(
                'Confirmed profile.', 'Build reliable APIs.', '', 'Software Developer',
                role_family='general-software-engineering', seniority='entry',
                confirmed_extraction=extraction, target_question_count=30,
                resume_content=checkpoint,
            )
        self.assertIn('too similar', str(raised.exception))
        self.assertEqual(checkpoint['rounds'][0]['questions'], questions)
        self.assertEqual([row['id'] for row in checkpoint['rounds'][0]['questions']],
                         [f'r1-q{index + 1:02d}' for index in range(30)])
        post.assert_not_called()

    @override_settings(INTERVIEW_PREP_AI_PROVIDER='openai', INTERVIEW_PREP_OPENAI_API_KEY='test-key', INTERVIEW_PREP_OPENAI_MODEL='test-model')
    @patch('interview_prep.openai_generator.requests.post')
    def test_confirmed_profile_skips_a_second_resume_extraction(self, post):
        self.mock_full_pipeline(post)
        confirmed_extraction = {
            'analysis': 'The candidate lists Python skills.',
            'resume_facts': [{
                'id': 'RES-01', 'fact': 'Python', 'fact_type': 'skill',
                'competencies': ['Programming and APIs'],
            }],
            'jd_requirements': [{
                'id': 'JD-01', 'requirement': 'Build Python APIs.', 'mandatory': True,
                'category': 'Programming and APIs', 'resume_fact_refs': ['RES-01'],
                'match_level': 'strong', 'match_rationale': 'Python appears in the confirmed profile.',
                'suggestion': 'Give a specific Python example.',
            }],
            'skill_gaps': [], 'career_gaps': [],
            'recommended_seniority': 'entry',
            'seniority_rationale': 'The profile shows foundational evidence.',
            'uncertain_information': [],
        }
        generated = generate_preparation(
            'Skills: Python', 'Build Python APIs.', 'Acme', 'Python Developer',
            role_family='general-software-engineering', seniority='entry',
            confirmed_extraction=confirmed_extraction,
        )
        self.assertEqual(generated['generation_metrics']['api_calls'], post.call_count)
        self.assertLess(post.call_count, 8)
        self.assertEqual(sum(len(row['questions']) for row in generated['rounds']), 30)

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
        self.assertEqual(len(second['rounds']), 1)
        # Targeted semantic-overlap retries can add bounded replacement calls.
        self.assertGreaterEqual(post.call_count, 16)
        self.assertLessEqual(post.call_count, 40)

    @override_settings(INTERVIEW_PREP_AI_PROVIDER='groq', INTERVIEW_PREP_GROQ_API_KEY='groq-test-key', INTERVIEW_PREP_GROQ_MODEL='openai/gpt-oss-20b')
    @patch('interview_prep.openai_generator.requests.post')
    def test_groq_uses_compatible_responses_endpoint_without_openai_storage_flag(self, post):
        self.mock_full_pipeline(post)
        result = generate_preparation('resume', 'requirements', '', 'Engineer')
        self.assertEqual(len(result['rounds']), 1)
        self.assertEqual(post.call_count, 8)
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
        self.assertEqual(len(result['rounds']), 1)
        self.assertEqual(post.call_count, 8)

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

    def test_unmapped_jd_requirement_is_visible_on_preparation_detail(self):
        preparation = PreparationSet.objects.create(
            owner=self.learner,
            access_period=PremiumAccessPeriod.objects.get(order__user=self.learner),
            set_number=1,
            company_name='Acme',
            job_title='Data Analyst',
            role_family='data-analytics',
            seniority='entry',
            job_description='Analyze reliable business data.',
            generated_content={
                'requirements': [{
                    'id': 'JD-UNMAPPED',
                    'requirement': 'Own lunar habitat operations.',
                    'source_category': 'Unlisted category',
                    'category': 'Role fundamentals',
                    'mapping_status': 'unmapped',
                    'mandatory': True,
                    'match_level': 'strong',
                    'match_rationale': 'The resume contains a related phrase.',
                    'suggestion': 'Review the requirement.',
                }],
                'jd_match': {'score': 0, 'counts': {'strong': 0, 'partial': 0, 'not_evidenced': 1}},
                'rounds': [],
            },
        )
        self.client.force_login(self.learner)
        response = self.client.get(reverse('interview_prep:preparation_detail', args=[preparation.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Role competency mapping needs review')
        self.assertContains(response, 'does not receive resume coverage credit')

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

    def test_structured_coding_question_renders_sections_safely_without_empty_headings(self):
        preparation = PreparationSet.objects.create(
            owner=self.learner,
            access_period=PremiumAccessPeriod.objects.get(order__user=self.learner),
            set_number=1, company_name='Acme', job_title='JavaScript Developer',
            role_family='general-software-engineering', seniority='entry',
            job_description='Build JavaScript features.',
            generated_content={'rounds': [{
                'round_number': 1, 'title': 'Practice round 1', 'questions': [{
                    'id': 'r1-q01', 'category': 'Programming and APIs',
                    'question': 'Write a function that selects users with more than two posts.',
                    'question_kind': 'coding',
                    'coding_solution': '```javascript\nreturn users.filter(user => user.posts.length > 2).map(({id, name}) => ({id, name}));\n```',
                    'coding_prompt': {
                        'title': 'Get Users With More Than Two Posts',
                        'language': 'JavaScript', 'difficulty': 'Entry',
                        'problem_statement': 'Return users with more than two posts. <script>alert(1)</script>',
                        'function_signature': '```javascript\nfunction getUsersWithMultiplePosts(users) {}\n```',
                        'example_input': '```javascript\n[]\n```',
                        'expected_output': '```javascript\n[]\n```',
                        'explanation': 'The empty list returns an empty list.',
                        'constraints': '', 'additional_requirements': '',
                    },
                    'answer_guidance': 'Filter by post count and project id and name.',
                    'explanation': 'Assesses array transformation.', 'evidence_refs': ['JD-01'],
                }],
            }]},
        )
        self.client.force_login(self.learner)
        response = self.client.get(reverse('interview_prep:preparation_questions', args=[preparation.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Get Users With More Than Two Posts')
        self.assertContains(response, 'Problem statement')
        self.assertContains(response, 'Function signature or starter code')
        self.assertContains(response, '<pre><code>function getUsersWithMultiplePosts(users) {}</code></pre>', html=True)
        self.assertContains(response, 'Reference solution')
        self.assertContains(response, 'user.posts.length &gt; 2')
        self.assertNotContains(response, 'Constraints and edge cases')
        self.assertNotContains(response, 'Additional requirements')
        self.assertNotContains(response, '<script>alert(1)</script>')

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
            'question_kind': 'scenario', 'coding_solution': '',
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

    @override_settings(INTERVIEW_PREP_OPENAI_API_KEY='test-key', INTERVIEW_PREP_TEST_ACCESS=True)
    @patch('interview_prep.views.generate_preparation')
    @patch('interview_prep.views.extract_candidate_profile')
    def test_candidate_reviews_profile_and_resumed_generation_reuses_confirmed_facts(self, extract_profile, generate):
        profile = {
            'skills': [{'id': 'RES-01', 'text': 'Python'}],
            'education': [], 'projects': [], 'experience': [], 'employment_history': [],
            'certifications': [], 'other_details': [],
            'summary': 'The resume lists Python experience.',
            'recommended_seniority': 'entry',
            'seniority_rationale': 'The resume shows foundational skills and a personal project.',
            'uncertain_information': [
                'The project dates are unclear.',
                '<script>alert("x")</script>',
            ],
            'career_gaps': [],
            'extraction': {
                'analysis': 'The resume lists Python experience.',
                'resume_facts': [{
                    'id': 'RES-01', 'fact': 'Python', 'fact_type': 'skill',
                    'competencies': ['Programming'],
                }],
                'jd_requirements': [{
                    'id': 'JD-01', 'requirement': 'Use Python.', 'mandatory': True,
                    'category': 'Programming', 'resume_fact_refs': ['RES-01'],
                    'match_level': 'strong', 'match_rationale': 'Python is listed.',
                    'suggestion': 'Give an example.',
                }],
                'skill_gaps': [], 'career_gaps': [],
                'recommended_seniority': 'entry',
                'seniority_rationale': 'Foundational evidence.',
                'uncertain_information': ['The project dates are unclear.'],
            },
        }
        extract_profile.return_value = profile
        reference = uuid.uuid4()
        form_data = {
            'request_reference': reference,
            'company_name': 'Acme', 'job_title': 'Python Developer',
            'role_family': 'general-software-engineering', 'seniority': 'entry',
            'question_target': 30,
            'job_description': 'Build Python services.',
            'resume_text': 'Private original resume text.',
            'consent_to_ai_provider': 'on', 'preparation_action': 'review',
        }
        self.client.force_login(self.learner)
        review = self.client.post(reverse('interview_prep:create_preparation'), form_data)
        self.assertEqual(review.status_code, 200)
        self.assertContains(review, 'Your resume match')
        self.assertContains(review, 'Details to confirm')
        self.assertContains(review, 'The project dates are unclear.')
        self.assertContains(review, '&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;')
        self.assertNotContains(review, '<script>alert("x")</script>')
        draft = PreparationSet.objects.get(owner=self.learner)
        self.assertNotIn('Private original resume text.', str(draft.generated_content))
        self.assertEqual(draft.generated_content['_candidate_profile_state'], 'review')

        resume_summary = 'Skills:\n- Python\n- SQL'
        confirmed_post = {
            **form_data,
            'preparation_action': 'generate', 'resume_draft_id': draft.pk,
            'seniority': 'mid', 'resume_text': resume_summary,
            'profile_skills': 'Python\nSQL', 'profile_education': '',
            'profile_projects': '', 'profile_experience': '',
            'profile_employment_history': '', 'profile_certifications': '',
            'profile_other_details': '',
        }

        def make_question(index):
            return {
                'id': f'r1-q{index:02d}',
                'question': f'How would you verify Python task {index}?',
                'category': 'Programming',
                'question_type': 'standardized',
                'question_kind': 'scenario',
                'coding_solution': '',
                'answer_content': _rich_answer(
                    'Check the input and explain the result.', [],
                    'I would check the input, explain the result, and verify it.',
                    'Name one test case.',
                ),
                'explanation': 'Assesses practical reasoning.',
                'evidence_refs': ['JD-01'],
            }

        checkpoint_questions = [make_question(index) for index in range(1, 25)]

        def fail_after_confirmation(**kwargs):
            self.assertEqual(kwargs['confirmed_extraction']['resume_facts'][1]['fact'], 'SQL')
            kwargs['progress_callback']({
                'phase': 'questions', 'completed': 24, 'total': 30,
                'round_number': 1,
                'round_questions': checkpoint_questions,
                'validated_questions': checkpoint_questions,
                'preview_questions': [row['question'] for row in checkpoint_questions[-5:]],
            })
            raise PreparationProviderError('Temporary provider interruption.')

        generate.side_effect = fail_after_confirmation
        failed = self.client.post(
            reverse('interview_prep:create_preparation'), confirmed_post,
            HTTP_ACCEPT='text/event-stream',
        )
        list(failed.streaming_content)
        draft.refresh_from_db()
        self.assertEqual(draft.generated_content['_candidate_profile_state'], 'confirmed')
        saved_extraction = draft.generated_content['_confirmed_extraction']
        self.assertEqual(draft.seniority, 'mid')
        self.assertEqual(draft.generated_content['_question_target'], 30)
        self.assertEqual(len(draft.generated_content['rounds'][0]['questions']), 24)
        self.assertEqual(draft.generated_content['_generation_progress'], {'completed': 24, 'total': 30})

        generate.side_effect = None
        generate.return_value = {
            'analysis': 'Confirmed profile reviewed.',
            'rounds': [{
                'round_number': 1,
                'title': 'Practice round 1',
                'questions': [make_question(index) for index in range(1, 31)],
            }],
            '_question_target': 30,
            '_generation_state': 'complete',
            '_generation_progress': {'completed': 30, 'total': 30},
        }
        resume_post = {
            **confirmed_post,
            'resume_text': 'Ignored raw text; saved profile is authoritative.',
        }
        resumed = self.client.post(reverse('interview_prep:create_preparation'), resume_post)
        self.assertEqual(resumed.status_code, 302)
        self.assertEqual(generate.call_args.kwargs['confirmed_extraction'], saved_extraction)
        self.assertIn('Python', generate.call_args.kwargs['resume_text'])
        self.assertIn('SQL', generate.call_args.kwargs['resume_text'])
        self.assertEqual(generate.call_args.kwargs['target_question_count'], 30)
        self.assertEqual(len(generate.call_args.kwargs['resume_content']['rounds'][0]['questions']), 24)

        draft.refresh_from_db()
        self.assertEqual(draft.generated_content['_generation_state'], 'complete')
        self.assertEqual(draft.generated_content['_generation_progress'], {'completed': 30, 'total': 30})
        self.assertEqual(len(draft.generated_content['rounds'][0]['questions']), 30)
        detail = self.client.get(reverse('interview_prep:preparation_detail', args=[draft.pk]))
        questions_page = self.client.get(reverse('interview_prep:preparation_questions', args=[draft.pk]))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(questions_page.status_code, 200)
        self.assertContains(questions_page, '30 of 30 valid questions are ready')

    @override_settings(
        INTERVIEW_PREP_OPENAI_API_KEY='test-key',
        INTERVIEW_PREP_TEST_ACCESS=True,
    )
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

