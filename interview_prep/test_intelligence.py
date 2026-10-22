import json
import requests
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, TestCase, override_settings

from .answer_content import normalize_answer_content, validate_answer_content
from .blueprint import build_competency_blueprint
from .intelligence_schema import validate_intelligence_output
from .learning_aids import build_learning_aid
from .market_research import register_research_provider, research_job_market
from .openai_generator import _batch_validation_errors, _build_jd_match, _check_extraction, _coverage_target, _invalid_question_indexes, _only_semantic_overlap_errors, _quality_failure_message, _questions_are_semantic_duplicates, _request_json
from .templatetags.interview_prep_markdown import safe_markdown
from .role_profiles import ROLE_PROFILES, SENIORITY_LEVELS, get_role_profile


def valid_answer_content(direct_answer='Compare the relevant evidence and verify the result.', sections=None):
    return {
        'direct_answer': direct_answer,
        'sections': sections or [],
        'interview_ready_answer': direct_answer,
        'interviewer_evaluation': {
            'what_interviewer_checks': ['Question-specific technical reasoning.'],
            'common_mistake': 'Assuming a cause before checking the evidence.',
            'key_takeaway': 'Verify the evidence before deciding.',
        },
        'practice_activity': 'Explain the evidence you would inspect first.',
    }


