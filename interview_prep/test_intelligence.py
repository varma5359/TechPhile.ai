import json
import shutil
import subprocess
import requests
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, TestCase, override_settings

from .answer_content import normalize_answer_content, validate_answer_content
from .blueprint import build_competency_blueprint, map_jd_requirements
from .candidate_profile import confirm_profile_edits, profile_to_resume_text
from .intelligence_schema import coding_prompt_errors, count_valid_unique_questions, validate_intelligence_output
from .learning_aids import build_learning_aid
from .market_research import register_research_provider, research_job_market
from .openai_generator import PreparationProviderError, _batch_validation_errors, _build_jd_match, _check_extraction, _clean_career_gaps, _coverage_target, _invalid_question_indexes, _quality_failure_message, _question_plan, _questions_are_semantic_duplicates, _semantic_duplicate_pairs, _request_json, _slot_exercise, _slot_focus
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


def valid_countable_question(number, *, question=None, question_kind='scenario', coding_solution=''):
    return {
        'id': f'r1-q{number:02d}',
        'question': question or f'How would you verify result {number}?',
        'category': 'Data quality',
        'question_type': 'standardized',
        'question_kind': question_kind,
        'coding_solution': coding_solution,
        'answer_content': valid_answer_content(),
        'explanation': 'Assesses practical reasoning.',
        'evidence_refs': ['JD-01'],
    }


