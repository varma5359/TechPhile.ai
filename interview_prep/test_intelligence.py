import json
import requests
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, TestCase, override_settings

from .blueprint import build_competency_blueprint
from .intelligence_schema import validate_intelligence_output
from .market_research import register_research_provider, research_job_market
from .openai_generator import _batch_validation_errors, _build_jd_match, _check_extraction, _invalid_question_indexes, _quality_failure_message, _request_json
from .templatetags.interview_prep_markdown import safe_markdown
from .role_profiles import ROLE_PROFILES, SENIORITY_LEVELS, get_role_profile


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

    def test_markdown_guidance_keeps_formatting_and_strips_unsafe_html(self):
        rendered = str(safe_markdown('**Approach**\n\n- Explain your method\n- Share the result\n\n<script>alert(1)</script>'))
        self.assertIn('<strong>Approach</strong>', rendered)
        self.assertIn('<ul>', rendered)
        self.assertNotIn('<script>', rendered)

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
                'answer_guidance': '',
                'explanation': 'Assesses data quality reasoning.',
                'evidence_refs': ['UNKNOWN-1'],
            }],
            ['standardized'], ['Data quality'], {'JD-01'},
            [{'question': 'How do you validate a dataset?'}],
        )
        self.assertTrue(any('answer guidance' in error for error in errors))
        self.assertTrue(any('invalid evidence' in error for error in errors))
        self.assertTrue(any('repeats an earlier question' in error for error in errors))
        self.assertEqual(_invalid_question_indexes(errors, 4), [0])
        self.assertEqual(_invalid_question_indexes(['incorrect question count'], 4), [0, 1, 2, 3])
        self.assertIn('repeating questions', _quality_failure_message(['question 1 repeats an earlier question']))

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
                    'answer_guidance': 'Explain your method and trade-offs.',
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