class RoleProfileAndSchemaTests(SimpleTestCase):
    @override_settings(INTERVIEW_PREP_AI_PROVIDER='groq')
    def test_provider_retries_groq_structured_output_validation_error(self):
        rejected = Mock()
        rejected.status_code = 400
        rejected.headers = {}
        rejected.json.return_value = {'error': {'code': 'json_validate_failed', 'message': 'Invalid generated schema output.'}}
        rejected.raise_for_status.side_effect = requests.HTTPError(response=rejected)
        accepted = Mock()
        accepted.raise_for_status.return_value = None
        accepted.json.return_value = {
            'status': 'completed',
            'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': '{"ok": true}'}]}],
            'usage': {'input_tokens': 3, 'output_tokens': 2},
        }
        with patch('interview_prep.openai_generator.requests.post', side_effect=[rejected, accepted]) as post:
            result, _ = _request_json(
                'Return strict JSON.', {'value': 'test'},
                {'type': 'object', 'properties': {'ok': {'type': 'boolean'}}},
                'openai/gpt-oss-20b', 'https://api.groq.com/openai/v1/responses', 'test-key',
            )
        self.assertEqual(result, {'ok': True})
        self.assertEqual(post.call_count, 2)
        self.assertIn('schema validation', post.call_args_list[1].kwargs['json']['instructions'])
        self.assertIn('schema_validation_retry', post.call_args_list[1].kwargs['json']['input'])

    @override_settings(INTERVIEW_PREP_AI_PROVIDER='groq')
    def test_provider_falls_back_to_json_object_after_repeated_schema_rejection(self):
        rejected = Mock()
        rejected.status_code = 400
        rejected.headers = {}
        rejected.json.return_value = {'error': {'code': 'json_validate_failed', 'message': 'Invalid generated schema output.'}}
        rejected.raise_for_status.side_effect = requests.HTTPError(response=rejected)
        accepted = Mock()
        accepted.raise_for_status.return_value = None
        accepted.json.return_value = {
            'choices': [{'message': {'content': '{"ok": true}'}}],
            'usage': {'prompt_tokens': 3, 'completion_tokens': 2},
        }
        schema = {
            'type': 'object',
            'properties': {'ok': {'type': 'boolean'}},
            'required': ['ok'],
            'additionalProperties': False,
        }
        with patch('interview_prep.openai_generator.requests.post', side_effect=[rejected, rejected, rejected, rejected, accepted]) as post:
            result, _ = _request_json(
                'Return strict JSON.', {'value': 'test'}, schema,
                'openai/gpt-oss-20b', 'https://api.groq.com/openai/v1/responses', 'test-key',
            )
        self.assertEqual(result, {'ok': True})
        self.assertEqual(post.call_count, 5)
        fallback_call = post.call_args_list[-1]
        self.assertEqual(fallback_call.args[0], 'https://api.groq.com/openai/v1/chat/completions')
        fallback_payload = fallback_call.kwargs['json']
        self.assertEqual(fallback_payload['response_format'], {'type': 'json_object'})
        self.assertGreater(fallback_payload['max_completion_tokens'], 1000)
        self.assertIn('required_output_schema', fallback_payload['messages'][1]['content'])
        self.assertIn('json_mode_retry', fallback_payload['messages'][1]['content'])
        self.assertIn('validates it against the full schema', fallback_payload['messages'][0]['content'])

    def test_markdown_guidance_keeps_formatting_and_strips_unsafe_html(self):
        rendered = str(safe_markdown('**Approach**\n\n- Explain your method\n- Share the result\n\n<script>alert(1)</script>'))
        self.assertIn('<strong>Approach</strong>', rendered)
        self.assertIn('<ul>', rendered)
        self.assertNotIn('<script>', rendered)

    def test_markdown_guidance_renders_fenced_code_and_tables_safely(self):
        rendered = str(safe_markdown('''```sql
SELECT region, SUM(revenue) FROM sales GROUP BY region;
```

| Region | Revenue |
| --- | ---: |
| West | 200 |'''))
        self.assertIn('<pre><code>', rendered)
        self.assertIn('GROUP BY region', rendered)
        self.assertIn('<table>', rendered)

    def test_jd_match_score_weights_required_skills_and_uses_resume_evidence(self):
        requirements = [
            {'mandatory': True, 'match_level': 'strong'},
            {'mandatory': True, 'match_level': 'not_evidenced'},
            {'mandatory': False, 'match_level': 'partial'},
        ]
        result = _build_jd_match(requirements)
        self.assertEqual(result['score'], 50)
        self.assertEqual(result['counts']['strong'], 1)
        self.assertEqual(result['counts']['not_evidenced'], 1)

    def test_extraction_maps_resume_requirement_evidence_and_suggestions(self):
        facts, requirements, gaps, _ = _check_extraction({
            'analysis': 'Some relevant project experience.',
            'resume_facts': [{'id': 'fact-a', 'fact': 'Built a sales dashboard', 'competencies': ['visualisation']}],
            'jd_requirements': [
                {
                    'id': 'req-a', 'requirement': 'Build dashboards', 'mandatory': True,
                    'category': 'Data visualisation', 'resume_fact_refs': ['fact-a'],
                    'match_level': 'strong', 'match_rationale': 'Dashboard example matches.',
                    'suggestion': 'Quantify dashboard adoption.',
                },
                {
                    'id': 'req-b', 'requirement': 'Use Python', 'mandatory': False,
                    'category': 'Role fundamentals', 'resume_fact_refs': [],
                    'match_level': 'strong', 'match_rationale': '', 'suggestion': '',
                },
            ],
            'skill_gaps': [],
        })
        self.assertEqual(requirements[0]['resume_fact_refs'], ['RES-01'])
        self.assertEqual(requirements[1]['match_level'], 'not_evidenced')
        self.assertTrue(requirements[1]['suggestion'])

    def test_question_batch_validation_reports_repairable_quality_issues(self):
        errors = _batch_validation_errors(
            [{
                'question': 'How do you validate a dataset?',
                'answer_content': {},
                'explanation': 'Assesses data quality reasoning.',
                'evidence_refs': ['UNKNOWN-1'],
            }],
            ['standardized'], ['Data quality'], {'JD-01'},
            [{'question': 'How do you validate a dataset?'}],
        )
        self.assertTrue(any('answer content' in error for error in errors))
        self.assertTrue(any('invalid evidence' in error for error in errors))
        self.assertTrue(any('repeats an exact earlier question' in error for error in errors))
        self.assertEqual(_invalid_question_indexes(errors, 4), [0])
        self.assertEqual(_invalid_question_indexes(['incorrect question count'], 4), [0, 1, 2, 3])
        failure_message = _quality_failure_message(['question 1 repeats an exact earlier question'])
        self.assertIn('interviewer', failure_message)
        self.assertNotIn('AI', failure_message)

    def test_semantic_overlap_fallback_does_not_ignore_exact_or_structural_errors(self):
        self.assertTrue(_only_semantic_overlap_errors([
            'question 2 is semantically equivalent to an earlier question',
        ]))
        self.assertFalse(_only_semantic_overlap_errors([
            'question 2 repeats an exact earlier question',
        ]))
        self.assertFalse(_only_semantic_overlap_errors([
            'question 2 is semantically equivalent to an earlier question',
            'question 3 has missing or invalid evidence references',
        ]))

    def test_semantic_duplicate_detection_catches_reworded_sql_comparison(self):
        tcs_question = {
            'question': 'When merging two sales tables that share a primary key, what trade-off would you explain to a stakeholder between using UNION ALL and a FULL OUTER JOIN?',
            'assessment_focus': 'compare union all and full outer join',
        }
        amazon_question = {
            'question': 'Compare the trade-offs of using a UNION ALL versus a FULL OUTER JOIN when merging two sales datasets that share a primary key.',
            'assessment_focus': 'compare full outer join with union all',
        }
        self.assertTrue(_questions_are_semantic_duplicates(tcs_question, amazon_question))

    def test_semantic_duplicate_detection_catches_redefined_kpi_rewrite(self):
        dashboard_question = {
            'question': 'You are tasked with revising a sales KPI dashboard after the marketing team redefines the promoted sale metric to include only online channel sales. How would you update the data model and communicate the change to stakeholders?',
            'assessment_focus': 'revise promoted sales KPI data model and communication',
        }
        kpi_question = {
            'question': 'When a business unit redefines a KPI, explain how you would update your data model and communicate the change to stakeholders, ensuring continuity of reporting and avoiding misinterpretation.',
            'assessment_focus': 'update KPI definitions model and stakeholder communication',
        }
        self.assertTrue(_questions_are_semantic_duplicates(dashboard_question, kpi_question))

    def test_related_questions_on_same_topic_are_not_duplicates(self):
        append_question = {
            'question': 'How would you use UNION ALL to append monthly sales rows and identify duplicate records?',
            'assessment_focus': 'append monthly rows and detect duplicates',
        }
        join_question = {
            'question': 'How would a FULL OUTER JOIN help locate customer keys missing from either sales dataset?',
            'assessment_focus': 'find unmatched keys across datasets',
        }
        self.assertFalse(_questions_are_semantic_duplicates(append_question, join_question))

    def test_shared_context_with_different_assessment_focus_is_allowed(self):
        investigate = {
            'question': 'A sales KPI dropped after an update. How would you trace the data and explain the cause?',
            'assessment_focus': 'diagnose pipeline metric change',
        }
        communicate = {
            'question': 'A sales KPI dropped after an update. How would you explain the impact to a nontechnical stakeholder?',
            'assessment_focus': 'communicate business impact to stakeholders',
        }
        self.assertFalse(_questions_are_semantic_duplicates(investigate, communicate))

    def test_distinct_job_skills_remain_distinct_coverage(self):
        representative_questions = [
            {
                'question': 'Revenue fell after a deployment. How would you trace totals through the pipeline to locate the first divergence?',
                'assessment_focus': 'trace revenue metric pipeline change',
            },
            {
                'question': 'How would you detect missing, duplicated, and late-arriving source records before publishing a report?',
                'assessment_focus': 'validate missing duplicate late records',
            },
            {
                'question': 'Write a query that groups sales by region and calculates total revenue for a reporting period.',
                'assessment_focus': 'aggregate sales revenue by region using SQL',
            },
            {
                'question': 'When several requests compete for a short deadline, how would you prioritize work and communicate trade-offs?',
                'assessment_focus': 'prioritize competing requests under deadline',
            },
        ]
        for index, question in enumerate(representative_questions):
            for earlier in representative_questions[:index]:
                self.assertFalse(_questions_are_semantic_duplicates(question, earlier))

    def test_same_focus_rejects_wording_variation(self):
        first = {
            'question': 'How would you investigate an unexpected revenue decline?',
            'assessment_focus': 'diagnose unexpected revenue decrease',
        }
        paraphrase = {
            'question': 'What steps would you take after reported sales suddenly fell?',
            'assessment_focus': 'diagnose unexpected revenue decrease',
        }
        self.assertTrue(_questions_are_semantic_duplicates(first, paraphrase))

    def test_coverage_retry_rotates_to_a_different_skill_target(self):
        requirements = [{'category': 'Data quality', 'requirement': 'Validate source freshness'}]
        competencies = ['Data quality monitoring', 'SQL diagnostics', 'Stakeholder communication']
        original = _coverage_target('Data quality', 1, requirements, competencies)
        replacement = _coverage_target('Data quality', 1, requirements, competencies, rotation=1)
        self.assertNotEqual(original, replacement)

    def test_question_batch_validation_rejects_placeholder_answers(self):
        errors = _batch_validation_errors(
            [{
                'question': 'Compare two approaches to storing events.',
                'answer_content': valid_answer_content(
                    'Option A improves speed. Option B has a cost or limitation to check.'
                ),
                'explanation': 'Assesses trade-off reasoning.',
                'evidence_refs': ['JD-01'],
            }],
            ['standardized'], ['System design'], {'JD-01'}, [],
        )
        self.assertTrue(any('generic placeholder' in error for error in errors))

    def test_answer_content_rejects_malformed_table_and_normalizer_keeps_valid_content(self):
        content = valid_answer_content(sections=[{
            'title': 'Example output',
            'blocks': [{
                'type': 'table', 'title': '', 'text': '', 'items': [],
                'headers': ['Region', 'Revenue'], 'rows': [['West']],
                'code': '', 'language': 'text',
            }, {
                'type': 'code', 'title': 'Illustrative SQL', 'text': '', 'items': [],
                'headers': [], 'rows': [], 'code': 'SELECT 1;', 'language': 'sql',
            }, {
                'type': [], 'title': '', 'text': '', 'items': [], 'headers': [],
                'rows': [], 'code': '', 'language': [],
            }],
        }])
        self.assertTrue(any('table rows must match' in error for error in validate_answer_content(content)))
        normalized = normalize_answer_content(content)
        self.assertEqual(len(normalized['sections'][0]['blocks']), 1)
        self.assertEqual(normalized['sections'][0]['blocks'][0]['type'], 'code')

    def test_answer_content_accepts_concise_markdown_sections(self):
        content = valid_answer_content(sections=[{
            'title': 'Query and result',
            'markdown': """```sql
SELECT region, SUM(revenue) AS total_revenue
FROM sales
GROUP BY region;
```

| Region | Total |
| --- | ---: |
| West | 200 |""",
        }])
        self.assertEqual(validate_answer_content(content), [])
        normalized = normalize_answer_content(content)
        self.assertIn('GROUP BY region', normalized['sections'][0]['markdown'])
        self.assertEqual(normalized['sections'][0]['blocks'], [])

    def test_practice_prompts_follow_question_subject_without_answer_fallbacks(self):
        sql_aid = build_learning_aid({'question': 'How would you use SQL to explain this aggregation?', 'category': 'SQL'})
        pipeline_aid = build_learning_aid({'question': 'Investigate a metric that changed after an ETL update.', 'category': 'Data pipelines'})
        self.assertIn('query', sql_aid['practice_prompt'])
        self.assertIn('data through', pipeline_aid['practice_prompt'])
        self.assertNotIn('example', sql_aid)

    def test_all_existing_career_families_have_a_profile_and_seniority(self):
        expected = {
            'data-analytics', 'business-analytics', 'machine-learning-engineering',
            'computer-vision-engineering', 'generative-ai-engineering',
            'rag-development', 'agentic-ai-development',
        }
        self.assertTrue(expected.issubset(ROLE_PROFILES))
        self.assertEqual(set(SENIORITY_LEVELS), {'entry', 'mid', 'senior', 'lead'})
        self.assertEqual(get_role_profile('unknown')['label'], 'General Software Engineering')

    def test_blueprint_creates_30_question_competency_allocation(self):
        blueprint = build_competency_blueprint(
            'data-analytics',
            [{'id': 'JD-01', 'requirement': 'SQL reporting', 'mandatory': True}],
            [{'id': 'RES-01', 'fact': 'Used SQL'}],
            [],
        )
        self.assertEqual(sum(blueprint['per_round']['category_counts'].values()), 30)
        self.assertEqual(blueprint['per_round']['standardized'], 21)
        self.assertEqual(blueprint['per_round']['personalized'], 9)

    def test_output_validator_enforces_two_distinct_evidence_linked_rounds(self):
        profile = get_role_profile('data-analytics')
        rounds = []
        for round_number in (1, 2):
            questions = []
            for index in range(30):
                questions.append({
                    'category': profile['categories'][index % len(profile['categories'])],
                    'question_type': 'standardized' if index < 21 else 'personalized',
                    'question': f'Round {round_number}, question {index}: how would you verify this result?',
                    'answer_content': valid_answer_content(),
                    'explanation': 'Assesses evidence-based reasoning.',
                    'evidence_refs': ['RES-01'] if index >= 21 else ['JD-01'],
                })
            rounds.append({'round_number': round_number, 'title': f'Round {round_number}', 'questions': questions})
        result = {'analysis': 'Relevant evidence.', 'skill_gaps': [], 'rounds': rounds}
        self.assertEqual(validate_intelligence_output(result, profile['categories'], {'JD-01', 'RES-01'}), [])
        self.assertEqual(result['rounds'][1]['questions'][29]['id'], 'r2-q30')

        result['rounds'][1]['questions'][0]['question'] = result['rounds'][0]['questions'][0]['question']
        self.assertTrue(any('unique across both rounds' in error for error in validate_intelligence_output(result, profile['categories'], {'JD-01', 'RES-01'})))


