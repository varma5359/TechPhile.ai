"""Database-free tests for legacy lesson conversion proposals."""

import unittest

from careers.lesson_conversion import propose_lesson_conversion


class LessonConversionTests(unittest.TestCase):
    def test_null_and_empty_inputs_produce_empty_proposals(self):
        for payload in (None, {}):
            with self.subTest(payload=payload):
                result = propose_lesson_conversion(payload)
                self.assertEqual(result['source_payload'], payload)
                self.assertEqual(result['proposed_fields'], {})
                self.assertEqual(result['safe_fields'], {})
                self.assertEqual(result['conflicts'], [])
                self.assertEqual(result['unmapped_content'], {})
                self.assertEqual(result['unmapped_reasons'], {})

        result = propose_lesson_conversion({'intro': None, 'objectives': [], 'sections': []})
        self.assertEqual(result['proposed_fields'], {})
        self.assertEqual(result['unmapped_content'], {})

    def test_intro_maps_without_changing_source(self):
        payload = {'intro': '  Start with evidence.  '}
        result = propose_lesson_conversion(payload)
        self.assertEqual(result['safe_fields'], {'lesson_intro': payload['intro']})
        self.assertEqual(result['source_payload'], payload)
        self.assertIsNot(result['source_payload'], payload)

    def test_historical_scenario_object_has_documented_markdown_mapping(self):
        result = propose_lesson_conversion({
            'scenario': {'title': 'The sales drop', 'body': 'Sales fell 12%.', 'prompt': 'What next?'}
        })
        self.assertEqual(result['safe_fields']['lesson_scenario'],
                         '### The sales drop\n\nSales fell 12%.\n\n> What next?')
        self.assertEqual(result['unmapped_content'], {})

    def test_historical_revision_object_has_documented_markdown_mapping(self):
        result = propose_lesson_conversion({
            'revision': {'core': 'Validate first.', 'takeaways': ['Check dates.', 'Compare like with like.'],
                         'rule': 'Do not guess.'}
        })
        self.assertEqual(result['safe_fields']['lesson_revision'],
                         '**Most important idea:** Validate first.\n\n'
                         '- Check dates.\n- Compare like with like.\n\n**Rule:** Do not guess.')

    def test_objectives_fill_only_empty_existing_field(self):
        result = propose_lesson_conversion({'objectives': ['One', 'Two']}, {'objectives': '  '})
        self.assertEqual(result['safe_fields']['objectives'], 'One\nTwo')

    def test_objectives_conflict_is_reported_without_becoming_safe(self):
        result = propose_lesson_conversion({'objectives': ['Legacy objective']},
                                           {'objectives': 'Admin objective'})
        self.assertEqual(result['proposed_fields']['objectives'], 'Legacy objective')
        self.assertNotIn('objectives', result['safe_fields'])
        self.assertEqual(result['conflicts'], [{
            'source_key': 'objectives', 'target_field': 'objectives',
            'existing_value': 'Admin objective', 'proposed_value': 'Legacy objective',
        }])

    def test_documented_section_content_maps_to_markdown_body(self):
        payload = {'sections': [{
            'heading': 'Approach',
            'paragraphs': ['Start with the question.'],
            'steps': ['Validate data.', 'Compare periods.'],
            'bullets': ['Check region', 'Check channel'],
            'table': {'headers': ['Metric', 'Value'], 'rows': [['Sales', '12% | down']]},
            'callouts': [{'kind': 'tip', 'text': 'Use comparable dates.'}],
        }]}
        result = propose_lesson_conversion(payload)
        self.assertEqual(
            result['safe_fields']['lesson_body'],
            '## Approach\n\nStart with the question.\n\n'
            '1. Validate data.\n2. Compare periods.\n\n'
            '- Check region\n- Check channel\n\n'
            '| Metric | Value |\n| --- | --- |\n| Sales | 12% \\| down |\n\n'
            '!!! tip\n    Use comparable dates.',
        )
        self.assertEqual(result['unmapped_content'], {})

    def test_unsupported_sections_are_retained_as_unmapped(self):
        sections = [{'heading': 'Part', 'nested_widget': {'value': 3}}]
        result = propose_lesson_conversion({'sections': sections})
        self.assertNotIn('lesson_body', result['proposed_fields'])
        self.assertEqual(result['unmapped_content']['sections'], sections)
        self.assertIn('unsupported shape', result['unmapped_reasons']['sections'])

    def test_unknown_nested_scenario_key_is_retained_without_partial_conversion(self):
        scenario = {'title': 'Case', 'body': 'Known text', 'custom': {'data': [1, 2]}}
        result = propose_lesson_conversion({'scenario': scenario})
        self.assertNotIn('lesson_scenario', result['proposed_fields'])
        self.assertEqual(result['unmapped_content']['scenario'], scenario)
        self.assertIn('unsupported shape', result['unmapped_reasons']['scenario'])

    def test_diagrams_and_examples_remain_unmapped(self):
        diagrams = [{'type': 'flow', 'title': 'Flow', 'steps': [{'label': 'A', 'hint': 'B'}]}]
        example = {'title': 'Example', 'steps': [{'do': 'Check', 'why': 'Avoid errors'}]}
        result = propose_lesson_conversion({'diagrams': diagrams, 'example': example})
        self.assertEqual(result['unmapped_content'], {'diagrams': diagrams, 'example': example})
        self.assertEqual(set(result['unmapped_reasons']), {'diagrams', 'example'})
        self.assertNotIn('lesson_body', result['proposed_fields'])

    def test_unknown_keys_and_nested_values_are_retained(self):
        unknown = {'new_block': [{'deep': {'raw': [1, None, 'x']}}]}
        result = propose_lesson_conversion({'intro': 'Hello', **unknown})
        self.assertEqual(result['unmapped_content'], unknown)
        self.assertEqual(result['unmapped_reasons']['new_block'],
                         'Unknown top-level key; retained unchanged.')
        self.assertEqual(result['safe_fields'], {'lesson_intro': 'Hello'})

    def test_existing_lesson_fields_are_reported_as_conflicts(self):
        result = propose_lesson_conversion(
            {'intro': 'Legacy intro', 'scenario': 'Legacy scenario', 'revision': 'Legacy revision'},
            {'lesson_intro': 'Current intro', 'lesson_scenario': 'Current scenario',
             'lesson_revision': 'Current revision'},
        )
        self.assertEqual(result['safe_fields'], {})
        self.assertEqual([item['target_field'] for item in result['conflicts']],
                         ['lesson_intro', 'lesson_scenario', 'lesson_revision'])
        self.assertEqual(result['proposed_fields'], {
            'lesson_intro': 'Legacy intro',
            'lesson_scenario': 'Legacy scenario',
            'lesson_revision': 'Legacy revision',
        })

    def test_metadata_keys_map_to_existing_metadata_fields(self):
        result = propose_lesson_conversion({'minutes': 25, 'level': 'Beginner'})
        self.assertEqual(result['safe_fields'], {'estimated_minutes': 25, 'difficulty_level': 'Beginner'})

    def test_conversion_is_deterministic_and_source_copy_is_independent(self):
        payload = {
            'intro': 'Intro',
            'sections': [{'heading': 'One', 'paragraphs': ['Text']}],
            'unknown': {'nested': [1, 2]},
        }
        first = propose_lesson_conversion(payload)
        second = propose_lesson_conversion(payload)
        self.assertEqual(first, second)
        self.assertEqual(first['source_payload'], payload)
        first['source_payload']['unknown']['nested'].append(3)
        self.assertEqual(payload['unknown']['nested'], [1, 2])

    def test_non_object_payload_is_retained_as_unmapped(self):
        payload = ['legacy', {'unknown': True}]
        result = propose_lesson_conversion(payload)
        self.assertEqual(result['source_payload'], payload)
        self.assertEqual(result['unmapped_content'], {'$payload': payload})
        self.assertEqual(result['unmapped_reasons']['$payload'],
                         'The source payload must be a JSON object.')


if __name__ == '__main__':
    unittest.main()
