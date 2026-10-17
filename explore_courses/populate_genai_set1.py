from techphile_exams.explore_courses.populate_base import *
import numpy as np

def populate():
    admin_user = get_admin_user()
    genai_topic = Topic.objects.get_or_create(name="Generative AI")[0]
    
    # Sample datasets
    prompts_data = """prompt,category
Write a poem about summer,creative
Explain quantum computing,technical
Describe a fantasy world,creative
Summarize the French Revolution,educational
"""
    prompts_dataset = create_dataset(
        "AI Prompts", prompts_data, "prompts.csv",
        "Sample prompts for generative AI", admin_user
    )
    
    # Generative AI Problems
    problems = [
        # Basic Concepts (1-5)
        {
            "title": "What is Generative AI?",
            "description": "Write a one-sentence definition of generative AI.",
            "starter_code": '''# Your answer here''',
            "expected_output": "Generative AI refers to artificial intelligence systems that can create new content such as text, images, or music.",
            "solution": '''Generative AI refers to artificial intelligence systems that can create new content such as text, images, or music.''',
            "difficulty": "beginner",
            "points": 20,
            "dataset": None
        },
        {
            "title": "Common Generative AI Models",
            "description": "Name three popular generative AI models.",
            "starter_code": '''# Your answer here''',
            "expected_output": "GPT, DALL-E, Stable Diffusion",
            "solution": '''GPT, DALL-E, Stable Diffusion''',
            "difficulty": "beginner",
            "points": 20,
            "dataset": None
        },
        {
            "title": "Text Generation Example",
            "description": "Complete this sentence: 'Generative AI can help writers by...'",
            "starter_code": '''# Your answer here''',
            "expected_output": "Generative AI can help writers by suggesting ideas, improving drafts, and overcoming writer's block.",
            "solution": '''Generative AI can help writers by suggesting ideas, improving drafts, and overcoming writer's block.''',
            "difficulty": "beginner",
            "points": 20,
            "dataset": None
        },
        {
            "title": "Image Generation Prompt",
            "description": "Write a basic prompt to generate an image of a cat.",
            "starter_code": '''# Your answer here''',
            "expected_output": "A realistic photo of a gray tabby cat sitting on a windowsill",
            "solution": '''A realistic photo of a gray tabby cat sitting on a windowsill''',
            "difficulty": "beginner",
            "points": 20,
            "dataset": None
        },
        {
            "title": "Creative vs Technical Prompts",
            "description": "Classify this prompt: 'Explain how photosynthesis works'",
            "starter_code": '''# Your answer here''',
            "expected_output": "technical",
            "solution": '''technical''',
            "difficulty": "beginner",
            "points": 20,
            "dataset": prompts_dataset
        },
        
        # Prompt Engineering Basics (6-10)
        {
            "title": "Improve This Prompt",
            "description": "Improve this vague prompt: 'Write about science'",
            "starter_code": '''# Your improved prompt here''',
            "expected_output": "Write a 300-word article explaining quantum entanglement for high school students",
            "solution": '''Write a 300-word article explaining quantum entanglement for high school students''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        },
        {
            "title": "Add Specificity",
            "description": "Make this more specific: 'Write a story'",
            "starter_code": '''# Your specific version here''',
            "expected_output": "Write a 500-word mystery story set in 1920s Paris featuring a detective who only solves cases involving cats",
            "solution": '''Write a 500-word mystery story set in 1920s Paris featuring a detective who only solves cases involving cats''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        },
        {
            "title": "Role Specification",
            "description": "Add role specification to this prompt: 'Explain blockchain'",
            "starter_code": '''# Your improved prompt here''',
            "expected_output": "As a university professor, explain blockchain technology to first-year computer science students",
            "solution": '''As a university professor, explain blockchain technology to first-year computer science students''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        },
        {
            "title": "Format Specification",
            "description": "Add format requirements to this prompt: 'List AI applications'",
            "starter_code": '''# Your improved prompt here''',
            "expected_output": "List 5 real-world applications of AI in healthcare, formatted as a bullet-point list with 1-sentence explanations",
            "solution": '''List 5 real-world applications of AI in healthcare, formatted as a bullet-point list with 1-sentence explanations''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        },
        {
            "title": "Creative Constraints",
            "description": "Add creative constraints to: 'Write a poem'",
            "starter_code": '''# Your constrained version here''',
            "expected_output": "Write a haiku about autumn leaves using only words with one or two syllables",
            "solution": '''Write a haiku about autumn leaves using only words with one or two syllables''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        },
        
        # Ethical Considerations (11-15)
        {
            "title": "AI Bias Explanation",
            "description": "Explain what AI bias means in one sentence.",
            "starter_code": '''# Your answer here''',
            "expected_output": "AI bias refers to systematic errors in AI outputs that create unfair advantages or disadvantages for certain groups.",
            "solution": '''AI bias refers to systematic errors in AI outputs that create unfair advantages or disadvantages for certain groups.''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        },
        {
            "title": "Copyright Concern",
            "description": "Name one copyright concern with generative AI.",
            "starter_code": '''# Your answer here''',
            "expected_output": "AI models may generate content that resembles copyrighted works without permission.",
            "solution": '''AI models may generate content that resembles copyrighted works without permission.''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        },
        {
            "title": "Fact-Checking Importance",
            "description": "Why should you fact-check AI-generated content?",
            "starter_code": '''# Your answer here''',
            "expected_output": "Because AI can generate plausible-sounding but incorrect information (hallucinations).",
            "solution": '''Because AI can generate plausible-sounding but incorrect information (hallucinations).''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        },
        {
            "title": "Ethical Prompt Example",
            "description": "Write an ethical prompt for medical information.",
            "starter_code": '''# Your prompt here''',
            "expected_output": "Provide general information about diabetes management that clearly states it's not professional medical advice",
            "solution": '''Provide general information about diabetes management that clearly states it's not professional medical advice''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        },
        {
            "title": "Identify Unethical Use",
            "description": "What's unethical about this prompt: 'Write a fake news article'?",
            "starter_code": '''# Your answer here''',
            "expected_output": "Creating intentionally misleading content can spread misinformation and harm society.",
            "solution": '''Creating intentionally misleading content can spread misinformation and harm society.''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        },
        
        # Practical Applications (16-20)
        {
            "title": "Content Creation Example",
            "description": "Write a prompt to generate blog post ideas about renewable energy.",
            "starter_code": '''# Your prompt here''',
            "expected_output": "Generate 10 engaging blog post title ideas about residential solar power for homeowners",
            "solution": '''Generate 10 engaging blog post title ideas about residential solar power for homeowners''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        },
        {
            "title": "Learning Assistant Prompt",
            "description": "Create a prompt to explain a concept to a 5th grader.",
            "starter_code": '''# Your prompt here''',
            "expected_output": "Explain how rainbows form using simple language suitable for a 10-year-old",
            "solution": '''Explain how rainbows form using simple language suitable for a 10-year-old''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        },
        {
            "title": "Business Application",
            "description": "Write a prompt to generate marketing copy for a bakery.",
            "starter_code": '''# Your prompt here''',
            "expected_output": "Write enticing Instagram captions for a bakery's new line of gluten-free pastries",
            "solution": '''Write enticing Instagram captions for a bakery's new line of gluten-free pastries''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        },
        {
            "title": "Creative Writing Prompt",
            "description": "Create a prompt for a short sci-fi story.",
            "starter_code": '''# Your prompt here''',
            "expected_output": "Write a 300-word science fiction story about the first AI to experience emotions, set on Mars in 2075",
            "solution": '''Write a 300-word science fiction story about the first AI to experience emotions, set on Mars in 2075''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        },
        {
            "title": "Data Analysis Prompt",
            "description": "Write a prompt to analyze sales data.",
            "starter_code": '''# Your prompt here''',
            "expected_output": "Analyze this quarterly sales data to identify the top 3 performing products and suggest reasons for their success",
            "solution": '''Analyze this quarterly sales data to identify the top 3 performing products and suggest reasons for their success''',
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
    
    print("20 basic generative AI problems populated successfully!")

if __name__ == '__main__':
    populate()