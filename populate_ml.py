from core.models import Topic, Question

# Get the topic instance
ml_topic = Topic.objects.get(name="Machine Learning")

# Logic gate problems
problems = [
    {
        "title": "Implement AND Logic Gate",
        "description": "Create a function that implements AND logic (returns 1 only if both inputs are 1).",
        "starter_code": '''def AND_gate(x1, x2):
    # Your code here
    return output

print(AND_gate(0, 1))''',
        "solution": '''def AND_gate(x1, x2):
    return 1 if x1 == 1 and x2 == 1 else 0

print(AND_gate(0, 1))''',
        "expected_output": "0",
        "difficulty": "beginner",
        "points": 50
    },
    {
        "title": "Implement OR Logic Gate",
        "description": "Create a function that implements OR logic (returns 1 if either input is 1).",
        "starter_code": '''def OR_gate(x1, x2):
    # Your code here
    return output

print(OR_gate(0, 1))''',
        "solution": '''def OR_gate(x1, x2):
    return 1 if x1 == 1 or x2 == 1 else 0

print(OR_gate(0, 1))''',
        "expected_output": "1",
        "difficulty": "beginner",
        "points": 50
    },
    {
        "title": "Implement NOT Logic Gate",
        "description": "Create a function that implements NOT logic (returns the opposite of input).",
        "starter_code": '''def NOT_gate(x):
    # Your code here
    return output

print(NOT_gate(1))''',
        "solution": '''def NOT_gate(x):
    return 0 if x == 1 else 1

print(NOT_gate(1))''',
        "expected_output": "0",
        "difficulty": "beginner",
        "points": 50
    }
]

# Save questions under "Machine Learning"
for data in problems:
    title=p["title"],
    topic=ai_topic,
    dataset=p.get("dataset"),
    difficulty=p["difficulty"],
    description=p["description"],
    starter_code=p["starter_code"],
    expected_output=p["expected_output"],
    solution=p["solution"],
    points=p["points"],
    created_by=admin_user
    