class RoleProfileAndSchemaTests(SimpleTestCase):
    def test_career_gap_uses_supported_employment_intervals_not_model_duration(self):
        facts = [
            {'id': 'RES-01', 'fact': 'Example Co, Analyst, Jan 2018 – Dec 2019', 'fact_type': 'employment_history'},
            {'id': 'RES-02', 'fact': 'Sample Ltd, Analyst, Jul 2020 – Present', 'fact_type': 'employment_history'},
        ]
        gaps = _clean_career_gaps({
            'career_gaps': [{'period': '2019–2023', 'months': 48, 'evidence_refs': ['RES-01', 'RES-02'], 'reason_stated': True}],
        }, {}, facts)
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]['period'], 'Jan 2020–Jun 2020')
        self.assertEqual(gaps[0]['months'], 6)
        self.assertEqual(gaps[0]['evidence_refs'], ['RES-01', 'RES-02'])
        self.assertFalse(gaps[0]['reason_stated'])

    def test_career_gap_merges_overlapping_employment_intervals(self):
        facts = [
            {'id': 'RES-01', 'fact': 'First employer, Engineer, Jan 2018 – Dec 2020', 'fact_type': 'employment_history'},
            {'id': 'RES-02', 'fact': 'Second employer, Consultant, Jun 2019 – Mar 2021', 'fact_type': 'employment_history'},
        ]
        self.assertEqual(_clean_career_gaps({}, {}, facts), [])

    def test_missing_or_ambiguous_employment_dates_leave_timeline_unverified(self):
        facts = [
            {'id': 'RES-01', 'fact': 'First employer, Engineer, Jan 2018 – Dec 2019', 'fact_type': 'employment_history'},
            {'id': 'RES-02', 'fact': 'Second employer, Consultant, 2022', 'fact_type': 'employment_history'},
        ]
        model_gap = {'career_gaps': [{'period': '2020–2021', 'months': 24, 'evidence_refs': ['RES-01', 'RES-02'], 'reason_stated': False}]}
        self.assertEqual(_clean_career_gaps(model_gap, {}, facts), [])

    def test_coding_plan_targets_missing_jd_skills_without_claiming_resume_experience(self):
        plan = _question_plan(
            [{'id': 'RES-01', 'fact': 'Completed a statistics course.', 'fact_type': 'education'}],
            'Use Python and SQL to analyze data.', 'data-analytics', 'entry',
            requirements=[
                {'id': 'JD-01', 'requirement': 'Develop Python scripts.', 'mandatory': True},
                {'id': 'JD-02', 'requirement': 'Write SQL queries.', 'mandatory': False},
            ],
        )
        self.assertEqual(plan['jd_coding_skills'], ['Python', 'SQL'])
        python_slot = _slot_exercise('standardized', 0, 1, plan)
        sql_slot = _slot_exercise('standardized', 1, 1, plan)
        self.assertEqual(python_slot, {'skill': 'Python', 'kind': 'coding', 'resume_supported': False})
        self.assertEqual(sql_slot, {'skill': 'SQL', 'kind': 'sql', 'resume_supported': False})
        self.assertIn('do not imply', _slot_focus('standardized', 0, 1, plan, [], []))

    def test_coding_plan_uses_resume_evidence_when_jd_skill_is_documented(self):
        facts = [{'id': 'RES-07', 'fact': 'Built Python data validation scripts.', 'fact_type': 'skill', 'competencies': ['Programming']}]
        plan = _question_plan(
            facts, 'Build Python data tools.', 'general-software-engineering', 'mid',
            requirements=[{'id': 'JD-01', 'requirement': 'Implement Python utilities.', 'mandatory': True}],
        )
        self.assertEqual(plan['jd_coding_skills'], [])
        self.assertIn('Python', plan['resume_coding_exercises'])
        slot = _slot_exercise('personalized', 30 - plan['personalized_count'], 1, plan)
        self.assertEqual(slot, {'skill': 'Python', 'kind': 'coding', 'resume_supported': True})
        self.assertIn('resume evidence', _slot_focus('personalized', 30 - plan['personalized_count'], 1, plan, facts, []))

    def test_business_analytics_does_not_force_unrelated_programming_exercises(self):
        plan = _question_plan(
            [{'id': 'RES-01', 'fact': 'Created a Python script in coursework.', 'fact_type': 'education'}],
            'Communicate business insights to stakeholders.', 'business-analytics', 'entry',
            requirements=[{'id': 'JD-01', 'requirement': 'Present clear insights.', 'mandatory': True}],
        )
        self.assertEqual(plan['coding_count'], 0)
        self.assertIsNone(_slot_exercise('standardized', 0, 1, plan))

    def test_coding_planner_calibrates_difficulty_to_seniority(self):
        requirement = [{'id': 'JD-01', 'requirement': 'Use Python.', 'mandatory': True}]
        entry = _question_plan([], 'Use Python.', 'data-analytics', 'entry', requirements=requirement)
        senior = _question_plan([], 'Use Python.', 'data-analytics', 'senior', requirements=requirement)
        self.assertIn('Beginner-friendly', _slot_focus('standardized', 0, 1, entry, [], []))
        self.assertIn('optimization task', _slot_focus('standardized', 0, 1, senior, [], []))

    def test_javascript_coding_regression_example_matches_strict_condition_and_edge_case(self):
        if not shutil.which('node'):
            self.skipTest('Node.js is required for the JavaScript regression example.')
        prompt = {
            'title': 'Get Users With More Than Two Posts',
            'language': 'JavaScript', 'difficulty': 'Entry',
            'problem_statement': 'Write a function named getUsersWithMultiplePosts that accepts an array of user objects with id, name, and posts. Return only id and name for users whose posts array has more than two items.',
            'function_signature': '```javascript\nfunction getUsersWithMultiplePosts(users) {\n    // Write your solution here\n}\n```',
            'example_input': '```javascript\n[{ id: 1, name: "Alice", posts: [{ id: 101 }, { id: 102 }] }, { id: 2, name: "Bob", posts: [{ id: 201 }, { id: 202 }, { id: 203 }] }]\n```',
            'expected_output': '```javascript\n[{ id: 2, name: "Bob" }]\n```',
            'explanation': 'Alice has two posts and is excluded. Bob has three and is included. Returned objects contain only id and name.',
            'constraints': 'An empty input array returns []. The condition is strictly greater than two.',
            'additional_requirements': 'Do not return the posts property.',
        }
        solution = 'function getUsersWithMultiplePosts(users) { return users.filter(user => user.posts.length > 2).map(({id, name}) => ({id, name})); }'
        self.assertEqual(coding_prompt_errors(prompt), [])
        self.assertIn('more than two', prompt['problem_statement'])
        self.assertNotIn('two or more', prompt['problem_statement'])
        self.assertIn('Alice', prompt['example_input'])
        self.assertIn('Bob', prompt['example_input'])
        self.assertIn('Bob', prompt['expected_output'])
        self.assertIn('returns []', prompt['constraints'])
        source = (
            solution + '\nconst users = ['
            '{id:1,name:"Alice",posts:[{id:101},{id:102}]},'
            '{id:2,name:"Bob",posts:[{id:201},{id:202},{id:203}]}'
            ']; console.log(JSON.stringify([getUsersWithMultiplePosts(users),getUsersWithMultiplePosts([])]));'
        )
        result = subprocess.run(['node', '-e', source], check=True, capture_output=True, text=True)
        self.assertEqual(json.loads(result.stdout), [[{'id': 2, 'name': 'Bob'}], []])

    def test_incomplete_coding_question_is_rejected_for_recovery(self):
        question = valid_countable_question(
            1, question_kind='coding', coding_solution='```javascript\nreturn [];\n```',
        )
        question['question_kind'] = 'coding'
        question['coding_prompt'] = {}
        errors = _batch_validation_errors(
            [question], ['standardized'], ['Data quality'], {'JD-01'}, [],
            expected_kinds=['coding'],
        )
        self.assertTrue(any('coding prompt needs title' in error for error in errors))
        self.assertEqual(_invalid_question_indexes(errors, 1), [0])
        question['coding_prompt'] = {
            'title': 'Filter records', 'language': 'JavaScript', 'difficulty': 'Entry',
            'problem_statement': 'Return matching records.', 'function_signature': '',
            'example_input': '```javascript\n[]\n```', 'expected_output': '```javascript\n[]\n```',
            'explanation': 'An empty list remains empty.', 'constraints': '', 'additional_requirements': '',
        }
        self.assertEqual(_batch_validation_errors(
            [question], ['standardized'], ['Data quality'], {'JD-01'}, [],
            expected_kinds=['coding'],
        ), [])

    def test_candidate_profile_edits_are_saved_as_generation_evidence(self):
        profile = {
            'skills': [{'id': 'RES-01', 'text': 'Python'}],
            'education': [{'id': 'RES-02', 'text': 'BSc Computer Science'}],
            'projects': [{'id': 'RES-03', 'text': 'Built a Django API'}],
            'experience': [], 'employment_history': [], 'certifications': [], 'other_details': [],
            'extraction': {
                'resume_facts': [
                    {'id': 'RES-01', 'fact': 'Python', 'fact_type': 'skill', 'competencies': ['Programming']},
                    {'id': 'RES-02', 'fact': 'BSc Computer Science', 'fact_type': 'education', 'competencies': ['Education']},
                    {'id': 'RES-03', 'fact': 'Built a Django API', 'fact_type': 'project', 'competencies': ['APIs']},
                ],
                'jd_requirements': [{
                    'id': 'JD-01', 'requirement': 'Build Python APIs.', 'resume_fact_refs': ['RES-01', 'RES-03'],
                    'match_level': 'strong', 'match_rationale': 'Evidence matches.',
                }],
                'skill_gaps': [], 'career_gaps': [], 'analysis': 'Relevant profile.',
            },
        }
        confirmed = confirm_profile_edits(profile, {
            'profile_skills': 'Python\nSQL',
            'profile_education': 'BSc Computer Science',
            'profile_projects': 'Built an inventory API',
            'profile_experience': '', 'profile_employment_history': '',
            'profile_certifications': '', 'profile_other_details': '',
        })
        self.assertEqual([row['text'] for row in confirmed['skills']], ['Python', 'SQL'])
        self.assertEqual(confirmed['extraction']['resume_facts'][3]['fact'], 'Built an inventory API')
        self.assertEqual(confirmed['extraction']['resume_facts'][3]['fact_type'], 'project')
        self.assertEqual(confirmed['extraction']['jd_requirements'][0]['resume_fact_refs'], ['RES-01', 'RES-03'])
        self.assertIn('Skills:\n- Python\n- SQL', profile_to_resume_text(confirmed))

    def test_candidate_profile_cannot_be_confirmed_without_any_resume_details(self):
        profile = {
            'extraction': {'resume_facts': [], 'jd_requirements': [], 'skill_gaps': []},
        }
        with self.assertRaisesMessage(ValueError, 'at least one resume detail'):
            confirm_profile_edits(profile, {})

    def test_valid_unique_question_counter_enforces_complete_answer_and_deduplicates(self):
        questions = [valid_countable_question(index) for index in range(1, 30)]
        questions.append(valid_countable_question(30, question='How would you verify result 1?'))
        self.assertEqual(count_valid_unique_questions([
            {'round_number': 1, 'questions': questions},
        ], allowed_categories={'Data quality'}, valid_evidence_ids={'JD-01'}), 29)

        questions[-1] = valid_countable_question(30)
        questions[-1]['answer_content'] = {'direct_answer': 'Incomplete'}
        self.assertEqual(count_valid_unique_questions([
            {'round_number': 1, 'questions': questions},
        ], allowed_categories={'Data quality'}, valid_evidence_ids={'JD-01'}), 29)

    def test_coding_questions_count_only_with_a_fenced_solution(self):
        missing_solution = valid_countable_question(1, question_kind='coding')
        present_solution = valid_countable_question(
            2, question_kind='coding',
            coding_solution='```sql\nSELECT 1;\n```',
        )
        self.assertEqual(count_valid_unique_questions([
            {'round_number': 1, 'questions': [missing_solution, present_solution]},
        ]), 1)

    def test_sql_inline_code_and_scenario_language_mentions_keep_their_kinds(self):
        sql = valid_countable_question(1, question='Write a query for active users.', question_kind='sql', coding_solution='```sql\nSELECT id FROM users;\n```')
        conceptual = valid_countable_question(2, question='Explain what `map()` returns.', question_kind='conceptual')
        scenario = valid_countable_question(3, question='How would you review a Python change?', question_kind='scenario')
        self.assertEqual(count_valid_unique_questions([
            {'round_number': 1, 'questions': [sql, conceptual, scenario]},
        ]), 3)

    def test_counter_keeps_counting_valid_questions_from_older_saved_drafts(self):
        legacy = {
            'question': 'Describe a project you completed.',
            'answer_guidance': 'Explain your contribution and the result.',
            'explanation': 'Assesses project communication.',
            'evidence_refs': ['RES-01'],
        }
        self.assertEqual(count_valid_unique_questions([
            {'round_number': 1, 'questions': [legacy]},
        ]), 1)

    def test_provider_failures_use_generic_student_messages(self):
        for provider, status_code in (('groq', 429), ('openai', 418)):
            response = Mock()
            response.status_code = status_code
            response.headers = {}
            response.json.return_value = {
                'error': {'code': 'private_code', 'message': 'provider-secret-detail'}
            }
            response.raise_for_status.side_effect = requests.HTTPError(response=response)
            with self.subTest(provider=provider, status_code=status_code):
                with override_settings(
                    INTERVIEW_PREP_AI_PROVIDER=provider,
                    INTERVIEW_PREP_GROQ_API_KEY='key',
                    INTERVIEW_PREP_OPENAI_API_KEY='key',
                ), patch('interview_prep.openai_generator.requests.post', return_value=response), patch('interview_prep.openai_generator.time.sleep'):
                    with self.assertRaises(PreparationProviderError) as raised:
                        _request_json(
                            'Generate JSON.', {}, {'type': 'object', 'properties': {}},
                            'test-model', 'https://example.test/v1/responses', 'key',
                        )
                message = str(raised.exception)
                self.assertNotIn('groq', message.casefold())
                self.assertNotIn(str(status_code), message)
                self.assertNotIn('provider-secret-detail', message)

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

    def test_unmapped_requirement_gets_no_coverage_credit_and_keeps_resume_evidence_status(self):
        requirement = {
            'id': 'JD-UNMAPPED', 'mandatory': True, 'match_level': 'strong',
            'mapping_status': 'unmapped', 'category': 'Role fundamentals',
        }
        result = _build_jd_match([requirement])
        self.assertEqual(result['score'], 0)
        self.assertEqual(result['counts']['not_evidenced'], 1)
        self.assertEqual(result['mapping_counts'], {'mapped': 0, 'unmapped': 1})
        self.assertEqual(requirement['match_level'], 'strong')

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
        self.assertIn('completed questions are saved', failure_message)
        self.assertNotIn('AI', failure_message)

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

    def test_semantic_duplicates_are_reported_across_batches_and_rounds(self):
        first = {
            **valid_countable_question(1, question='How would you diagnose a revenue decline after a dashboard update?'),
            'assessment_focus': 'diagnose revenue decline after update',
        }
        paraphrase = {
            **valid_countable_question(2, question='What would you investigate when sales fall following a reporting change?'),
            'assessment_focus': 'diagnose revenue decline after update',
        }
        errors = _batch_validation_errors(
            [paraphrase], ['standardized'], ['Data quality'], {'JD-01'}, [first],
        )
        self.assertTrue(any('semantically equivalent' in error for error in errors))
        self.assertEqual(
            _semantic_duplicate_pairs([
                {'round_number': 1, 'questions': [first]},
                {'round_number': 2, 'questions': [paraphrase]},
            ]),
            [((1, 1), (2, 1))],
        )

    def test_personalized_project_question_must_cite_and_name_its_planned_fact(self):
        question = {
            **valid_countable_question(1, question='Describe your inventory project and how you used SQL.'),
            'question_type': 'personalized',
            'evidence_refs': ['RES-02'],
        }
        evidence = {'id': 'RES-01', 'fact': 'Built an inventory dashboard using SQL.', 'fact_type': 'project'}
        errors = _batch_validation_errors(
            [question], ['personalized'], ['Projects and experience'],
            {'RES-01', 'RES-02'}, [], required_resume_evidence=[evidence],
        )
        self.assertTrue(any('planned resume evidence' in error for error in errors))

        question['evidence_refs'] = ['RES-01']
        self.assertEqual(_batch_validation_errors(
            [question], ['personalized'], ['Projects and experience'],
            {'RES-01', 'RES-02'}, [], required_resume_evidence=[evidence],
        ), [])

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

    def test_jd_requirement_mapping_handles_varied_wording_and_canonical_categories(self):
        requirements = [
            {'id': 'JD-01', 'requirement': 'Write queries across relational tables.', 'mandatory': True},
            {'id': 'JD-02', 'requirement': 'Find missing and duplicate records before publication.', 'mandatory': True},
            {'id': 'JD-03', 'requirement': 'Design an experiment and interpret its confidence interval.', 'mandatory': False},
            {'id': 'JD-04', 'requirement': 'Build executive dashboards that explain trends.', 'mandatory': False},
        ]
        mapped, diagnostics = map_jd_requirements('data-analytics', requirements)
        by_id = {row['id']: row for row in mapped}
        self.assertEqual(by_id['JD-01']['category'], 'SQL and data modelling')
        self.assertIn('SQL and data modelling', by_id['JD-01']['mapped_competencies'][0])
        self.assertEqual(by_id['JD-02']['category'], 'Role fundamentals')
        self.assertIn('data quality', by_id['JD-02']['mapped_competencies'])
        self.assertEqual(by_id['JD-03']['category'], 'Statistics and experimentation')
        self.assertEqual(by_id['JD-04']['category'], 'Data visualisation')
        self.assertEqual(diagnostics['unmapped'], [])

    def test_blueprint_uses_each_requested_target_and_covers_mandatory_categories(self):
        profile = get_role_profile('data-analytics')
        requirements = [
            {'id': 'JD-01', 'requirement': 'Write queries across relational tables.', 'mandatory': True},
            {'id': 'JD-02', 'requirement': 'Find missing and duplicate records before publication.', 'mandatory': True},
        ]
        mapped_requirements, _diagnostics = map_jd_requirements('data-analytics', requirements)
        self.assertIn(
            'JD requirement: Write queries across relational tables.',
            _coverage_target(
                'SQL and data modelling', 1, mapped_requirements,
                get_role_profile('data-analytics')['competencies'],
            ),
        )
        for target in (30, 45, 60):
            with self.subTest(target=target):
                blueprint = build_competency_blueprint(
                    'data-analytics', requirements, [], [], standard_ratio=0.70,
                    total_questions=target,
                )
                allocations = blueprint['round_allocations']
                self.assertEqual([row['total'] for row in allocations], [min(30, target - start) for start in range(0, target, 30)])
                self.assertEqual(sum(row['total'] for row in allocations), target)
                self.assertEqual(sum(sum(row['category_counts'].values()) for row in allocations), target)
                self.assertEqual(
                    sum(row['standardized'] + row['personalized'] for row in allocations), target,
                )
                for allocation in allocations:
                    self.assertGreaterEqual(allocation['category_counts']['SQL and data modelling'], 1)
                    self.assertGreaterEqual(allocation['category_counts']['Role fundamentals'], 1)
                self.assertEqual(blueprint['total_questions'], target)
                if target == 45:
                    self.assertEqual(allocations[0]['category_counts'], {
                        'Role fundamentals': 6,
                        'Problem solving': 4,
                        'Projects and experience': 4,
                        'Communication and collaboration': 3,
                        'SQL and data modelling': 5,
                        'Statistics and experimentation': 4,
                        'Data visualisation': 4,
                    })
                    self.assertEqual(allocations[1]['category_counts'], {
                        'Role fundamentals': 4,
                        'Problem solving': 2,
                        'Projects and experience': 2,
                        'Communication and collaboration': 1,
                        'SQL and data modelling': 3,
                        'Statistics and experimentation': 2,
                        'Data visualisation': 1,
                    })

    def test_invalid_or_unmapped_jd_categories_are_explicit_and_never_emitted(self):
        mapped, diagnostics = map_jd_requirements('data-analytics', [{
            'id': 'JD-99', 'requirement': 'Own lunar habitat operations.',
            'category': 'Unlisted category', 'mandatory': True,
        }])
        self.assertEqual(mapped[0]['category'], 'Role fundamentals')
        self.assertEqual(mapped[0]['mapping_status'], 'unmapped')
        self.assertEqual(mapped[0]['mapped_competencies'], [])
        self.assertEqual(mapped[0]['source_category'], 'Unlisted category')
        self.assertEqual(diagnostics['unmapped'], ['JD-99'])
        self.assertIn(mapped[0]['category'], get_role_profile('data-analytics')['categories'])

    def test_every_role_profile_competency_maps_to_an_allowed_category(self):
        for role_family, profile in ROLE_PROFILES.items():
            with self.subTest(role_family=role_family):
                requirements = [
                    {'id': f'JD-{index:02d}', 'requirement': competency}
                    for index, competency in enumerate(profile['competencies'], start=1)
                ]
                mapped, _diagnostics = map_jd_requirements(role_family, requirements)
                self.assertEqual(len(mapped), len(profile['competencies']))
                self.assertTrue(all(row['mapping_status'] == 'competency' for row in mapped))
                self.assertTrue(all(row['category'] in profile['categories'] for row in mapped))

    def test_question_plan_uses_confirmed_project_types_and_relevant_documented_skills(self):
        facts = [
            {'id': 'RES-01', 'fact': 'Python', 'fact_type': 'skill'},
            {'id': 'RES-02', 'fact': 'SQL', 'fact_type': 'skill'},
            {'id': 'RES-03', 'fact': 'Retail inventory dashboard using SQL and Power BI', 'fact_type': 'project'},
            {'id': 'RES-04', 'fact': 'Built a personal music playlist app in Java', 'fact_type': 'project'},
        ]
        plan = _question_plan(facts, 'Build SQL reports and inventory dashboards.', 'data-analytics', 'entry')
        self.assertEqual(plan['total'], 30)
        self.assertEqual(plan['coding_count'], 10)
        self.assertEqual(plan['project_count'], 6)
        self.assertEqual(plan['projects'][0]['id'], 'RES-03')
        coding_focus = _slot_focus('personalized', 30 - plan['personalized_count'], 1, plan, facts, [])
        self.assertIn('Beginner-friendly fundamentals', coding_focus)
        project_focus = [
            _slot_focus('personalized', 30 - plan['personalized_count'] + plan['coding_count'] + index,
                        1, plan, facts, [])
            for index in range(3)
        ]
        self.assertIn('purpose and design', project_focus[0])
        self.assertIn('actual contribution', project_focus[1])
        self.assertIn('documented challenge', project_focus[2])

        senior_plan = _question_plan(facts, 'Build SQL reports and inventory dashboards.', 'data-analytics', 'senior')
        senior_coding_focus = _slot_focus('personalized', 30 - senior_plan['personalized_count'], 1, senior_plan, facts, [])
        self.assertIn('optimization task', senior_coding_focus)
        self.assertNotIn('Beginner-friendly', senior_coding_focus)

    def test_company_name_adds_safe_motivation_focus_and_more_experience_allows_60(self):
        facts = [
            {'id': f'RES-{index:02d}', 'fact': f'Python SQL data analysis experience {index}', 'fact_type': 'experience'}
            for index in range(1, 13)
        ]
        plan = _question_plan(facts, 'Analyze data with Python and SQL.', 'data-analytics', 'mid', company_name='Example Ltd')
        self.assertEqual(plan['total'], 60)
        self.assertEqual(plan['coding_count'], 15)
        self.assertEqual(plan['company_count_per_round'], 1)
        company_focus = _slot_focus('standardized', 30 - plan['personalized_count'] - 1, 1, plan, facts, [])
        self.assertIn('company-motivation', company_focus)
        self.assertIn('make no factual claims', company_focus)

    def test_output_validator_enforces_two_distinct_evidence_linked_rounds(self):
        profile = get_role_profile('data-analytics')
        rounds = []
        for round_number in (1, 2):
            questions = []
            for index in range(30):
                questions.append({
                    'category': profile['categories'][index % len(profile['categories'])],
                    'question_type': 'standardized' if index < 21 else 'personalized',
                    'question_kind': 'scenario',
                    'coding_solution': '',
                    'question': f'Round {round_number}, question {index}: how would you verify this result?',
                    'answer_content': valid_answer_content(),
                    'explanation': 'Assesses evidence-based reasoning.',
                    'evidence_refs': ['RES-01'] if index >= 21 else ['JD-01'],
                })
            rounds.append({'round_number': round_number, 'title': f'Round {round_number}', 'questions': questions})
        result = {'analysis': 'Relevant evidence.', 'skill_gaps': [], 'rounds': rounds}
        self.assertEqual(validate_intelligence_output(result, profile['categories'], {'JD-01', 'RES-01'}), [])
        self.assertEqual(result['rounds'][1]['questions'][29]['id'], 'r2-q30')

        result['versions'] = {'schema': '1.7'}
        coding_question = result['rounds'][0]['questions'][0]
        coding_question['question_kind'] = 'coding'
        coding_question['coding_solution'] = '```javascript\nreturn [];\n```'
        self.assertTrue(any('structured coding prompt' in error for error in validate_intelligence_output(
            result, profile['categories'], {'JD-01', 'RES-01'},
        )))
        coding_question['coding_prompt'] = {
            'title': 'Filter users', 'language': 'JavaScript', 'difficulty': 'Entry',
            'problem_statement': 'Return matching users.', 'function_signature': '',
            'example_input': '```javascript\n[]\n```', 'expected_output': '```javascript\n[]\n```',
            'explanation': 'The empty input produces no results.', 'constraints': '',
            'additional_requirements': '',
        }
        self.assertEqual(validate_intelligence_output(
            result, profile['categories'], {'JD-01', 'RES-01'},
        ), [])

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
