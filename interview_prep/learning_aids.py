"""Question-specific practice prompts for generated interview questions."""


def build_learning_aid(question):
    """Return a practice task without replacing or inventing the model answer."""
    text = f"{question.get('question', '')} {question.get('category', '')}".casefold()

    if any(term in text for term in ('tell me about a time', 'describe a time', 'your experience', 'a project you')):
        prompt = (
            'Choose a real work, coursework, or personal project. Explain your own contribution, '
            'the decision you made, and the result without claiming someone else’s work.'
        )
    elif any(term in text for term in ('sql', 'query', 'aggregation', 'join')):
        prompt = 'Explain the rows you need, write or describe the query, and walk through what its result means.'
    elif any(term in text for term in ('python', 'code', 'function', 'script')):
        prompt = 'Describe the input, the key Python steps, and the expected output; then mention one edge case you would test.'
    elif any(term in text for term in ('model', 'machine learning', 'classifier', 'prediction', 'evaluation')):
        prompt = 'Name the data and metric you would use, explain why they fit the decision, and describe how you would check for failure on important subgroups.'
    elif any(term in text for term in ('pipeline', 'etl', 'data quality', 'missing', 'duplicated', 'late-arriving', 'metric changed')):
        prompt = 'Trace the data through the relevant stages, identify the evidence that would isolate the cause, and state how you would verify the correction.'
    elif any(term in text for term in ('prioriti', 'limited time', 'time is limited')):
        prompt = 'Rank the work using impact, risk, dependencies, and effort, then explain what you would defer and why.'
    elif any(term in text for term in ('stakeholder', 'non-technical', 'communicat', 'explain a result')):
        prompt = 'Explain the finding in plain language, connect it to a decision, and state the main caveat the audience needs to know.'
    else:
        prompt = 'Answer this specific question directly, support your reasoning with a relevant example, and explain how you would check that your approach worked.'

    return {'practice_prompt': prompt}
