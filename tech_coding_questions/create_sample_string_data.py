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
        'title': 'String Concatenation',
        'slug': 'string-concatenation',
        'description': 'Combine two strings into one',
        'difficulty': 'Very Easy',
        'category': 'String',
        'input_format': 'Two strings str1 and str2',
        'output_format': 'Combined string',
        'constraints': '1 ≤ str1.length, str2.length ≤ 100',
        'sample_input': '"Hello"\n"World"',
        'sample_output': '"HelloWorld"',
        'expected_output': '"HelloWorld"',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'String Length',
        'slug': 'string-length',
        'description': 'Find the length of a string',
        'difficulty': 'Very Easy',
        'category': 'String',
        'input_format': 'A string',
        'output_format': 'Length of string',
        'constraints': '1 ≤ string.length ≤ 1000',
        'sample_input': '"Hello"',
        'sample_output': '5',
        'expected_output': '5',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Character at Position',
        'slug': 'char-at-position',
        'description': 'Get the character at a specific position in a string',
        'difficulty': 'Very Easy',
        'category': 'String',
        'input_format': 'String and integer position',
        'output_format': 'Character at given position',
        'constraints': '0 ≤ position < string.length ≤ 100',
        'sample_input': '"Hello"\n1',
        'sample_output': '"e"',
        'expected_output': '"e"',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Count Vowels',
        'slug': 'count-vowels',
        'description': 'Count the number of vowels in a string',
        'difficulty': 'Easy',
        'category': 'String',
        'input_format': 'A string',
        'output_format': 'Number of vowels (a,e,i,o,u)',
        'constraints': '1 ≤ string.length ≤ 1000',
        'sample_input': '"Hello World"',
        'sample_output': '3',
        'expected_output': '3',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'String Reversal',
        'slug': 'string-reverse',
        'description': 'Reverse a given string',
        'difficulty': 'Easy',
        'category': 'String',
        'input_format': 'A string',
        'output_format': 'Reversed string',
        'constraints': '1 ≤ string.length ≤ 1000',
        'sample_input': '"hello"',
        'sample_output': '"olleh"',
        'expected_output': '"olleh"',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Check Palindrome',
        'slug': 'check-palindrome',
        'description': 'Determine if a string reads the same backward as forward',
        'difficulty': 'Easy',
        'category': 'String',
        'input_format': 'A string',
        'output_format': '"Palindrome" or "Not Palindrome"',
        'constraints': '1 ≤ string.length ≤ 1000',
        'sample_input': '"madam"',
        'sample_output': 'Palindrome',
        'expected_output': 'Palindrome',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Count Words',
        'slug': 'count-words',
        'description': 'Count the number of words in a string',
        'difficulty': 'Easy',
        'category': 'String',
        'input_format': 'A string',
        'output_format': 'Number of words',
        'constraints': '1 ≤ string.length ≤ 1000',
        'sample_input': '"This is a test"',
        'sample_output': '4',
        'expected_output': '4',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Uppercase Conversion',
        'slug': 'uppercase-conversion',
        'description': 'Convert a string to uppercase',
        'difficulty': 'Very Easy',
        'category': 'String',
        'input_format': 'A string',
        'output_format': 'Uppercase string',
        'constraints': '1 ≤ string.length ≤ 1000',
        'sample_input': '"hello"',
        'sample_output': '"HELLO"',
        'expected_output': '"HELLO"',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Lowercase Conversion',
        'slug': 'lowercase-conversion',
        'description': 'Convert a string to lowercase',
        'difficulty': 'Very Easy',
        'category': 'String',
        'input_format': 'A string',
        'output_format': 'Lowercase string',
        'constraints': '1 ≤ string.length ≤ 1000',
        'sample_input': '"HELLO"',
        'sample_output': '"hello"',
        'expected_output': '"hello"',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Remove Spaces',
        'slug': 'remove-spaces',
        'description': 'Remove all spaces from a string',
        'difficulty': 'Easy',
        'category': 'String',
        'input_format': 'A string',
        'output_format': 'String without spaces',
        'constraints': '1 ≤ string.length ≤ 1000',
        'sample_input': '"H e l l o"',
        'sample_output': '"Hello"',
        'expected_output': '"Hello"',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Count Character',
        'slug': 'count-character',
        'description': 'Count how many times a character appears in a string',
        'difficulty': 'Easy',
        'category': 'String',
        'input_format': 'String and a character',
        'output_format': 'Count of character',
        'constraints': '1 ≤ string.length ≤ 1000',
        'sample_input': '"hello"\n"l"',
        'sample_output': '2',
        'expected_output': '2',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Replace Character',
        'slug': 'replace-character',
        'description': 'Replace all occurrences of a character in a string',
        'difficulty': 'Easy',
        'category': 'String',
        'input_format': 'String, old character, new character',
        'output_format': 'Modified string',
        'constraints': '1 ≤ string.length ≤ 1000',
        'sample_input': '"hello"\n"l"\n"x"',
        'sample_output': '"hexxo"',
        'expected_output': '"hexxo"',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Check Substring',
        'slug': 'check-substring',
        'description': 'Check if one string is a substring of another',
        'difficulty': 'Easy',
        'category': 'String',
        'input_format': 'Two strings str1 and str2',
        'output_format': '"Yes" or "No"',
        'constraints': '1 ≤ str1.length, str2.length ≤ 100',
        'sample_input': '"hello world"\n"world"',
        'sample_output': 'Yes',
        'expected_output': 'Yes',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'First Unique Character',
        'slug': 'first-unique-char',
        'description': 'Find the first non-repeating character in a string',
        'difficulty': 'Easy',
        'category': 'String',
        'input_format': 'A string',
        'output_format': 'First unique character or "_" if none',
        'constraints': '1 ≤ string.length ≤ 1000',
        'sample_input': '"hello"',
        'sample_output': '"h"',
        'expected_output': '"h"',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'String Comparison',
        'slug': 'string-comparison',
        'description': 'Compare two strings lexicographically',
        'difficulty': 'Very Easy',
        'category': 'String',
        'input_format': 'Two strings str1 and str2',
        'output_format': '"Equal", "First Greater", or "Second Greater"',
        'constraints': '1 ≤ str1.length, str2.length ≤ 100',
        'sample_input': '"apple"\n"banana"',
        'sample_output': 'Second Greater',
        'expected_output': 'Second Greater',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Trim Whitespace',
        'slug': 'trim-whitespace',
        'description': 'Remove leading and trailing whitespace from a string',
        'difficulty': 'Easy',
        'category': 'String',
        'input_format': 'A string',
        'output_format': 'Trimmed string',
        'constraints': '1 ≤ string.length ≤ 1000',
        'sample_input': '"   hello   "',
        'sample_output': '"hello"',
        'expected_output': '"hello"',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Count Lines',
        'slug': 'count-lines',
        'description': 'Count the number of lines in a multi-line string',
        'difficulty': 'Easy',
        'category': 'String',
        'input_format': 'Multi-line string',
        'output_format': 'Number of lines',
        'constraints': '1 ≤ string.length ≤ 1000',
        'sample_input': '"Line1\nLine2\nLine3"',
        'sample_output': '3',
        'expected_output': '3',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Repeat String',
        'slug': 'repeat-string',
        'description': 'Repeat a string n times',
        'difficulty': 'Very Easy',
        'category': 'String',
        'input_format': 'String and integer n',
        'output_format': 'Repeated string',
        'constraints': '1 ≤ string.length ≤ 100\n0 ≤ n ≤ 100',
        'sample_input': '"hi"\n3',
        'sample_output': '"hihihi"',
        'expected_output': '"hihihi"',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'String Starts With',
        'slug': 'string-starts-with',
        'description': 'Check if a string starts with a given prefix',
        'difficulty': 'Very Easy',
        'category': 'String',
        'input_format': 'String and prefix',
        'output_format': '"Yes" or "No"',
        'constraints': '1 ≤ string.length, prefix.length ≤ 100',
        'sample_input': '"hello"\n"he"',
        'sample_output': 'Yes',
        'expected_output': 'Yes',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'String Ends With',
        'slug': 'string-ends-with',
        'description': 'Check if a string ends with a given suffix',
        'difficulty': 'Very Easy',
        'category': 'String',
        'input_format': 'String and suffix',
        'output_format': '"Yes" or "No"',
        'constraints': '1 ≤ string.length, suffix.length ≤ 100',
        'sample_input': '"hello"\n"lo"',
        'sample_output': 'Yes',
        'expected_output': 'Yes',
        'time_limit': 1000,
        'memory_limit': 64
    },

    {
        'title': 'Longest Substring Without Repeating Characters',
        'slug': 'longest-substring-no-repeats',
        'description': 'Find the length of the longest substring without repeating characters',
        'difficulty': 'Medium',
        'category': 'String',
        'input_format': 'A string',
        'output_format': 'Integer length',
        'constraints': '0 ≤ s.length ≤ 5 * 10^4',
        'sample_input': '"abcabcbb"',
        'sample_output': '3',
        'expected_output': '3',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'String to Integer (atoi)',
        'slug': 'string-to-integer',
        'description': 'Implement the atoi function to convert string to integer',
        'difficulty': 'Medium',
        'category': 'String',
        'input_format': 'A string',
        'output_format': 'Converted integer',
        'constraints': '0 ≤ s.length ≤ 200',
        'sample_input': '"   -42"',
        'sample_output': '-42',
        'expected_output': '-42',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Longest Palindromic Substring',
        'slug': 'longest-palindromic-substring',
        'description': 'Find the longest palindromic substring in a string',
        'difficulty': 'Medium',
        'category': 'String',
        'input_format': 'A string',
        'output_format': 'Longest palindromic substring',
        'constraints': '1 ≤ s.length ≤ 1000',
        'sample_input': '"babad"',
        'sample_output': '"bab"',
        'expected_output': '"bab"',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Group Anagrams',
        'slug': 'group-anagrams',
        'description': 'Group strings that are anagrams together',
        'difficulty': 'Medium',
        'category': 'String',
        'input_format': 'List of strings',
        'output_format': 'List of grouped anagrams',
        'constraints': '1 ≤ strs.length ≤ 10^4',
        'sample_input': '["eat","tea","tan","ate","nat","bat"]',
        'sample_output': '[["eat","tea","ate"],["tan","nat"],["bat"]]',
        'expected_output': '[["eat","tea","ate"],["tan","nat"],["bat"]]',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Decode String',
        'slug': 'decode-string',
        'description': 'Decode a string encoded with k[encoded_string] pattern',
        'difficulty': 'Medium',
        'category': 'String',
        'input_format': 'Encoded string',
        'output_format': 'Decoded string',
        'constraints': '1 ≤ s.length ≤ 30',
        'sample_input': '"3[a]2[bc]"',
        'sample_output': '"aaabcbc"',
        'expected_output': '"aaabcbc"',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Find All Anagrams in a String',
        'slug': 'find-all-anagrams',
        'description': 'Find all start indices of p\'s anagrams in s',
        'difficulty': 'Medium',
        'category': 'String',
        'input_format': 'Strings s and p',
        'output_format': 'List of starting indices',
        'constraints': '1 ≤ s.length, p.length ≤ 3 * 10^4',
        'sample_input': '"cbaebabacd"\n"abc"',
        'sample_output': '[0, 6]',
        'expected_output': '[0, 6]',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Longest Repeating Character Replacement',
        'slug': 'character-replacement',
        'description': 'Find the length of the longest substring with same letters after k replacements',
        'difficulty': 'Medium',
        'category': 'String',
        'input_format': 'String s and integer k',
        'output_format': 'Maximum length',
        'constraints': '1 ≤ s.length ≤ 10^5',
        'sample_input': '"AABABBA"\n1',
        'sample_output': '4',
        'expected_output': '4',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Palindromic Substrings',
        'slug': 'palindromic-substrings',
        'description': 'Count how many palindromic substrings in a string',
        'difficulty': 'Medium',
        'category': 'String',
        'input_format': 'A string',
        'output_format': 'Count of palindromic substrings',
        'constraints': '1 ≤ s.length ≤ 1000',
        'sample_input': '"aaa"',
        'sample_output': '6',
        'expected_output': '6',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Minimum Window Substring',
        'slug': 'minimum-window-substring',
        'description': 'Find the minimum window in s containing all characters of t',
        'difficulty': 'Hard',
        'category': 'String',
        'input_format': 'Strings s and t',
        'output_format': 'Minimum window substring',
        'constraints': '1 ≤ s.length, t.length ≤ 10^5',
        'sample_input': '"ADOBECODEBANC"\n"ABC"',
        'sample_output': '"BANC"',
        'expected_output': '"BANC"',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Valid Parenthesis String',
        'slug': 'valid-parenthesis-string',
        'description': 'Check if a string with wildcards can be valid parentheses',
        'difficulty': 'Medium',
        'category': 'String',
        'input_format': 'A string containing (, ) and *',
        'output_format': 'true/false',
        'constraints': '1 ≤ s.length ≤ 100',
        'sample_input': '"(*))"',
        'sample_output': 'true',
        'expected_output': 'true',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Simplify Path',
        'slug': 'simplify-path',
        'description': 'Simplify a Unix-style file path',
        'difficulty': 'Medium',
        'category': 'String',
        'input_format': 'A string representing absolute path',
        'output_format': 'Simplified canonical path',
        'constraints': '1 ≤ path.length ≤ 3000',
        'sample_input': '"/a/./b/../../c/"',
        'sample_output': '"/c"',
        'expected_output': '"/c"',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Basic Calculator II',
        'slug': 'basic-calculator-ii',
        'description': 'Implement a basic calculator to evaluate simple expressions',
        'difficulty': 'Medium',
        'category': 'String',
        'input_format': 'A string expression',
        'output_format': 'Integer result',
        'constraints': '1 ≤ s.length ≤ 3 * 10^5',
        'sample_input': '"3+2*2"',
        'sample_output': '7',
        'expected_output': '7',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Integer to Roman',
        'slug': 'integer-to-roman',
        'description': 'Convert an integer to a Roman numeral',
        'difficulty': 'Medium',
        'category': 'String',
        'input_format': 'Integer num',
        'output_format': 'Roman numeral string',
        'constraints': '1 ≤ num ≤ 3999',
        'sample_input': '58',
        'sample_output': '"LVIII"',
        'expected_output': '"LVIII"',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Roman to Integer',
        'slug': 'roman-to-integer',
        'description': 'Convert a Roman numeral to an integer',
        'difficulty': 'Easy',
        'category': 'String',
        'input_format': 'Roman numeral string',
        'output_format': 'Converted integer',
        'constraints': '1 ≤ s.length ≤ 15',
        'sample_input': '"LVIII"',
        'sample_output': '58',
        'expected_output': '58',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Count and Say',
        'slug': 'count-and-say',
        'description': 'Generate the count-and-say sequence',
        'difficulty': 'Medium',
        'category': 'String',
        'input_format': 'Integer n',
        'output_format': 'nth term of count-and-say sequence',
        'constraints': '1 ≤ n ≤ 30',
        'sample_input': '4',
        'sample_output': '"1211"',
        'expected_output': '"1211"',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Reorganize String',
        'slug': 'reorganize-string',
        'description': 'Rearrange characters so no two adjacent are same',
        'difficulty': 'Medium',
        'category': 'String',
        'input_format': 'A string',
        'output_format': 'Reorganized string or empty if impossible',
        'constraints': '1 ≤ s.length ≤ 500',
        'sample_input': '"aab"',
        'sample_output': '"aba"',
        'expected_output': '"aba"',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Longest Happy Prefix',
        'slug': 'longest-happy-prefix',
        'description': 'Find the longest prefix which is also suffix',
        'difficulty': 'Hard',
        'category': 'String',
        'input_format': 'A string',
        'output_format': 'Longest happy prefix',
        'constraints': '1 ≤ s.length ≤ 10^5',
        'sample_input': '"level"',
        'sample_output': '"l"',
        'expected_output': '"l"',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Multiply Strings',
        'slug': 'multiply-strings',
        'description': 'Multiply two numbers represented as strings',
        'difficulty': 'Medium',
        'category': 'String',
        'input_format': 'Two strings num1 and num2',
        'output_format': 'Product as string',
        'constraints': '1 ≤ num1.length, num2.length ≤ 200',
        'sample_input': '"2"\n"3"',
        'sample_output': '"6"',
        'expected_output': '"6"',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Zigzag Conversion',
        'slug': 'zigzag-conversion',
        'description': 'Convert string to zigzag pattern and read row-wise',
        'difficulty': 'Medium',
        'category': 'String',
        'input_format': 'String s and integer numRows',
        'output_format': 'Converted string',
        'constraints': '1 ≤ s.length ≤ 1000',
        'sample_input': '"PAYPALISHIRING"\n3',
        'sample_output': '"PAHNAPLSIIGYIR"',
        'expected_output': '"PAHNAPLSIIGYIR"',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Find Kth Bit in Nth Binary String',
        'slug': 'find-kth-bit',
        'description': 'Find the kth bit in the nth binary string sequence',
        'difficulty': 'Medium',
        'category': 'String',
        'input_format': 'Integers n and k',
        'output_format': 'kth bit as character',
        'constraints': '1 ≤ n ≤ 20\n1 ≤ k ≤ 2^n - 1',
        'sample_input': '3\n1',
        'sample_output': '"0"',
        'expected_output': '"0"',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Shortest Way to Form String',
        'slug': 'shortest-way-to-form-string',
        'description': 'Find minimum subsequences of source needed to form target',
        'difficulty': 'Medium',
        'category': 'String',
        'input_format': 'Strings source and target',
        'output_format': 'Minimum number of subsequences',
        'constraints': '1 ≤ source.length, target.length ≤ 1000',
        'sample_input': '"abc"\n"abcbc"',
        'sample_output': '2',
        'expected_output': '2',
        'time_limit': 1000,
        'memory_limit': 64
    },
   
    {
        'title': 'Regular Expression Matching',
        'slug': 'regular-expression-matching',
        'description': 'Implement regular expression matching with support for "." and "*"',
        'difficulty': 'Hard',
        'category': 'String/DP',
        'input_format': 'String s and pattern p',
        'output_format': 'true/false',
        'constraints': '0 ≤ s.length ≤ 20\n0 ≤ p.length ≤ 30',
        'sample_input': '"aa"\n"a*"',
        'sample_output': 'true',
        'expected_output': 'true',
        'time_limit': 1000,
        'memory_limit': 256
    },
    {
        'title': 'Wildcard Matching',
        'slug': 'wildcard-matching',
        'description': 'Implement wildcard pattern matching with support for "?" and "*"',
        'difficulty': 'Hard',
        'category': 'String/DP',
        'input_format': 'String s and pattern p',
        'output_format': 'true/false',
        'constraints': '0 ≤ s.length, p.length ≤ 2000',
        'sample_input': '"adceb"\n"*a*b"',
        'sample_output': 'true',
        'expected_output': 'true',
        'time_limit': 1000,
        'memory_limit': 256
    },
    {
        'title': 'Minimum Window Subsequence',
        'slug': 'minimum-window-subsequence',
        'description': 'Find shortest substring of S that contains all characters of T in order',
        'difficulty': 'Hard',
        'category': 'String/DP',
        'input_format': 'Strings S and T',
        'output_format': 'Minimum window substring',
        'constraints': '1 ≤ S.length, T.length ≤ 10^4',
        'sample_input': '"abcdebdde"\n"bde"',
        'sample_output': '"bcde"',
        'expected_output': '"bcde"',
        'time_limit': 1000,
        'memory_limit': 256
    },
    {
        'title': 'Distinct Subsequences',
        'slug': 'distinct-subsequences',
        'description': 'Count the number of distinct subsequences of S that equal T',
        'difficulty': 'Hard',
        'category': 'String/DP',
        'input_format': 'Strings S and T',
        'output_format': 'Number of distinct subsequences',
        'constraints': '1 ≤ S.length, T.length ≤ 1000',
        'sample_input': '"rabbbit"\n"rabbit"',
        'sample_output': '3',
        'expected_output': '3',
        'time_limit': 1000,
        'memory_limit': 256
    },
    {
        'title': 'Longest Valid Parentheses',
        'slug': 'longest-valid-parentheses',
        'description': 'Find the length of the longest valid parentheses substring',
        'difficulty': 'Hard',
        'category': 'String/Stack',
        'input_format': 'String containing "(" and ")"',
        'output_format': 'Maximum length',
        'constraints': '0 ≤ s.length ≤ 3 * 10^4',
        'sample_input': '")()())"',
        'sample_output': '4',
        'expected_output': '4',
        'time_limit': 1000,
        'memory_limit': 256
    },
    {
        'title': 'Text Justification',
        'slug': 'text-justification',
        'description': 'Arrange words in lines with maxWidth, adding extra spaces as needed',
        'difficulty': 'Hard',
        'category': 'String',
        'input_format': 'List of words and integer maxWidth',
        'output_format': 'List of justified lines',
        'constraints': '1 ≤ words.length ≤ 300',
        'sample_input': '["This", "is", "an", "example", "of", "text", "justification."]\n16',
        'sample_output': '["This    is    an","example  of text","justification.  "]',
        'expected_output': '["This    is    an","example  of text","justification.  "]',
        'time_limit': 1000,
        'memory_limit': 256
    },
    {
        'title': 'Word Break II',
        'slug': 'word-break-ii',
        'description': 'Return all possible sentence constructions from dictionary words',
        'difficulty': 'Hard',
        'category': 'String/Backtracking',
        'input_format': 'String s and dictionary wordDict',
        'output_format': 'List of possible sentences',
        'constraints': '1 ≤ s.length ≤ 20',
        'sample_input': '"catsanddog"\n["cat","cats","and","sand","dog"]',
        'sample_output': '["cats and dog","cat sand dog"]',
        'expected_output': '["cats and dog","cat sand dog"]',
        'time_limit': 1000,
        'memory_limit': 256
    },
    {
        'title': 'Substring with Concatenation of All Words',
        'slug': 'substring-with-concatenation',
        'description': 'Find all starting indices of substrings that are concatenation of each word',
        'difficulty': 'Hard',
        'category': 'String/Hash Table',
        'input_format': 'String s and list of words',
        'output_format': 'List of starting indices',
        'constraints': '1 ≤ s.length ≤ 10^4',
        'sample_input': '"barfoothefoobarman"\n["foo","bar"]',
        'sample_output': '[0,9]',
        'expected_output': '[0,9]',
        'time_limit': 1000,
        'memory_limit': 256
    },
    {
        'title': 'Smallest Range Covering Elements from K Lists',
        'slug': 'smallest-range',
        'description': 'Find smallest range that includes at least one number from each of k lists',
        'difficulty': 'Hard',
        'category': 'String/Heap',
        'input_format': 'List of k sorted integer lists',
        'output_format': 'Smallest range [start, end]',
        'constraints': 'nums.length == k',
        'sample_input': '[[4,10,15,24,26],[0,9,12,20],[5,18,22,30]]',
        'sample_output': '[20,24]',
        'expected_output': '[20,24]',
        'time_limit': 1000,
        'memory_limit': 256
    },
    {
        'title': 'Longest Duplicate Substring',
        'slug': 'longest-duplicate-substring',
        'description': 'Find the longest substring that occurs at least twice in a string',
        'difficulty': 'Hard',
        'category': 'String/Binary Search',
        'input_format': 'String s',
        'output_format': 'Longest duplicate substring',
        'constraints': '2 ≤ s.length ≤ 3 * 10^4',
        'sample_input': '"banana"',
        'sample_output': '"ana"',
        'expected_output': '"ana"',
        'time_limit': 1000,
        'memory_limit': 256
    },
    {
        'title': 'Minimum Number of Operations to Make String Sorted',
        'slug': 'make-string-sorted',
        'description': 'Calculate operations needed to make string sorted (mod 10^9+7)',
        'difficulty': 'Hard',
        'category': 'String/Math',
        'input_format': 'String s',
        'output_format': 'Number of operations',
        'constraints': '1 ≤ s.length ≤ 3000',
        'sample_input': '"cba"',
        'sample_output': '5',
        'expected_output': '5',
        'time_limit': 1000,
        'memory_limit': 256
    },
    {
        'title': 'String Transforms Into Another String',
        'slug': 'string-transformation',
        'description': 'Determine if str1 can be transformed into str2 with character mappings',
        'difficulty': 'Hard',
        'category': 'String/Graph',
        'input_format': 'Strings str1 and str2',
        'output_format': 'true/false',
        'constraints': '1 ≤ str1.length, str2.length ≤ 10^5',
        'sample_input': '"aabcc"\n"ccdee"',
        'sample_output': 'true',
        'expected_output': 'true',
        'time_limit': 1000,
        'memory_limit': 256
    },
    {
        'title': 'Palindrome Pairs',
        'slug': 'palindrome-pairs',
        'description': 'Find all unique index pairs (i,j) where words[i]+words[j] is palindrome',
        'difficulty': 'Hard',
        'category': 'String/Hash Table',
        'input_format': 'List of unique words',
        'output_format': 'List of index pairs',
        'constraints': '1 ≤ words.length ≤ 5000',
        'sample_input': '["abcd","dcba","lls","s","sssll"]',
        'sample_output': '[[0,1],[1,0],[3,2],[2,4]]',
        'expected_output': '[[0,1],[1,0],[3,2],[2,4]]',
        'time_limit': 1000,
        'memory_limit': 256
    },
    {
        'title': 'Count Unique Characters of All Substrings',
        'slug': 'count-unique-chars',
        'description': 'Sum counts of unique characters in all substrings',
        'difficulty': 'Hard',
        'category': 'String/Dynamic Programming',
        'input_format': 'String s',
        'output_format': 'Sum of counts',
        'constraints': '1 ≤ s.length ≤ 10^5',
        'sample_input': '"ABC"',
        'sample_output': '10',
        'expected_output': '10',
        'time_limit': 1000,
        'memory_limit': 256
    },
    {
        'title': 'Minimum Insertions to Balance a Parentheses String',
        'slug': 'minimum-insertions-balance',
        'description': 'Calculate minimum insertions needed to balance parentheses',
        'difficulty': 'Hard',
        'category': 'String/Stack',
        'input_format': 'String s containing "(" and ")"',
        'output_format': 'Minimum insertions',
        'constraints': '1 ≤ s.length ≤ 10^5',
        'sample_input': '"(()))"',
        'sample_output': '1',
        'expected_output': '1',
        'time_limit': 1000,
        'memory_limit': 256
    },
    {
        'title': 'Longest Chunked Palindrome Decomposition',
        'slug': 'longest-chunked-palindrome',
        'description': 'Split text into maximum parts where parts read same forwards and backwards',
        'difficulty': 'Hard',
        'category': 'String/Greedy',
        'input_format': 'String text',
        'output_format': 'Maximum number of parts',
        'constraints': '1 ≤ text.length ≤ 1000',
        'sample_input': '"ghiabcdefhelloadamhelloabcdefghi"',
        'sample_output': '7',
        'expected_output': '7',
        'time_limit': 1000,
        'memory_limit': 256
    },
    {
        'title': 'Shortest Palindrome',
        'slug': 'shortest-palindrome',
        'description': 'Add characters in front to make shortest palindrome',
        'difficulty': 'Hard',
        'category': 'String/KMP',
        'input_format': 'String s',
        'output_format': 'Shortest palindrome',
        'constraints': '0 ≤ s.length ≤ 5 * 10^4',
        'sample_input': '"aacecaaa"',
        'sample_output': '"aaacecaaa"',
        'expected_output': '"aaacecaaa"',
        'time_limit': 1000,
        'memory_limit': 256
    },
    {
        'title': 'Find All Good Strings',
        'slug': 'find-all-good-strings',
        'description': 'Count strings of length n between s1 and s2 without evil as substring',
        'difficulty': 'Hard',
        'category': 'String/DP',
        'input_format': 'Integer n, strings s1, s2, and evil',
        'output_format': 'Count modulo 10^9+7',
        'constraints': 's1.length == s2.length == n',
        'sample_input': '2\n"aa"\n"da"\n"b"',
        'sample_output': '51',
        'expected_output': '51',
        'time_limit': 1000,
        'memory_limit': 256
    },
    {
        'title': 'Maximum Number of Non-Overlapping Substrings',
        'slug': 'max-non-overlapping-substrings',
        'description': 'Find maximum number of substrings that meet criteria and don\'t overlap',
        'difficulty': 'Hard',
        'category': 'String/Greedy',
        'input_format': 'String s',
        'output_format': 'List of substrings',
        'constraints': '1 ≤ s.length ≤ 10^5',
        'sample_input': '"adefaddaccc"',
        'sample_output': '["e","f","ccc"]',
        'expected_output': '["e","f","ccc"]',
        'time_limit': 1000,
        'memory_limit': 256
    },
    {
        'title': 'Minimum Number of Flips to Make Binary String Alternating',
        'slug': 'min-flips-to-alternate',
        'description': 'Calculate minimum flips (0→1 or 1→0) to make binary string alternating',
        'difficulty': 'Hard',
        'category': 'String/Sliding Window',
        'input_format': 'Binary string s',
        'output_format': 'Minimum flips',
        'constraints': '1 ≤ s.length ≤ 10^5',
        'sample_input': '"111000"',
        'sample_output': '2',
        'expected_output': '2',
        'time_limit': 1000,
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