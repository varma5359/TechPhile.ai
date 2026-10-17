#!/usr/bin/env python
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'techphile_exams.settings')
django.setup()

from django.contrib.auth.models import User
from coding.models import Problem, UserProfile

def create_sample_data():
    # Create admin user
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@techphile.ai',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        UserProfile.objects.create(user=admin_user)
        print("Created admin user (username: admin, password: admin123)")

    # Create sample problems
problem_data = [
    # Variables, Data Types, Input/Output (5 questions)
    {
        'title': 'Add Two Numbers',
        'slug': 'add-two-numbers',
        'description': 'Take two numbers as input and print their sum',
        'difficulty': 'Very Easy',
        'category': 'Variables/IO',
        'input_format': 'Two numbers separated by space',
        'output_format': 'Sum of the numbers',
        'constraints': '-1000 ≤ numbers ≤ 1000',
        'sample_input': '5 7',
        'sample_output': '12',
        'expected_output': '12',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Swap Two Variables',
        'slug': 'swap-variables',
        'description': 'Swap the values of two variables',
        'difficulty': 'Very Easy',
        'category': 'Variables',
        'input_format': 'Two values separated by space',
        'output_format': 'Swapped values',
        'constraints': 'Values can be any basic type',
        'sample_input': '10 hello',
        'sample_output': 'hello 10',
        'expected_output': 'hello 10',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Type Conversion',
        'slug': 'type-conversion',
        'description': 'Convert input string to integer and float',
        'difficulty': 'Very Easy',
        'category': 'Data Types',
        'input_format': 'A number as string',
        'output_format': 'Integer and float versions',
        'constraints': 'Input is a valid number string',
        'sample_input': '"123"',
        'sample_output': '123 123.0',
        'expected_output': '123 123.0',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'User Greeting',
        'slug': 'user-greeting',
        'description': 'Take user name as input and print a greeting',
        'difficulty': 'Very Easy',
        'category': 'Input/Output',
        'input_format': 'String name',
        'output_format': 'Greeting message',
        'constraints': '1 ≤ name.length ≤ 50',
        'sample_input': 'Alice',
        'sample_output': 'Hello, Alice!',
        'expected_output': 'Hello, Alice!',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Area of Circle',
        'slug': 'circle-area',
        'description': 'Calculate area of circle given radius',
        'difficulty': 'Very Easy',
        'category': 'Variables/Math',
        'input_format': 'Radius as float',
        'output_format': 'Area rounded to 2 decimals',
        'constraints': '0 < radius ≤ 1000',
        'sample_input': '5.0',
        'sample_output': '78.54',
        'expected_output': '78.54',
        'time_limit': 1000,
        'memory_limit': 64
    },

    # Conditional Statements (5 questions)
    {
        'title': 'Positive/Negative/Zero',
        'slug': 'check-number',
        'description': 'Check if number is positive, negative or zero',
        'difficulty': 'Very Easy',
        'category': 'Conditionals',
        'input_format': 'A number',
        'output_format': 'String classification',
        'constraints': '-10^9 ≤ number ≤ 10^9',
        'sample_input': '-5',
        'sample_output': 'Negative',
        'expected_output': 'Negative',
        'time_limit': 1000,
        'memory_limit': 64
    },

    {
        'title': 'Largest of Three',
        'slug': 'largest-of-three',
        'description': 'Find the largest of three numbers',
        'difficulty': 'Easy',
        'category': 'Conditionals',
        'input_format': 'Three numbers separated by spaces',
        'output_format': 'Largest number',
        'constraints': '-10^9 ≤ numbers ≤ 10^9',
        'sample_input': '10 20 15',
        'sample_output': '20',
        'expected_output': '20',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Leap Year Checker',
        'slug': 'leap-year',
        'description': 'Determine if a year is a leap year',
        'difficulty': 'Easy',
        'category': 'Conditionals',
        'input_format': 'Year as integer',
        'output_format': '"Leap Year" or "Not Leap Year"',
        'constraints': '1 ≤ year ≤ 9999',
        'sample_input': '2020',
        'sample_output': 'Leap Year',
        'expected_output': 'Leap Year',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Grade Calculator',
        'slug': 'grade-calculator',
        'description': 'Convert percentage to letter grade',
        'difficulty': 'Easy',
        'category': 'Conditionals',
        'input_format': 'Percentage score (0-100)',
        'output_format': 'Letter grade (A-F)',
        'constraints': '0 ≤ score ≤ 100',
        'sample_input': '85',
        'sample_output': 'B',
        'expected_output': 'B',
        'time_limit': 1000,
        'memory_limit': 64
    },

    # Loops (5 questions)
   
    {
        'title': 'Multiplication Table',
        'slug': 'multiplication-table',
        'description': 'Print multiplication table up to 10 for given number',
        'difficulty': 'Easy',
        'category': 'Loops',
        'input_format': 'An integer',
        'output_format': '10 lines of multiplication table',
        'constraints': '1 ≤ number ≤ 1000',
        'sample_input': '5',
        'sample_output': '5x1=5\n5x2=10\n...\n5x10=50',
        'expected_output': '5x1=5\n5x2=10\n...\n5x10=50',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Count Vowels',
        'slug': 'count-vowels',
        'description': 'Count vowels in a string',
        'difficulty': 'Easy',
        'category': 'Loops/String',
        'input_format': 'A string',
        'output_format': 'Number of vowels',
        'constraints': '1 ≤ string.length ≤ 1000',
        'sample_input': 'Hello World',
        'sample_output': '3',
        'expected_output': '3',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Factorial Calculation',
        'slug': 'factorial',
        'description': 'Calculate factorial of a number',
        'difficulty': 'Easy',
        'category': 'Loops',
        'input_format': 'Non-negative integer',
        'output_format': 'Factorial value',
        'constraints': '0 ≤ n ≤ 20',
        'sample_input': '5',
        'sample_output': '120',
        'expected_output': '120',
        'time_limit': 1000,
        'memory_limit': 64
    },

    # Functions and Recursion (5 questions)
    {
        'title': 'Function to Check Prime',
        'slug': 'is-prime-function',
        'description': 'Write a function to check if number is prime',
        'difficulty': 'Easy',
        'category': 'Functions',
        'input_format': 'An integer',
        'output_format': 'true/false',
        'constraints': '1 ≤ number ≤ 10^6',
        'sample_input': '13',
        'sample_output': 'true',
        'expected_output': 'true',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Recursive Fibonacci',
        'slug': 'recursive-fibonacci',
        'description': 'Calculate nth Fibonacci number using recursion',
        'difficulty': 'Easy',
        'category': 'Recursion',
        'input_format': 'Integer n',
        'output_format': 'nth Fibonacci number',
        'constraints': '0 ≤ n ≤ 20',
        'sample_input': '6',
        'sample_output': '8',
        'expected_output': '8',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Power Function',
        'slug': 'power-function',
        'description': 'Implement a function to calculate x^n',
        'difficulty': 'Easy',
        'category': 'Functions',
        'input_format': 'Base x and exponent n',
        'output_format': 'x raised to power n',
        'constraints': '-10 ≤ x ≤ 10\n0 ≤ n ≤ 10',
        'sample_input': '2 3',
        'sample_output': '8',
        'expected_output': '8',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Sum of Natural Numbers',
        'slug': 'sum-natural-numbers',
        'description': 'Calculate sum of first n natural numbers using recursion',
        'difficulty': 'Easy',
        'category': 'Recursion',
        'input_format': 'Integer n',
        'output_format': 'Sum of numbers',
        'constraints': '1 ≤ n ≤ 1000',
        'sample_input': '5',
        'sample_output': '15',
        'expected_output': '15',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Palindrome Checker Function',
        'slug': 'palindrome-function',
        'description': 'Write a function to check if string is palindrome',
        'difficulty': 'Easy',
        'category': 'Functions/String',
        'input_format': 'A string',
        'output_format': 'true/false',
        'constraints': '1 ≤ string.length ≤ 1000',
        'sample_input': 'madam',
        'sample_output': 'true',
        'expected_output': 'true',
        'time_limit': 1000,
        'memory_limit': 64
    },

    # Arrays/Lists (5 questions)
    {
        'title': 'Find Maximum in Array',
        'slug': 'array-max',
        'description': 'Find the maximum value in an array',
        'difficulty': 'Very Easy',
        'category': 'Arrays',
        'input_format': 'List of numbers',
        'output_format': 'Maximum value',
        'constraints': '1 ≤ array.length ≤ 1000',
        'sample_input': '[3, 5, 2, 8, 1]',
        'sample_output': '8',
        'expected_output': '8',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Array Sum',
        'slug': 'array-sum',
        'description': 'Calculate sum of all elements in array',
        'difficulty': 'Very Easy',
        'category': 'Arrays',
        'input_format': 'List of numbers',
        'output_format': 'Sum of elements',
        'constraints': '1 ≤ array.length ≤ 1000',
        'sample_input': '[1, 2, 3, 4, 5]',
        'sample_output': '15',
        'expected_output': '15',
        'time_limit': 1000,
        'memory_limit': 64
    },


    {
        'title': 'Array Average',
        'slug': 'array-average',
        'description': 'Calculate average of array elements',
        'difficulty': 'Very Easy',
        'category': 'Arrays',
        'input_format': 'List of numbers',
        'output_format': 'Average (float)',
        'constraints': '1 ≤ array.length ≤ 1000',
        'sample_input': '[10, 20, 30, 40]',
        'sample_output': '25.0',
        'expected_output': '25.0',
        'time_limit': 1000,
        'memory_limit': 64
    },

    # Dictionaries/Sets/Tuples (5 questions)
    {
        'title': 'Word Frequency Counter',
        'slug': 'word-frequency',
        'description': 'Count frequency of each word in a string',
        'difficulty': 'Easy',
        'category': 'Dictionaries',
        'input_format': 'A string',
        'output_format': 'Dictionary of word counts',
        'constraints': '1 ≤ string.length ≤ 1000',
        'sample_input': 'hello world hello',
        'sample_output': '{"hello": 2, "world": 1}',
        'expected_output': '{"hello": 2, "world": 1}',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Unique Elements',
        'slug': 'unique-elements',
        'description': 'Find all unique elements in a list',
        'difficulty': 'Easy',
        'category': 'Sets',
        'input_format': 'List of elements',
        'output_format': 'List of unique elements',
        'constraints': '1 ≤ list.length ≤ 1000',
        'sample_input': '[1, 2, 2, 3, 4, 4, 5]',
        'sample_output': '[1, 2, 3, 4, 5]',
        'expected_output': '[1, 2, 3, 4, 5]',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Tuple Unpacking',
        'slug': 'tuple-unpacking',
        'description': 'Unpack a tuple into individual variables',
        'difficulty': 'Very Easy',
        'category': 'Tuples',
        'input_format': 'Tuple of 3 elements',
        'output_format': 'Three separate values',
        'constraints': 'Tuple contains 3 elements',
        'sample_input': '(10, 20, 30)',
        'sample_output': '10 20 30',
        'expected_output': '10 20 30',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Dictionary Merging',
        'slug': 'merge-dictionaries',
        'description': 'Merge two dictionaries into one',
        'difficulty': 'Easy',
        'category': 'Dictionaries',
        'input_format': 'Two dictionaries',
        'output_format': 'Merged dictionary',
        'constraints': 'Both dictionaries have string keys',
        'sample_input': '{"a": 1, "b": 2}\n{"c": 3, "d": 4}',
        'sample_output': '{"a": 1, "b": 2, "c": 3, "d": 4}',
        'expected_output': '{"a": 1, "b": 2, "c": 3, "d": 4}',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Set Operations',
        'slug': 'set-operations',
        'description': 'Perform union, intersection on two sets',
        'difficulty': 'Easy',
        'category': 'Sets',
        'input_format': 'Two sets of numbers',
        'output_format': 'Union and intersection',
        'constraints': '1 ≤ set sizes ≤ 100',
        'sample_input': '{1, 2, 3}\n{2, 3, 4}',
        'sample_output': 'Union: {1, 2, 3, 4}\nIntersection: {2, 3}',
        'expected_output': 'Union: {1, 2, 3, 4}\nIntersection: {2, 3}',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
    'title': 'Frequency of Elements',
    'slug': 'frequency-of-elements',
    'description': 'Find the frequency of each element in a list.',
    'difficulty': 'Medium',
    'category': 'Dictionary',
    'input_format': '[1, 2, 2, 3, 3, 3]',
    'output_format': '{1: 1, 2: 2, 3: 3}',
    'constraints': 'List length ≤ 10^5',
    'sample_input': '[1, 2, 2, 3, 3, 3]',
    'sample_output': '{1: 1, 2: 2, 3: 3}',
    'expected_output': '{1: 1, 2: 2, 3: 3}',
    'time_limit': 1000,
    'memory_limit': 64
},{
    'title': 'Remove Duplicates Using Set',
    'slug': 'remove-duplicates-set',
    'description': 'Remove duplicates from a list using a set.',
    'difficulty': 'Medium',
    'category': 'Set',
    'input_format': '[1, 2, 2, 3, 4, 4, 5]',
    'output_format': '[1, 2, 3, 4, 5]',
    'constraints': 'List length ≤ 10^5',
    'sample_input': '[1, 2, 2, 3, 4, 4, 5]',
    'sample_output': '[1, 2, 3, 4, 5]',
    'expected_output': '[1, 2, 3, 4, 5]',
    'time_limit': 1000,
    'memory_limit': 64
},
{
    'title': 'Longest Substring Without Repeating Characters',
    'slug': 'longest-substring-no-repeat',
    'description': 'Find the length of the longest substring without repeating characters.',
    'difficulty': 'Medium',
    'category': 'Dictionary & While Loop',
    'input_format': '"abcabcbb"',
    'output_format': '3',
    'constraints': 'String length ≤ 10^5',
    'sample_input': '"abcabcbb"',
    'sample_output': '3',
    'expected_output': '3',
    'time_limit': 1000,
    'memory_limit': 64
},
{
    'title': 'Sum Until Zero',
    'slug': 'sum-until-zero',
    'description': 'Keep taking input numbers until 0 is entered, then return the sum.',
    'difficulty': 'Medium',
    'category': 'While Loop',
    'input_format': '5, 3, 0',
    'output_format': '8',
    'constraints': 'Numbers ≤ 10^5',
    'sample_input': '5, 3, 0',
    'sample_output': '8',
    'expected_output': '8',
    'time_limit': 1000,
    'memory_limit': 64
},
{
    'title': 'Dictionary Key-Value Swap',
    'slug': 'dict-key-value-swap',
    'description': 'Swap keys and values in a dictionary.',
    'difficulty': 'Medium',
    'category': 'Dictionary',
    'input_format': '{"a": 1, "b": 2, "c": 3}',
    'output_format': '{1: "a", 2: "b", 3: "c"}',
    'constraints': 'Dictionary size ≤ 10^5',
    'sample_input': '{"a": 1, "b": 2, "c": 3}',
    'sample_output': '{1: "a", 2: "b", 3: "c"}',
    'expected_output': '{1: "a", 2: "b", 3: "c"}',
    'time_limit': 1000,
    'memory_limit': 64
},

]




