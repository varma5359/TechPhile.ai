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
        'title': 'Print Numbers from 1 to N',
        'slug': 'print-1-to-n',
        'description': 'Print all numbers from 1 to N',
        'difficulty': 'Very Easy',
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
        'difficulty': 'Very Easy',
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
        'difficulty': 'Very Easy',
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
        'title': 'Count Even Numbers',
        'slug': 'count-even',
        'description': 'Count how many even numbers are in an array',
        'difficulty': 'Very Easy',
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
        'difficulty': 'Very Easy',
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
        'difficulty': 'Very Easy',
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
        'title': 'Two Sum',
        'slug': 'two-sum',
        'description': 'Find indices of two numbers that add up to target value',
        'difficulty': 'Medium',
        'category': 'Arrays',
        'input_format': 'First line: space-separated array elements\nSecond line: target sum',
        'output_format': 'Indices of two numbers',
        'constraints': '2 ≤ array length ≤ 10^4\n-10^9 ≤ elements ≤ 10^9',
        'sample_input': '2 7 11 15\n9',
        'sample_output': '0 1',
        'expected_output': '0 1',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Container With Most Water',
        'slug': 'container-most-water',
        'description': 'Find two lines that form container with most water',
        'difficulty': 'Medium',
        'category': 'Arrays',
        'input_format': 'Space-separated array of heights',
        'output_format': 'Maximum area',
        'constraints': '2 ≤ array length ≤ 10^5',
        'sample_input': '1 8 6 2 5 4 8 3 7',
        'sample_output': '49',
        'expected_output': '49',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': '3Sum',
        'slug': 'three-sum',
        'description': 'Find all unique triplets that sum to zero',
        'difficulty': 'Medium',
        'category': 'Arrays',
        'input_format': 'Space-separated array elements',
        'output_format': 'List of triplets',
        'constraints': '0 ≤ array length ≤ 3000',
        'sample_input': '-1 0 1 2 -1 -4',
        'sample_output': '-1 -1 2\n-1 0 1',
        'expected_output': '-1 -1 2\n-1 0 1',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Next Permutation',
        'slug': 'next-permutation',
        'description': 'Rearrange numbers into lexicographically next greater permutation',
        'difficulty': 'Medium',
        'category': 'Arrays',
        'input_format': 'Space-separated array elements',
        'output_format': 'Next permutation',
        'constraints': '1 ≤ array length ≤ 100',
        'sample_input': '1 2 3',
        'sample_output': '1 3 2',
        'expected_output': '1 3 2',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Search in Rotated Sorted Array',
        'slug': 'search-rotated-sorted',
        'description': 'Search target in rotated sorted array',
        'difficulty': 'Medium',
        'category': 'Arrays',
        'input_format': 'First line: space-separated array elements\nSecond line: target',
        'output_format': 'Index of target or -1',
        'constraints': '1 ≤ array length ≤ 5000',
        'sample_input': '4 5 6 7 0 1 2\n0',
        'sample_output': '4',
        'expected_output': '4',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Maximum Subarray',
        'slug': 'maximum-subarray',
        'description': 'Find contiguous subarray with largest sum (Kadane\'s Algorithm)',
        'difficulty': 'Medium',
        'category': 'Arrays',
        'input_format': 'Space-separated array elements',
        'output_format': 'Maximum sum',
        'constraints': '1 ≤ array length ≤ 10^5',
        'sample_input': '-2 1 -3 4 -1 2 1 -5 4',
        'sample_output': '6',
        'expected_output': '6',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Product of Array Except Self',
        'slug': 'product-array-except-self',
        'description': 'Return array where output[i] = product of all elements except nums[i]',
        'difficulty': 'Medium',
        'category': 'Arrays',
        'input_format': 'Space-separated array elements',
        'output_format': 'Result array',
        'constraints': '2 ≤ array length ≤ 10^5',
        'sample_input': '1 2 3 4',
        'sample_output': '24 12 8 6',
        'expected_output': '24 12 8 6',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Find Minimum in Rotated Sorted Array',
        'slug': 'find-min-rotated-sorted',
        'description': 'Find minimum element in rotated sorted array',
        'difficulty': 'Medium',
        'category': 'Arrays',
        'input_format': 'Space-separated array elements',
        'output_format': 'Minimum element',
        'constraints': '1 ≤ array length ≤ 5000',
        'sample_input': '3 4 5 1 2',
        'sample_output': '1',
        'expected_output': '1',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Combination Sum',
        'slug': 'combination-sum',
        'description': 'Find all unique combinations that sum to target (candidates may be reused)',
        'difficulty': 'Medium',
        'category': 'Arrays',
        'input_format': 'First line: space-separated candidates\nSecond line: target',
        'output_format': 'All unique combinations',
        'constraints': '1 ≤ candidates length ≤ 30',
        'sample_input': '2 3 6 7\n7',
        'sample_output': '2 2 3\n7',
        'expected_output': '2 2 3\n7',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Jump Game',
        'slug': 'jump-game',
        'description': 'Determine if you can reach last index (nums[i] = max jump)',
        'difficulty': 'Medium',
        'category': 'Arrays',
        'input_format': 'Space-separated array elements',
        'output_format': 'true/false',
        'constraints': '1 ≤ array length ≤ 10^4',
        'sample_input': '2 3 1 1 4',
        'sample_output': 'true',
        'expected_output': 'true',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Merge Intervals',
        'slug': 'merge-intervals',
        'description': 'Merge all overlapping intervals',
        'difficulty': 'Medium',
        'category': 'Arrays',
        'input_format': 'List of intervals (e.g., "1 3 2 6 8 10 15 18")',
        'output_format': 'Merged intervals',
        'constraints': '1 ≤ intervals length ≤ 10^4',
        'sample_input': '1 3 2 6 8 10 15 18',
        'sample_output': '1 6\n8 10\n15 18',
        'expected_output': '1 6\n8 10\n15 18',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Rotate Image',
        'slug': 'rotate-image',
        'description': 'Rotate n x n matrix 90 degrees clockwise (in-place)',
        'difficulty': 'Medium',
        'category': 'Arrays',
        'input_format': 'n followed by n x n matrix elements row-wise',
        'output_format': 'Rotated matrix',
        'constraints': '1 ≤ n ≤ 20',
        'sample_input': '3\n1 2 3\n4 5 6\n7 8 9',
        'sample_output': '7 4 1\n8 5 2\n9 6 3',
        'expected_output': '7 4 1\n8 5 2\n9 6 3',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Spiral Matrix',
        'slug': 'spiral-matrix',
        'description': 'Return all elements in spiral order',
        'difficulty': 'Medium',
        'category': 'Arrays',
        'input_format': 'm n followed by m x n matrix elements row-wise',
        'output_format': 'Elements in spiral order',
        'constraints': '1 ≤ m, n ≤ 10',
        'sample_input': '3 3\n1 2 3\n4 5 6\n7 8 9',
        'sample_output': '1 2 3 6 9 8 7 4 5',
        'expected_output': '1 2 3 6 9 8 7 4 5',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Set Matrix Zeroes',
        'slug': 'set-matrix-zeroes',
        'description': 'If element is 0, set entire row and column to 0 (in-place)',
        'difficulty': 'Medium',
        'category': 'Arrays',
        'input_format': 'm n followed by m x n matrix elements row-wise',
        'output_format': 'Modified matrix',
        'constraints': '1 ≤ m, n ≤ 200',
        'sample_input': '3 3\n1 1 1\n1 0 1\n1 1 1',
        'sample_output': '1 0 1\n0 0 0\n1 0 1',
        'expected_output': '1 0 1\n0 0 0\n1 0 1',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Subarray Sum Equals K',
        'slug': 'subarray-sum-equals-k',
        'description': 'Count number of contiguous subarrays that sum to k',
        'difficulty': 'Medium',
        'category': 'Arrays',
        'input_format': 'First line: space-separated array elements\nSecond line: k',
        'output_format': 'Count of subarrays',
        'constraints': '1 ≤ array length ≤ 2 * 10^4',
        'sample_input': '1 1 1\n2',
        'sample_output': '2',
        'expected_output': '2',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Longest Consecutive Sequence',
        'slug': 'longest-consecutive-sequence',
        'description': 'Find length of longest consecutive elements sequence',
        'difficulty': 'Medium',
        'category': 'Arrays',
        'input_format': 'Space-separated array elements',
        'output_format': 'Length of sequence',
        'constraints': '0 ≤ array length ≤ 10^5',
        'sample_input': '100 4 200 1 3 2',
        'sample_output': '4',
        'expected_output': '4',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'First Missing Positive',
        'slug': 'first-missing-positive',
        'description': 'Find smallest missing positive integer',
        'difficulty': 'Hard',
        'category': 'Arrays',
        'input_format': 'Space-separated array elements',
        'output_format': 'First missing positive',
        'constraints': '1 ≤ array length ≤ 5 * 10^5',
        'sample_input': '3 4 -1 1',
        'sample_output': '2',
        'expected_output': '2',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Find the Duplicate Number',
        'slug': 'find-duplicate-number',
        'description': 'Find the duplicate number in array of n+1 integers (1 to n)',
        'difficulty': 'Medium',
        'category': 'Arrays',
        'input_format': 'Space-separated array elements',
        'output_format': 'Duplicate number',
        'constraints': '2 ≤ array length ≤ 3 * 10^4',
        'sample_input': '1 3 4 2 2',
        'sample_output': '2',
        'expected_output': '2',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Insert Delete GetRandom O(1)',
        'slug': 'insert-delete-getrandom',
        'description': 'Design data structure supporting O(1) insert, delete, getRandom',
        'difficulty': 'Medium',
        'category': 'Arrays',
        'input_format': 'Series of operations (insert, remove, getRandom)',
        'output_format': 'Results of operations',
        'constraints': 'At most 2 * 10^5 operations',
        'sample_input': 'insert(1), remove(2), insert(2), getRandom()',
        'sample_output': 'true, false, true, 1 or 2',
        'expected_output': 'true, false, true, 1 or 2',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Task Scheduler',
        'slug': 'task-scheduler',
        'description': 'Find least number of intervals to complete tasks with cooldown',
        'difficulty': 'Medium',
        'category': 'Arrays',
        'input_format': 'First line: space-separated tasks (A-Z)\nSecond line: cooldown n',
        'output_format': 'Minimum intervals',
        'constraints': '1 ≤ tasks length ≤ 10^4',
        'sample_input': 'A A A B B B\n2',
        'sample_output': '8',
        'expected_output': '8',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Trapping Rain Water',
        'slug': 'trapping-rain-water',
        'description': 'Calculate how much water can be trapped between elevation bars',
        'difficulty': 'Hard',
        'category': 'Arrays',
        'input_format': 'Space-separated array of non-negative integers',
        'output_format': 'Total trapped water',
        'constraints': '1 ≤ height.length ≤ 2 * 10^4',
        'sample_input': '0 1 0 2 1 0 1 3 2 1 2 1',
        'sample_output': '6',
        'expected_output': '6',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Median of Two Sorted Arrays',
        'slug': 'median-two-sorted-arrays',
        'description': 'Find median of two sorted arrays in O(log(min(m,n))) time',
        'difficulty': 'Hard',
        'category': 'Arrays',
        'input_format': 'First line: space-separated array1\nSecond line: space-separated array2',
        'output_format': 'Median value',
        'constraints': '0 ≤ nums1.length, nums2.length ≤ 1000',
        'sample_input': '1 3\n2',
        'sample_output': '2.0',
        'expected_output': '2.0',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Sliding Window Maximum',
        'slug': 'sliding-window-maximum',
        'description': 'Find max in each sliding window of size k (O(n) solution)',
        'difficulty': 'Hard',
        'category': 'Arrays',
        'input_format': 'First line: space-separated array\nSecond line: window size k',
        'output_format': 'Array of maximums',
        'constraints': '1 ≤ nums.length ≤ 10^5',
        'sample_input': '1 3 -1 -3 5 3 6 7\n3',
        'sample_output': '3 3 5 5 6 7',
        'expected_output': '3 3 5 5 6 7',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Minimum Window Substring',
        'slug': 'minimum-window-substring',
        'description': 'Find smallest substring containing all characters of pattern',
        'difficulty': 'Hard',
        'category': 'Arrays',
        'input_format': 'First line: string S\nSecond line: string T',
        'output_format': 'Minimum window substring',
        'constraints': '1 ≤ s.length, t.length ≤ 10^5',
        'sample_input': 'ADOBECODEBANC\nABC',
        'sample_output': 'BANC',
        'expected_output': 'BANC',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Largest Rectangle in Histogram',
        'slug': 'largest-rectangle-histogram',
        'description': 'Find largest rectangular area under histogram',
        'difficulty': 'Hard',
        'category': 'Arrays',
        'input_format': 'Space-separated array of histogram heights',
        'output_format': 'Maximum area',
        'constraints': '1 ≤ heights.length ≤ 10^5',
        'sample_input': '2 1 5 6 2 3',
        'sample_output': '10',
        'expected_output': '10',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Merge k Sorted Lists',
        'slug': 'merge-k-sorted-lists',
        'description': 'Merge k sorted arrays into one sorted array',
        'difficulty': 'Hard',
        'category': 'Arrays',
        'input_format': 'k followed by k sorted arrays (space-separated)',
        'output_format': 'Merged sorted array',
        'constraints': 'k == arrays.length\n0 ≤ k ≤ 10^4',
        'sample_input': '3\n1 4 5\n1 3 4\n2 6',
        'sample_output': '1 1 2 3 4 4 5 6',
        'expected_output': '1 1 2 3 4 4 5 6',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Count of Smaller Numbers After Self',
        'slug': 'count-smaller-after-self',
        'description': 'Count how many elements to the right are smaller than current element',
        'difficulty': 'Hard',
        'category': 'Arrays',
        'input_format': 'Space-separated array elements',
        'output_format': 'Counts for each element',
        'constraints': '1 ≤ nums.length ≤ 10^5',
        'sample_input': '5 2 6 1',
        'sample_output': '2 1 1 0',
        'expected_output': '2 1 1 0',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Maximum Sum Circular Subarray',
        'slug': 'max-sum-circular-subarray',
        'description': 'Find maximum sum subarray in circular array',
        'difficulty': 'Medium',
        'category': 'Arrays',
        'input_format': 'Space-separated array elements',
        'output_format': 'Maximum sum',
        'constraints': '1 ≤ nums.length ≤ 3 * 10^4',
        'sample_input': '5 -3 5',
        'sample_output': '10',
        'expected_output': '10',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Longest Increasing Subsequence',
        'slug': 'longest-increasing-subsequence',
        'description': 'Find length of longest strictly increasing subsequence',
        'difficulty': 'Medium',
        'category': 'Arrays',
        'input_format': 'Space-separated array elements',
        'output_format': 'Length of LIS',
        'constraints': '1 ≤ nums.length ≤ 2500',
        'sample_input': '10 9 2 5 3 7 101 18',
        'sample_output': '4',
        'expected_output': '4',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Russian Doll Envelopes',
        'slug': 'russian-doll-envelopes',
        'description': 'Find maximum envelopes you can stack (one inside another)',
        'difficulty': 'Hard',
        'category': 'Arrays',
        'input_format': 'Pairs of width,height (space-separated)',
        'output_format': 'Maximum stack size',
        'constraints': '1 ≤ envelopes.length ≤ 10^5',
        'sample_input': '5 4 6 4 6 7 2 3',
        'sample_output': '3',
        'expected_output': '3',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Find K Closest Elements',
        'slug': 'find-k-closest-elements',
        'description': 'Find k closest elements to target in sorted array',
        'difficulty': 'Medium',
        'category': 'Arrays',
        'input_format': 'First line: space-separated sorted array\nSecond line: k and x (target)',
        'output_format': 'k closest elements',
        'constraints': '1 ≤ k ≤ arr.length ≤ 10^4',
        'sample_input': '1 2 3 4 5\n4 3',
        'sample_output': '1 2 3 4',
        'expected_output': '1 2 3 4',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Subarray Sums Divisible by K',
        'slug': 'subarray-sums-divisible-k',
        'description': 'Count subarrays where sum is divisible by k',
        'difficulty': 'Medium',
        'category': 'Arrays',
        'input_format': 'First line: space-separated array\nSecond line: k',
        'output_format': 'Count of subarrays',
        'constraints': '1 ≤ nums.length ≤ 3 * 10^4',
        'sample_input': '4 5 0 -2 -3 1\n5',
        'sample_output': '7',
        'expected_output': '7',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Continuous Subarray Sum',
        'slug': 'continuous-subarray-sum',
        'description': 'Check if array has continuous subarray of size ≥ 2 with sum multiple of k',
        'difficulty': 'Medium',
        'category': 'Arrays',
        'input_format': 'First line: space-separated array\nSecond line: k',
        'output_format': 'true/false',
        'constraints': '1 ≤ nums.length ≤ 10^5',
        'sample_input': '23 2 4 6 7\n6',
        'sample_output': 'true',
        'expected_output': 'true',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Kth Largest Element in Array',
        'slug': 'kth-largest-element',
        'description': 'Find kth largest element in unsorted array (O(n) solution)',
        'difficulty': 'Medium',
        'category': 'Arrays',
        'input_format': 'First line: space-separated array\nSecond line: k',
        'output_format': 'Kth largest element',
        'constraints': '1 ≤ k ≤ nums.length ≤ 10^4',
        'sample_input': '3 2 1 5 6 4\n2',
        'sample_output': '5',
        'expected_output': '5',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Wiggle Sort',
        'slug': 'wiggle-sort',
        'description': 'Reorder array so nums[0] ≤ nums[1] ≥ nums[2] ≤ nums[3]... (in-place)',
        'difficulty': 'Medium',
        'category': 'Arrays',
        'input_format': 'Space-separated array elements',
        'output_format': 'Wiggle-sorted array',
        'constraints': '1 ≤ nums.length ≤ 5 * 10^4',
        'sample_input': '3 5 2 1 6 4',
        'sample_output': '3 5 1 6 2 4',
        'expected_output': '3 5 1 6 2 4',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Find Peak Element II',
        'slug': 'find-peak-element-ii',
        'description': 'Find peak element in 2D array (greater than all neighbors)',
        'difficulty': 'Hard',
        'category': 'Arrays',
        'input_format': 'm n followed by m x n matrix elements row-wise',
        'output_format': 'Coordinates of peak element',
        'constraints': '1 ≤ m, n ≤ 500',
        'sample_input': '3 3\n1 4 3\n6 5 2\n7 8 9',
        'sample_output': '1 0',
        'expected_output': '1 0',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Split Array Largest Sum',
        'slug': 'split-array-largest-sum',
        'description': 'Minimize largest sum when splitting array into m subarrays',
        'difficulty': 'Hard',
        'category': 'Arrays',
        'input_format': 'First line: space-separated array\nSecond line: m',
        'output_format': 'Minimized largest sum',
        'constraints': '1 ≤ m ≤ nums.length ≤ 1000',
        'sample_input': '7 2 5 10 8\n2',
        'sample_output': '18',
        'expected_output': '18',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Maximum Gap',
        'slug': 'maximum-gap',
        'description': 'Find maximum difference between successive elements in sorted form (O(n) time/space)',
        'difficulty': 'Hard',
        'category': 'Arrays',
        'input_format': 'Space-separated array elements',
        'output_format': 'Maximum gap',
        'constraints': '1 ≤ nums.length ≤ 10^5',
        'sample_input': '3 6 9 1',
        'sample_output': '3',
        'expected_output': '3',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Shortest Unsorted Continuous Subarray',
        'slug': 'shortest-unsorted-subarray',
        'description': 'Find shortest subarray that if sorted would make entire array sorted',
        'difficulty': 'Medium',
        'category': 'Arrays',
        'input_format': 'Space-separated array elements',
        'output_format': 'Length of shortest subarray',
        'constraints': '1 ≤ nums.length ≤ 10^4',
        'sample_input': '2 6 4 8 10 9 15',
        'sample_output': '5',
        'expected_output': '5',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Circular Array Loop',
        'slug': 'circular-array-loop',
        'description': 'Detect if there is a cycle in circular array (forward/backward moves)',
        'difficulty': 'Medium',
        'category': 'Arrays',
        'input_format': 'Space-separated array elements',
        'output_format': 'true/false',
        'constraints': '1 ≤ nums.length ≤ 5000',
        'sample_input': '2 -1 1 2 2',
        'sample_output': 'true',
        'expected_output': 'true',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Best Time to Buy/Sell Stock with Cooldown',
        'slug': 'best-time-stock-cooldown',
        'description': 'Maximize profit with 1 day cooldown after sell',
        'difficulty': 'Medium',
        'category': 'Arrays',
        'input_format': 'Space-separated array of prices',
        'output_format': 'Maximum profit',
        'constraints': '1 ≤ prices.length ≤ 5000',
        'sample_input': '1 2 3 0 2',
        'sample_output': '3',
        'expected_output': '3',
        'time_limit': 1000,
        'memory_limit': 64
    }



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