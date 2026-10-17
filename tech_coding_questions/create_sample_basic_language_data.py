#!/usr/bin/env python
import os
import sys
import django
import re
from django.utils import timezone

# Ensure project root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'techphile_exams.settings')
django.setup()

from django.contrib.auth.models import User
from coding.models import Problem, UserProfile

from django.utils import timezone
import time

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

    # Create sample problems in reverse order (last one first)
    base_time = timezone.now()
    
    # Process problems in reverse order
    for i, prob in enumerate(reversed(problem_data)):
        # Clean sample input
        prob['sample_input'] = clean_sample_input(prob['sample_input'])
        
        # Set creation time (newest first)
        prob['created_at'] = base_time - timezone.timedelta(minutes=i)
        
        problem, created = Problem.objects.get_or_create(
            slug=prob['slug'],
            defaults=prob
        )
        if created:
            print(f"✅ Created problem: {problem.title} (created at: {prob['created_at']})")
    
    print("\nSample data creation completed!")
    print(f"Total problems in database: {Problem.objects.count()}")
    print("\nProblems created in descending order (newest first).")
    # Create sample problems

problem_data = [




    {
        'title': 'Simple Interest Calculator',
        'slug': 'simple-interest',
        'description': 'Calculate simple interest given principal, rate, and time.',
        'difficulty': 'Easy',
        'category': 'Math',
        'input_format': 'Three space-separated numbers: principal, rate, time',
        'output_format': 'Simple interest value',
        'constraints': 'All values positive',
        'sample_input': '1000 5 2',
        'sample_output': '100.0',
        'expected_output': '100.0',
        'time_limit': 1000,
        'memory_limit': 64
    },

        {
        'title': 'Count Even Numbers',
        'slug': 'count-even',
        'description': 'Count how many even numbers are in an array',
        'difficulty': 'Easy',
        'category': 'Array',
        'input_format': 'Array of integers',
        'output_format': 'Count of even numbers',
        'constraints': '1 ≤ array length ≤ 1000',
        'sample_input': '[1, 2, 3, 4, 5, 6]',
        'sample_output': '3',
        'expected_output': '3',
        'time_limit': 1000,
        'memory_limit': 64
    },
      {
        'title': 'Count Digits in Number',
        'slug': 'count-digits',
        'description': 'Count the number of digits in a number',
        'difficulty': 'Easy',
        'category': 'Math',
        'input_format': 'Single integer n',
        'output_format': 'Number of digits',
        'constraints': '-10^9 ≤ n ≤ 10^9',
        'sample_input': '12345',
        'sample_output': '5',
        'expected_output': '5',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Sum of Digits',
        'slug': 'sum-digits',
        'description': 'Calculate sum of all digits in a number',
        'difficulty': 'Easy',
        'category': 'Math',
        'input_format': 'Single integer n',
        'output_format': 'Sum of digits',
        'constraints': '-10^9 ≤ n ≤ 10^9',
        'sample_input': '123',
        'sample_output': '6',
        'expected_output': '6',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Reverse a String',
        'slug': 'reverse-string-basic',
        'description': 'Given a string, print it in reverse order.',
        'difficulty': 'Easy',
        'category': 'String',
        'input_format': 'A single string',
        'output_format': 'The reversed string',
        'constraints': '1 ≤ length ≤ 100',
        'sample_input': 'hello',
        'sample_output': 'olleh',
        'expected_output': 'olleh',
        'time_limit': 1000,
        'memory_limit': 64
    },

    {
        'title': 'Count Vowels',
        'slug': 'count-vowels-basic',
        'description': 'Count the number of vowels in a given string.',
        'difficulty': 'Easy',
        'category': 'String',
        'input_format': 'A single string',
        'output_format': 'Number of vowels',
        'constraints': '1 ≤ length ≤ 100',
        'sample_input': 'apple',
        'sample_output': '2',
        'expected_output': '2',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Fahrenheit to Celsius',
        'slug': 'fahrenheit-to-celsius',
        'description': 'Convert temperature from Fahrenheit to Celsius.',
        'difficulty': 'Easy',
        'category': 'Math',
        'input_format': 'A single integer (Fahrenheit)',
        'output_format': 'Celsius value rounded to 2 decimal places',
        'constraints': '-1000 ≤ F ≤ 1000',
        'sample_input': '98',
        'sample_output': '36.67',
        'expected_output': '36.67',
        'time_limit': 1000,
        'memory_limit': 64
    },
        {
        'title': 'Swap Two Numbers',
        'slug': 'swap-two-numbers',
        'description': 'Swap the values of two variables and print them.',
        'difficulty': 'Easy',
        'category': 'Basic',
        'input_format': 'Two space-separated integers',
        'output_format': 'The swapped values, space-separated',
        'constraints': '-1000 ≤ numbers ≤ 1000',
        'sample_input': '4 9',
        'sample_output': '9 4',
        'expected_output': '9 4',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Area of a Circle',
        'slug': 'area-of-circle',
        'description': 'Given the radius, calculate the area of a circle (use π = 3.14).',
        'difficulty': 'Easy',
        'category': 'Math',
        'input_format': 'A single integer (radius)',
        'output_format': 'Area of the circle (rounded to 2 decimal places)',
        'constraints': 'radius > 0',
        'sample_input': '5',
        'sample_output': '78.50',
        'expected_output': '78.50',
        'time_limit': 1000,
        'memory_limit': 64
    },
        {
        'title': 'Find Average',
        'slug': 'find-average',
        'description': 'Calculate average of numbers in an array',
        'difficulty': 'Easy',
        'category': 'Array',
        'input_format': 'Array of integers',
        'output_format': 'Average (rounded to 2 decimal places)',
        'constraints': '1 ≤ array length ≤ 1000',
        'sample_input': '[10, 20, 30, 40]',
        'sample_output': '25.00',
        'expected_output': '25.00',
        'time_limit': 1000,
        'memory_limit': 64
    },
    
       {
        'title': 'Print Numbers from 1 to N',
        'slug': 'print-1-to-n',
        'description': 'Print all numbers from 1 to N',
        'difficulty': 'Easy',
        'category': 'Loops',
        'input_format': 'Single integer n',
        'output_format': 'Numbers from 1 to n separated by space',
        'constraints': '1 ≤ n ≤ 1000',
        'sample_input': '5',
        'sample_output': '1 2 3 4 5',
        'expected_output': '1 2 3 4 5',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Sum of First N Numbers',
        'slug': 'sum-first-n',
        'description': 'Calculate sum of numbers from 1 to N',
        'difficulty': 'Easy',
        'category': 'Math',
        'input_format': 'Single integer n',
        'output_format': 'Sum of numbers from 1 to n',
        'constraints': '1 ≤ n ≤ 10000',
        'sample_input': '10',
        'sample_output': '55',
        'expected_output': '55',
        'time_limit': 1000,
        'memory_limit': 64
    },
        {
        'title': 'Even or Odd',
        'slug': 'even-or-odd-basic',
        'description': 'Write a program to check if a given number is even or odd.',
        'difficulty': 'Easy',
        'category': 'Basic',
        'input_format': 'A single integer',
        'output_format': '"even" if the number is even, "odd" otherwise',
        'constraints': '-1000 ≤ n ≤ 1000',
        'sample_input': '7',
        'sample_output': 'odd',
        'expected_output': 'odd',
        'time_limit': 1000,
        'memory_limit': 64
    },
        {
        'title': 'Find the Maximum',
        'slug': 'find-the-maximum',
        'description': 'Given three numbers, print the largest one.',
        'difficulty': 'Easy',
        'category': 'Basic',
        'input_format': 'Three space-separated integers',
        'output_format': 'The largest integer',
        'constraints': '-1000 ≤ numbers ≤ 1000',
        'sample_input': '10 20 15',
        'sample_output': '20',
        'expected_output': '20',
        'time_limit': 1000,
        'memory_limit': 64
    },
            {
        'title': 'String Length',
        'slug': 'string-length',
        'description': 'Find the length of a string without using built-in functions',
        'difficulty': 'Very Easy',
        'category': 'String',
        'input_format': 'A string',
        'output_format': 'Length of string',
        'constraints': '1 ≤ string length ≤ 1000',
        'sample_input': '"Hello"',
        'sample_output': '5',
        'expected_output': '5',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Sum of Two Numbers',
        'slug': 'sum-of-two-numbers',
        'description': 'Write a program that takes two integers as input and prints their sum.',
        'difficulty': 'Easy',
        'category': 'Basic',
        'input_format': 'Two space-separated integers',
        'output_format': 'Sum of the two integers',
        'constraints': '-1000 ≤ a, b ≤ 1000',
        'sample_input': '3 5',
        'sample_output': '8',
        'expected_output': '8',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Print Hello World',
        'slug': 'print-hello-world',
        'description': 'Write a program to print "Hello, World!" to the output.',
        'difficulty': 'Easy',
        'category': 'Basic',
        'input_format': 'None',
        'output_format': 'Hello, World!',
        'constraints': 'None',
        'sample_input': '',
        'sample_output': 'Hello, World!',
        'expected_output': 'Hello, World!',
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