import re

def clean_sample_input(sample_input):
    # Remove surrounding quotes for strings
    sample_input = re.sub(r'^"|"$', '', sample_input.strip())
    # Convert [1, 2, 3] or ["a", "b", "c"] to '1 2 3' or 'a b c'
    if sample_input.startswith('[') and sample_input.endswith(']'):
        # Remove outer brackets
        sample_input = sample_input[1:-1]
        # Remove inner brackets for matrices
        sample_input = sample_input.replace('],[', '\n').replace('[', '').replace(']', '')
        # Remove quotes and extra spaces
        sample_input = sample_input.replace('"', '').replace("'", '').replace(',', ' ')
        # Collapse multiple spaces
        sample_input = re.sub(r'\s+', ' ', sample_input)
        # For matrices, restore newlines
        sample_input = sample_input.replace(' \n ', '\n').replace(' \n', '\n').replace('\n ', '\n')
    # Remove quotes from each line
    sample_input = '\n'.join([line.replace('"', '').replace("'", '') for line in sample_input.split('\n')])
    return sample_input.strip()

# Example usage:
sample_inputs = [
    '[1, 2, 3, 4]',
    '[[1,2],[3,4]]',
    '"hello"\n"world"',
    '[["A","B","C"],["D","E","F"]]',
    '[{"name": "Shirt", "price": 20}, {"name": "Jeans", "price": 50}]'
]
for s in sample_inputs:
    print('Before:', s)
    print('After:', clean_sample_input(s))
    print('---')
 

 
# Step 1: Remove duplicates by slug (keep first occurrence)
unique_slugs = set()
filtered_problem_data = []
for prob in problem_data:
    if prob['slug'] not in unique_slugs:
        filtered_problem_data.append(prob)
        unique_slugs.add(prob['slug'])

# Step 2: Insert filtered problems into the database
for prob in filtered_problem_data:
    prob['sample_input'] = clean_sample_input(prob['sample_input'])  # <-- Add this line
    problem, created = Problem.objects.get_or_create(
        slug=prob['slug'],
        defaults=prob
    )
    if created:
        print(f"✅ Created problem: {problem.title}")

# Step 3: Final Summary Output
print("\n Sample data creation completed!")
print(f"Total problems in database: {Problem.objects.count()}")
print("\n Admin user created with credentials:")
print("   Username: admin")
print("   Password: admin123")
print("\n You can now start the development server!")


if __name__ == '__main__':
    create_sample_data()