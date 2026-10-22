"""Question-specific learning aids for older saved sets without structured guides."""


def build_learning_aid(question):
    """Choose a useful fallback format from the question and its existing answer tip."""
    question_text = str(question.get('question', '')).strip()
    guidance = str(question.get('answer_guidance', '')).strip()
    text = f'{question_text} {guidance}'.casefold()

    # Newer model output owns its own format (flow, table, STAR, etc.).
    guide_lower = guidance.casefold()
    if all(marker in guide_lower for marker in ('learn the idea', 'answer path', 'example')):
        return {'kind': 'model', 'title': 'Answer guide'}

    if any(term in text for term in ('trade-off', 'tradeoff', 'compare', 'versus', 'two ways', 'quick patch', 'full redesign')):
        if 'quick patch' in text or 'full redesign' in text:
            options = [
                {'name': 'Quick patch', 'benefit': 'Can reduce immediate impact and take less time.', 'risk': 'May leave the underlying design problem in place.'},
                {'name': 'Full redesign', 'benefit': 'Can improve long-term clarity and maintainability.', 'risk': 'Needs more time, testing, and careful rollout.'},
            ]
            example = (
                'I would first assess urgency, user impact, and the risk of changing the module. '
                'If users need a fast recovery, I would make a small, tested patch and record the follow-up redesign. '
                'If the module repeatedly causes problems or blocks needed work, I would plan a redesign in safe stages with the team.'
            )
        else:
            options = [
                {'name': 'Option A', 'benefit': 'What it improves', 'risk': 'Cost or limitation to check'},
                {'name': 'Option B', 'benefit': 'What it improves', 'risk': 'Cost or limitation to check'},
            ]
            example = 'Compare both options against the same needs, explain the main trade-off, then recommend one and say why.'
        return {
            'kind': 'table', 'title': 'Compare the choices',
            'simple_explanation': 'There may not be one right choice. Explain when each option fits, then choose using the impact and constraints in the question.',
            'options': options, 'example': example,
        }

    if any(term in text for term in ('tell me about a time', 'describe a time', 'a project you', 'your experience', 'you delivered', 'past experience')):
        return {
            'kind': 'star', 'title': 'Use a real example (STAR)',
            'simple_explanation': 'Use a real project or work example. Spend most of your answer on the actions you personally took.',
            'steps': [
                {'label': 'Situation', 'hint': 'What was happening? [real project or context]'},
                {'label': 'Task', 'hint': 'What did you need to do?'},
                {'label': 'Action', 'hint': 'What steps did you take?'},
                {'label': 'Result', 'hint': 'What changed or what did you learn?'},
            ],
            'example': 'Situation: [real example]. Task: [your responsibility]. Action: [the steps you took]. Result: [the outcome]. Replace each bracket with your own truthful details.',
        }

    if any(term in text for term in ('unexpected failure', 'diagnos', 'debug', 'production bug', 'incident')):
        return {
            'kind': 'flow', 'title': 'Trace the problem step by step',
            'simple_explanation': 'Start with what users see, use evidence to narrow down the cause, then verify the fix and prevent a repeat.',
            'steps': ['Check impact, logs, and monitoring', 'Reproduce safely', 'Isolate the failing component and recent changes', 'Fix, test, and monitor the result'],
            'example': 'I would first check the logs and monitoring to understand the impact. Then I would try to reproduce the issue, isolate the failing component, and review recent changes. After fixing it, I would test the change and monitor the service to confirm recovery.',
        }

    if any(term in text for term in ('migrat', 'step-by-step plan', 'roll out', 'deploy', 'implement', 'how would you')):
        if 'graphql' in text or 'rest api' in text:
            steps = ['Map current API behavior and client needs', 'Design the GraphQL schema and resolvers', 'Run both APIs while clients move gradually', 'Test, monitor, then retire old routes when safe']
            example = 'I would document the REST behavior clients rely on, design and test the GraphQL schema, then run both APIs in parallel. I would migrate clients in stages, monitor errors and performance, and retire REST routes only after clients have moved.'
            explanation = 'A gradual migration protects existing clients. Keep the old route working until the new path is tested and adopted.'
        elif 'health check' in text or 'reliability' in text:
            steps = ['List important failure modes', 'Choose checks that detect them', 'Set clear pass/fail thresholds', 'Alert, recover, and review results']
            example = 'I would check whether the service can start, reach required dependencies, and answer a simple request. I would set clear thresholds, alert on failures, and test that recovery works.'
            explanation = 'A useful health check tells you whether the service can safely do its job, not just whether its process is running.'
        else:
            steps = ['Clarify the goal and constraints', 'Choose a safe approach', 'Make the change in small steps', 'Test results and adjust']
            example = 'I would clarify the expected result and constraints, break the work into small steps, test each important change, and check the final result against the original goal.'
            explanation = 'A clear plan connects each action to the result you need and includes a way to check that it worked.'
        return {'kind': 'flow', 'title': 'Follow the steps', 'simple_explanation': explanation, 'steps': steps, 'example': example}

    if any(term in text for term in ('explain', 'what is ', 'how does ', 'concept', 'foundational knowledge')):
        return {
            'kind': 'concept', 'title': 'Explain the idea simply',
            'simple_explanation': 'Begin with a plain-language meaning. Then say why it matters, give a small example, and mention one limit or check.',
            'steps': ['Meaning', 'Why it matters', 'Simple example', 'Limit or check'],
            'example': 'A clear answer can start: "In simple terms, [idea] means ____. It matters because ____. For example, ____. I would check it by ____." Fill the blanks with the topic in the question.',
        }

    return {
        'kind': 'flow', 'title': 'Organize your answer',
        'simple_explanation': 'Make your reasoning easy to follow: state the goal, explain your approach, give an example, and say how you would check the result.',
        'steps': ['Goal', 'Approach', 'Example', 'Check the result'],
        'example': 'I would first clarify ____. Then I would ____. For example, ____. I would check success by ____.',
    }
