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
        'title': 'QuickSort Implementation',
        'slug': 'quicksort-implementation',
        'description': 'Implement the QuickSort algorithm to sort an array in ascending order',
        'difficulty': 'Medium',
        'category': 'Sorting',
        'input_format': '[a1, a2, ..., an] (array of integers)',
        'output_format': '[sorted array]',
        'constraints': '1 ≤ n ≤ 10^5, -10^9 ≤ ai ≤ 10^9',
        'sample_input': '[5, 2, 9, 1, 5, 6]',
        'sample_output': '[1, 2, 5, 5, 6, 9]',
        'expected_output': '[1, 2, 5, 5, 6, 9]',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Merge k Sorted Lists',
        'slug': 'merge-k-sorted-lists',
        'description': 'Merge k sorted linked lists into one sorted linked list',
        'difficulty': 'Hard',
        'category': 'Sorting',
        'input_format': '[[l1], [l2], ..., [lk]] (list of sorted arrays)',
        'output_format': '[merged sorted array]',
        'constraints': '0 ≤ k ≤ 10^4, total elements ≤ 10^4',
        'sample_input': '[[1,4,5],[1,3,4],[2,6]]',
        'sample_output': '[1,1,2,3,4,4,5,6]',
        'expected_output': '[1,1,2,3,4,4,5,6]',
        'time_limit': 1500,
        'memory_limit': 64
    },
    {
        'title': 'Binary Search Implementation',
        'slug': 'binary-search-implementation',
        'description': 'Implement binary search to find target in sorted array',
        'difficulty': 'Easy',
        'category': 'Searching',
        'input_format': '[a1, a2, ..., an] (sorted array), target',
        'output_format': 'index or -1 if not found',
        'constraints': '1 ≤ n ≤ 10^4, -10^4 ≤ ai ≤ 10^4',
        'sample_input': '[-1,0,3,5,9,12], 9',
        'sample_output': '4',
        'expected_output': '4',
        'time_limit': 500,
        'memory_limit': 64
    },
    {
        'title': 'Word Search (DFS)',
        'slug': 'word-search-dfs',
        'description': 'Given 2D board and word, find if word exists in the grid (DFS)',
        'difficulty': 'Medium',
        'category': 'Searching',
        'input_format': '[[c11,c12,...],...] (2D grid), word',
        'output_format': 'true/false',
        'constraints': 'm,n ≤ 6, word length ≤ 15',
        'sample_input': '[["A","B","C","E"],["S","F","C","S"],["A","D","E","E"]], "ABCCED"',
        'sample_output': 'true',
        'expected_output': 'true',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'N-Queens Problem',
        'slug': 'n-queens-problem',
        'description': 'Place N queens on N×N chessboard so no two queens threaten each other',
        'difficulty': 'Hard',
        'category': 'Recursion & Backtracking',
        'input_format': 'n (integer)',
        'output_format': 'All distinct solutions',
        'constraints': '1 ≤ n ≤ 9',
        'sample_input': '4',
        'sample_output': '[[".Q..","...Q","Q...","..Q."],["..Q.","Q...","...Q",".Q.."]]',
        'expected_output': '[[".Q..","...Q","Q...","..Q."],["..Q.","Q...","...Q",".Q.."]]',
        'time_limit': 2000,
        'memory_limit': 64
    },
    {
        'title': '0/1 Knapsack Problem',
        'slug': '01-knapsack',
        'description': 'Maximize value in knapsack without exceeding weight capacity',
        'difficulty': 'Hard',
        'category': 'Dynamic Programming',
        'input_format': 'weights[], values[], capacity',
        'output_format': 'maximum value',
        'constraints': '1 ≤ n ≤ 100, 1 ≤ capacity ≤ 10^4',
        'sample_input': '[1,2,3], [10,15,40], 5',
        'sample_output': '55',
        'expected_output': '55',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Coin Change (Greedy)',
        'slug': 'coin-change-greedy',
        'description': 'Find minimum coins needed for amount (canonical coin system)',
        'difficulty': 'Easy',
        'category': 'Greedy Algorithms',
        'input_format': 'coins[], amount',
        'output_format': 'minimum coins or -1',
        'constraints': '1 ≤ coins.length ≤ 10, coins sorted descending',
        'sample_input': '[25,10,5,1], 63',
        'sample_output': '6',
        'expected_output': '6',
        'time_limit': 500,
        'memory_limit': 64
    },
    {
        'title': 'Longest Substring Without Repeating Characters',
        'slug': 'longest-substring-no-repeat',
        'description': 'Find length of longest substring without repeating characters',
        'difficulty': 'Medium',
        'category': 'Sliding Window',
        'input_format': 's (string)',
        'output_format': 'integer',
        'constraints': '0 ≤ s.length ≤ 5×10^4',
        'sample_input': '"abcabcbb"',
        'sample_output': '3',
        'expected_output': '3',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Number of Islands (Union-Find)',
        'slug': 'number-of-islands-unionfind',
        'description': 'Count number of islands in 2D grid using Union-Find',
        'difficulty': 'Medium',
        'category': 'Union-Find',
        'input_format': '[[0 or 1, ...], ...] (2D grid)',
        'output_format': 'integer',
        'constraints': 'm,n ≤ 300',
        'sample_input': '[["1","1","0","0","0"],["1","1","0","0","0"],["0","0","1","0","0"],["0","0","0","1","1"]]',
        'sample_output': '3',
        'expected_output': '3',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Single Number (Bit Manipulation)',
        'slug': 'single-number-bit',
        'description': 'Find the single number in array where others appear twice (use XOR)',
        'difficulty': 'Easy',
        'category': 'Bit Manipulation',
        'input_format': '[a1, a2, ..., an]',
        'output_format': 'integer',
        'constraints': '1 ≤ n ≤ 3×10^4, n is odd',
        'sample_input': '[4,1,2,1,2]',
        'sample_output': '4',
        'expected_output': '4',
        'time_limit': 500,
        'memory_limit': 64
    },
    {
    'title': 'Sort Colors (Dutch Flag Problem)',
    'slug': 'sort-colors',
    'description': 'Sort an array of 0s, 1s, and 2s in-place using the Dutch National Flag algorithm.',
    'difficulty': 'Medium',
    'category': 'Sorting',
    'input_format': '[0, 1, 2, 0, 1, 2] (array of 0s, 1s, and 2s)',
    'output_format': '[sorted array]',
    'constraints': '1 ≤ n ≤ 300',
    'sample_input': '[2,0,2,1,1,0]',
    'sample_output': '[0,0,1,1,2,2]',
    'expected_output': '[0,0,1,1,2,2]',
    'time_limit': 1000,
    'memory_limit': 64
},{
    'title': 'Find Peak Element (Binary Search)',
    'slug': 'find-peak-element',
    'description': 'A peak element is greater than its neighbors. Find any peak in O(log n) time.',
    'difficulty': 'Medium',
    'category': 'Searching',
    'input_format': '[a1, a2, ..., an] (array where nums[i] ≠ nums[i+1])',
    'output_format': 'index of any peak',
    'constraints': '1 ≤ n ≤ 1000, -2^31 ≤ nums[i] ≤ 2^31-1',
    'sample_input': '[1,2,3,1]',
    'sample_output': '2',
    'expected_output': '2',
    'time_limit': 1000,
    'memory_limit': 64
},
{
    'title': 'Subsets (Backtracking)',
    'slug': 'subsets-backtracking',
    'description': 'Generate all possible subsets of a set (power set) using backtracking.',
    'difficulty': 'Medium',
    'category': 'Recursion & Backtracking',
    'input_format': '[a1, a2, ..., an] (array of unique integers)',
    'output_format': '[[], [a1], [a2], ..., [a1,a2,...,an]]',
    'constraints': '1 ≤ n ≤ 10',
    'sample_input': '[1,2,3]',
    'sample_output': '[[],[1],[2],[1,2],[3],[1,3],[2,3],[1,2,3]]',
    'expected_output': '[[],[1],[2],[1,2],[3],[1,3],[2,3],[1,2,3]]',
    'time_limit': 1000,
    'memory_limit': 64
},
{
    'title': 'Longest Common Subsequence (LCS)',
    'slug': 'longest-common-subsequence',
    'description': 'Find the length of the longest subsequence common to two strings.',
    'difficulty': 'Medium',
    'category': 'Dynamic Programming',
    'input_format': 'text1 (string), text2 (string)',
    'output_format': 'integer (length of LCS)',
    'constraints': '1 ≤ text.length ≤ 1000',
    'sample_input': '"abcde", "ace"',
    'sample_output': '3',
    'expected_output': '3',
    'time_limit': 1000,
    'memory_limit': 64
},
{
    'title': 'Jump Game II (Greedy)',
    'slug': 'jump-game-ii',
    'description': 'Find the minimum number of jumps to reach the end of the array.',
    'difficulty': 'Medium',
    'category': 'Greedy Algorithms',
    'input_format': '[a1, a2, ..., an] (array of non-negative integers)',
    'output_format': 'minimum jumps (integer)',
    'constraints': '1 ≤ n ≤ 10^4, 0 ≤ a[i] ≤ 1000',
    'sample_input': '[2,3,1,1,4]',
    'sample_output': '2',
    'expected_output': '2',
    'time_limit': 1000,
    'memory_limit': 64
},
{
    'title': 'Minimum Window Substring',
    'slug': 'minimum-window-substring',
    'description': 'Find the smallest substring of s containing all characters of t.',
    'difficulty': 'Hard',
    'category': 'Sliding Window',
    'input_format': 's (string), t (string)',
    'output_format': 'smallest substring (string)',
    'constraints': '1 ≤ s.length, t.length ≤ 10^5',
    'sample_input': '"ADOBECODEBANC", "ABC"',
    'sample_output': '"BANC"',
    'expected_output': '"BANC"',
    'time_limit': 1000,
    'memory_limit': 64
},
{
    'title': 'Redundant Connection',
    'slug': 'redundant-connection',
    'description': 'Find an edge that can be removed to make a tree (detect cycle in undirected graph).',
    'difficulty': 'Medium',
    'category': 'Union-Find',
    'input_format': '[[u1,v1], [u2,v2], ...] (edges of a graph)',
    'output_format': '[u, v] (edge to remove)',
    'constraints': '3 ≤ n ≤ 1000',
    'sample_input': '[[1,2],[1,3],[2,3]]',
    'sample_output': '[2,3]',
    'expected_output': '[2,3]',
    'time_limit': 1000,
    'memory_limit': 64
},
{
    'title': 'Count Set Bits (Hamming Weight)',
    'slug': 'count-set-bits',
    'description': 'Count the number of 1 bits in an unsigned integer (binary representation).',
    'difficulty': 'Easy',
    'category': 'Bit Manipulation',
    'input_format': 'n (unsigned integer)',
    'output_format': 'count (integer)',
    'constraints': '0 ≤ n ≤ 2^32 - 1',
    'sample_input': '11 (binary: 1011)',
    'sample_output': '3',
    'expected_output': '3',
    'time_limit': 500,
    'memory_limit': 64
},
{
    'title': 'Inversion Count (MergeSort)',
    'slug': 'inversion-count',
    'description': 'Count inversions in an array (how far it is from being sorted).',
    'difficulty': 'Hard',
    'category': 'Sorting',
    'input_format': '[a1, a2, ..., an] (array of integers)',
    'output_format': 'count (integer)',
    'constraints': '1 ≤ n ≤ 5×10^5',
    'sample_input': '[8, 4, 2, 1]',
    'sample_output': '6',
    'expected_output': '6',
    'time_limit': 2000,
    'memory_limit': 256
},
{
    'title': 'TSP with Bitmask DP',
    'slug': 'tsp-bitmask-dp',
    'description': 'Solve the Traveling Salesman Problem using DP with bitmasking.',
    'difficulty': 'Hard',
    'category': 'Dynamic Programming + Bit Manipulation',
    'input_format': '[[w11, w12, ...], ...] (n x n cost matrix)',
    'output_format': 'minimum cost (integer)',
    'constraints': '2 ≤ n ≤ 20',
    'sample_input': '[[0, 10, 15, 20], [10, 0, 35, 25], [15, 35, 0, 30], [20, 25, 30, 0]]',
    'sample_output': '80',
    'expected_output': '80',
    'time_limit': 3000,
    'memory_limit': 256
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