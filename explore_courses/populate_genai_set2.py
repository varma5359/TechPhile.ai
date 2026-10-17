from techphile_exams.explore_courses.populate_base import *
import numpy as np

def populate():
    admin_user = get_admin_user()
    genai_topic = Topic.objects.get_or_create(name="Generative AI")[0]
    
    # Sample datasets
    image_prompts = """prompt,style
A sunset over mountains,photorealistic
A robot cat playing guitar,cartoon
A futuristic city at night,cyberpunk
A bowl of fruit,watercolor
"""
    prompts_dataset = create_dataset(
        "Image Prompts", image_prompts, "image_prompts.csv",
        "Sample prompts for image generation", admin_user
    )
    
    # Generative AI Problems
    problems = [
        # Core Concepts (1-5)
        {
            "title": "How LLMs Work",
            "description": "Complete this sentence: 'Large Language Models predict...'",
            "starter_code": '''# Your answer here''',
            "expected_output": "Large Language Models predict the next word in a sequence based on patterns in their training data.",
            "solution": '''Large Language Models predict the next word in a sequence based on patterns in their training data.''',
            "difficulty": "beginner",
            "points": 20,
            "dataset": None
        },
        {
            "title": "Diffusion Models",
            "description": "What do diffusion models start with when generating images?",
            "starter_code": '''# Your answer here''',
            "expected_output": "Diffusion models start with random noise and gradually refine it into an image.",
            "solution": '''Diffusion models start with random noise and gradually refine it into an image.''',
            "difficulty": "beginner",
            "points": 20,
            "dataset": None
        },
        {
            "title": "Temperature Parameter",
            "description": "What does increasing the temperature parameter do in text generation?",
            "starter_code": '''# Your answer here''',
            "expected_output": "Increasing temperature makes outputs more random and creative.",
            "solution": '''Increasing temperature makes outputs more random and creative.''',
            "difficulty": "beginner",
            "points": 20,
            "dataset": None
        },
        {
            "title": "Tokenization",
            "description": "What is tokenization in NLP?",
            "starter_code": '''# Your answer here''',
            "expected_output": "Tokenization is the process of breaking text into smaller units (tokens) for processing.",
            "solution": '''Tokenization is the process of breaking text into smaller units (tokens) for processing.''',
            "difficulty": "beginner",
            "points": 20,
            "dataset": None
        },
        {
            "title": "Zero-Shot Learning",
            "description": "What is zero-shot learning?",
            "starter_code": '''# Your answer here''',
            "expected_output": "When a model performs tasks without specific training examples for that task.",
            "solution": '''When a model performs tasks without specific training examples for that task.''',
            "difficulty": "beginner",
            "points": 20,
            "dataset": None
        },
        
        # Prompt Engineering (6-10)
        {
            "title": "Negative Prompting",
            "description": "Add negative guidance to this image prompt: 'A beautiful landscape'",
            "starter_code": '''# Your improved prompt here''',
            "expected_output": "A beautiful landscape, low quality, blurry, distorted, unrealistic",
            "solution": '''A beautiful landscape, low quality, blurry, distorted, unrealistic''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        },
        {
            "title": "Style Specification",
            "description": "Add style to this prompt: 'A portrait of a dog'",
            "starter_code": '''# Your styled version here''',
            "expected_output": "A portrait of a dog in the style of Van Gogh painting",
            "solution": '''A portrait of a dog in the style of Van Gogh painting''',
            "difficulty": "beginner",
            "points": 30,
            "dataset":prompts_dataset
        },
        {
            "title": "Multi-Modal Prompt",
            "description": "Create a prompt that combines image and text generation",
            "starter_code": '''# Your prompt here''',
            "expected_output": "Generate an image of a medieval castle and write a 100-word story about it",
            "solution": '''Generate an image of a medieval castle and write a 100-word story about it''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        },
        {
            "title": "Iterative Refinement",
            "description": "Improve this vague prompt: 'Make a logo'",
            "starter_code": '''# Your refined prompt here''',
            "expected_output": "Design a minimalist logo for a coffee shop called 'Bean There', using coffee bean brown and cream colors",
            "solution": '''Design a minimalist logo for a coffee shop called 'Bean There', using coffee bean brown and cream colors''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        },
        {
            "title": "Technical Detail",
            "description": "Add technical specs to: 'Generate a website design'",
            "starter_code": '''# Your detailed prompt here''',
            "expected_output": "Generate a mobile-responsive website design for a bookstore with a dark mode option, using a 12-column grid layout",
            "solution": '''Generate a mobile-responsive website design for a bookstore with a dark mode option, using a 12-column grid layout''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        },
        
        # Evaluation (11-15)
        {
            "title": "Hallucination Check",
            "description": "Why should you verify facts in AI-generated content?",
            "starter_code": '''# Your answer here''',
            "expected_output": "Because AI can confidently generate incorrect or made-up information (hallucinations).",
            "solution": '''Because AI can confidently generate incorrect or made-up information (hallucinations).''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        },
        {
            "title": "Bias Detection",
            "description": "What's one way to check for bias in AI outputs?",
            "starter_code": '''# Your answer here''',
            "expected_output": "Test the model with diverse inputs and check for consistent unfair treatment of certain groups.",
            "solution": '''Test the model with diverse inputs and check for consistent unfair treatment of certain groups.''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        },
        {
            "title": "Quality Metrics",
            "description": "Name one metric for evaluating text generation quality.",
            "starter_code": '''# Your answer here''',
            "expected_output": "Perplexity (how surprised the model is by the text)",
            "solution": '''Perplexity (how surprised the model is by the text)''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        },
        {
            "title": "Human Evaluation",
            "description": "Why is human evaluation important for generative AI?",
            "starter_code": '''# Your answer here''',
            "expected_output": "Because humans can assess subjective qualities like coherence and creativity that metrics may miss.",
            "solution": '''Because humans can assess subjective qualities like coherence and creativity that metrics may miss.''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        },
        {
            "title": "Safety Check",
            "description": "What should you check before deploying AI-generated content?",
            "starter_code": '''# Your answer here''',
            "expected_output": "Verify for accuracy, bias, copyright issues, and appropriateness.",
            "solution": '''Verify for accuracy, bias, copyright issues, and appropriateness.''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        },
        
        # Applications (16-20)
        {
            "title": "Education Prompt",
            "description": "Create a prompt to generate a quiz question about photosynthesis.",
            "starter_code": '''# Your prompt here''',
            "expected_output": "Generate a multiple-choice quiz question about photosynthesis for 8th grade students, with 4 options and an explanation of the correct answer",
            "solution": '''Generate a multiple-choice quiz question about photosynthesis for 8th grade students, with 4 options and an explanation of the correct answer''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        },
        {
            "title": "Code Generation",
            "description": "Write a prompt to generate Python code.",
            "starter_code": '''# Your prompt here''',
            "expected_output": "Write a Python function that takes a list of numbers and returns the sum of even numbers",
            "solution": '''Write a Python function that takes a list of numbers and returns the sum of even numbers''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        },
        {
            "title": "Business Email",
            "description": "Create a prompt to draft a professional email.",
            "starter_code": '''# Your prompt here''',
            "expected_output": "Draft a polite 200-word email to reschedule a client meeting from Friday to next Monday, providing 3 alternative time slots",
            "solution": '''Draft a polite 200-word email to reschedule a client meeting from Friday to next Monday, providing 3 alternative time slots''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        },
        {
            "title": "Creative Constraint",
            "description": "Add constraints to: 'Write a story'",
            "starter_code": '''# Your constrained prompt here''',
            "expected_output": "Write a 200-word mystery story where the first letter of each sentence spells 'CLUE' when read vertically",
            "solution": '''Write a 200-word mystery story where the first letter of each sentence spells 'CLUE' when read vertically''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        },
        {
            "title": "Multilingual Prompt",
            "description": "Create a prompt for translation with context.",
            "starter_code": '''# Your prompt here''',
            "expected_output": "Translate this restaurant menu from English to Spanish, keeping culinary terms authentic",
            "solution": '''Translate this restaurant menu from English to Spanish, keeping culinary terms authentic''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        }
    ]
    
    for p in problems:
        Problem.objects.get_or_create(
            title=p["title"],
            topic=genai_topic,
            dataset=p.get("dataset"),
            difficulty=p["difficulty"],
            description=p["description"],
            starter_code=p["starter_code"],
            expected_output=p["expected_output"],
            solution=p["solution"],
            points=p["points"],
            created_by=admin_user
        )
    
    print("20 more basic generative AI problems populated successfully!")

if __name__ == '__main__':
    populate()