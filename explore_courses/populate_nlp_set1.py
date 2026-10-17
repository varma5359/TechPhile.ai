from techphile_exams.explore_courses.populate_base import *

def populate():
    admin_user = get_admin_user()
    nlp_topic = Topic.objects.get_or_create(name="NLP")[0]
    
    # Create simple datasets
    greetings_data = """text,response
Hello,Hi there!
How are you?,I'm good, thanks!
What's your name?,I'm a chatbot
Goodbye,See you later!
"""
    greetings_dataset = create_dataset(
        "Greetings Q&A", greetings_data, "greetings.csv",
        "Simple question-answer pairs for chatbot training", admin_user
    )
    
    # More Basic NLP Problems
    problems = [
        {
            "title": "Count Characters in String",
            "description": "Count the number of characters in a string (including spaces).",
            "starter_code": '''text = "Hello World"

# Your code here''',
            "solution": '''print(len(text))''',
            "expected_output": "11",
            "difficulty": "beginner",
            "points": 30
        },
        {
            "title": "Count Words in String",
            "description": "Count the number of words in a string.",
            "starter_code": '''text = "Natural Language Processing is fun"

# Your code here''',
            "solution": '''print(len(text.split()))''',
            "expected_output": "4",
            "difficulty": "beginner",
            "points": 30
        },
        {
            "title": "Reverse a String",
            "description": "Reverse the characters in a string.",
            "starter_code": '''text = "Python"

# Your code here''',
            "solution": '''print(text[::-1])''',
            "expected_output": "nohtyP",
            "difficulty": "beginner",
            "points": 30
        },
        {
            "title": "Check Palindrome",
            "description": "Check if a word is a palindrome (reads same forwards and backwards).",
            "starter_code": '''word = "madam"

# Your code here''',
            "solution": '''print(word == word[::-1])''',
            "expected_output": "True",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Replace Words",
            "description": "Replace all occurrences of a word in a sentence.",
            "starter_code": '''sentence = "I like cats and cats are cute"

# Your code here''',
            "solution": '''print(sentence.replace("cats", "dogs"))''',
            "expected_output": "I like dogs and dogs are cute",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Find Longest Word",
            "description": "Find the longest word in a sentence.",
            "starter_code": '''sentence = "The quick brown fox jumps"

# Your code here''',
            "solution": '''print(max(sentence.split(), key=len))''',
            "expected_output": "quick",
            "difficulty": "beginner",
            "points": 50
        },
        {
            "title": "Count Vowels",
            "description": "Count the number of vowels in a string.",
            "starter_code": '''text = "Hello World"

# Your code here''',
            "solution": '''vowels = "aeiou"
count = sum(1 for char in text.lower() if char in vowels)
print(count)''',
            "expected_output": "3",
            "difficulty": "beginner",
            "points": 50
        },
        {
            "title": "Capitalize First Letters",
            "description": "Capitalize the first letter of each word in a sentence.",
            "starter_code": '''sentence = "natural language processing"

# Your code here''',
            "solution": '''print(sentence.title())''',
            "expected_output": "Natural Language Processing",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Remove Whitespace",
            "description": "Remove extra whitespace from the beginning and end of a string.",
            "starter_code": '''text = "   too much space   "

# Your code here''',
            "solution": '''print(text.strip())''',
            "expected_output": "too much space",
            "difficulty": "beginner",
            "points": 30
        },
        {
            "title": "Split by Character",
            "description": "Split a string into a list of characters.",
            "starter_code": '''word = "hello"

# Your code here''',
            "solution": '''print(list(word))''',
            "expected_output": "['h', 'e', 'l', 'l', 'o']",
            "difficulty": "beginner",
            "points": 30
        },
        {
            "title": "Join Words",
            "description": "Join a list of words into a single string with spaces.",
            "starter_code": '''words = ["I", "love", "Python"]

# Your code here''',
            "solution": '''print(" ".join(words))''',
            "expected_output": "I love Python",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Check Substring",
            "description": "Check if one string contains another string.",
            "starter_code": '''text = "The quick brown fox"
sub = "brown"

# Your code here''',
            "solution": '''print(sub in text)''',
            "expected_output": "True",
            "difficulty": "beginner",
            "points": 30
        },
        {
            "title": "Repeat String",
            "description": "Repeat a string multiple times.",
            "starter_code": '''word = "hello"

# Your code here''',
            "solution": '''print(word * 3)''',
            "expected_output": "hellohellohello",
            "difficulty": "beginner",
            "points": 30
        },
        {
            "title": "Count Specific Word",
            "description": "Count how many times a specific word appears in text.",
            "starter_code": '''text = "apple orange apple banana orange apple"
target = "apple"

# Your code here''',
            "solution": '''print(text.split().count(target))''',
            "expected_output": "3",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Swap Cases",
            "description": "Swap uppercase and lowercase letters in a string.",
            "starter_code": '''text = "Hello World"

# Your code here''',
            "solution": '''print(text.swapcase())''',
            "expected_output": "hELLO wORLD",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Find First Occurrence",
            "description": "Find the index of the first occurrence of a word.",
            "starter_code": '''text = "Python is great and Python is fun"
word = "Python"

# Your code here''',
            "solution": '''print(text.index(word))''',
            "expected_output": "0",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Check Digit",
            "description": "Check if a string contains any digits.",
            "starter_code": '''text = "Hello123"

# Your code here''',
            "solution": '''print(any(char.isdigit() for char in text))''',
            "expected_output": "True",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Remove Digits",
            "description": "Remove all digits from a string.",
            "starter_code": '''text = "Python3 is better than Python2"

# Your code here''',
            "solution": '''print(''.join(char for char in text if not char.isdigit()))''',
            "expected_output": "Python is better than Python",
            "difficulty": "beginner",
            "points": 50
        },
        {
            "title": "Simple Chat Response",
            "description": "Return a predefined response based on input text.",
            "starter_code": '''def respond(message):
    # Your code here
    return response

print(respond("Hello"))''',
            "solution": '''def respond(message):
    message = message.lower()
    if "hello" in message:
        return "Hi there!"
    elif "how are you" in message:
        return "I'm good, thanks!"
    else:
        return "I don't understand"

print(respond("Hello"))''',
            "expected_output": "Hi there!",
            "difficulty": "beginner",
            "points": 60
        },
        {
            "title": "Extract Numbers",
            "description": "Extract all numbers from a string.",
            "starter_code": '''text = "I have 3 apples and 5 oranges"

# Your code here''',
            "solution": '''print([int(s) for s in text.split() if s.isdigit()])''',
            "expected_output": "[3, 5]",
            "difficulty": "beginner",
            "points": 50
        }
    ]

    # Create Problem entries
    for p in problems:
        Problem.objects.get_or_create(
            title=p["title"],
            topic=nlp_topic,
            dataset=greetings_dataset if p.get("dataset") else None,
            difficulty=p["difficulty"],
            description=p["description"],
            starter_code=p["starter_code"],
            expected_output=p["expected_output"],
            solution=p["solution"],
            points=p["points"],
            created_by=admin_user
        )
    
    print("✅ 20 More Basic NLP problems populated.")

if __name__ == '__main__':
    populate()