class MarketResearchTests(TestCase):
    def tearDown(self):
        register_research_provider('test_provider', None)

    @override_settings(INTERVIEW_PREP_MARKET_RESEARCH_PROVIDER='none')
    def test_unconfigured_research_never_claims_a_search(self):
        result = research_job_market('data-analytics', 'Data Analyst')
        self.assertEqual(result['status'], 'not_performed')
        self.assertEqual(result['sources'], [])

    @override_settings(INTERVIEW_PREP_MARKET_RESEARCH_PROVIDER='test_provider', INTERVIEW_PREP_MARKET_RESEARCH_CACHE_HOURS=24)
    def test_research_validates_status_and_caches_source_results(self):
        provider = Mock()
        provider.search.return_value = [
            {
                'id': 'external-1', 'title': 'Data Analyst', 'employer': 'Example Ltd',
                'url': 'https://careers.example.com/jobs/1', 'published_at': '2026-10-20',
                'vacancy_status': 'verified_open', 'official_employer_source': True,
                'evidence': 'Employer careers page lists an active vacancy.',
            },
            {
                'title': 'Unverified role', 'url': 'https://jobs.example.net/2',
                'published_at': '2026-10-20', 'vacancy_status': 'verified_open',
                'official_employer_source': False,
            },
        ]
        register_research_provider('test_provider', provider)
        first = research_job_market('data-analytics', 'Data Analyst', 'Example Ltd')
        second = research_job_market('data-analytics', 'Data Analyst', 'Example Ltd')
        self.assertEqual(first['status'], 'completed')
        self.assertEqual(first['sources'][0]['vacancy_status'], 'verified_open')
        self.assertEqual(first['sources'][1]['vacancy_status'], 'unverified')
        self.assertEqual(second['status'], 'cached')
        provider.search.assert_called_once()
