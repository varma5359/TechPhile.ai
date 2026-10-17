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

    # Create sample problems
problem_data=[
    {
        'title': 'Calculate Cart Total',
        'slug': 'cart-total',
        'description': 'Given a list of products with prices, calculate the total cart value.',
        'difficulty': 'Basic',
        'category': 'E-Commerce',
        'input_format': '[ {"name": "Shirt", "price": 20}, {"name": "Jeans", "price": 50} ]',
        'output_format': '70',
        'constraints': 'Number of products ≤ 1000',
        'sample_input': '[ {"name": "Shirt", "price": 20}, {"name": "Jeans", "price": 50} ]',
        'sample_output': '70',
        'expected_output': '70',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Apply Discount to Cart',
        'slug': 'apply-discount',
        'description': 'Apply a discount percentage to the total cart value.',
        'difficulty': 'Basic',
        'category': 'E-Commerce',
        'input_format': '[ {"name": "Shirt", "price": 20}, {"name": "Jeans", "price": 50} ], discount=10',
        'output_format': '63.0',
        'constraints': '0 ≤ discount ≤ 100',
        'sample_input': '[ {"name": "Shirt", "price": 20}, {"name": "Jeans", "price": 50} ], 10',
        'sample_output': '63.0',
        'expected_output': '63.0',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Find Cheapest Product',
        'slug': 'cheapest-product',
        'description': 'Given a list of products, return the cheapest one.',
        'difficulty': 'Basic',
        'category': 'E-Commerce',
        'input_format': '[ {"name": "Shirt", "price": 20}, {"name": "Jeans", "price": 50} ]',
        'output_format': '{"name": "Shirt", "price": 20}',
        'constraints': 'List length ≤ 1000',
        'sample_input': '[ {"name": "Shirt", "price": 20}, {"name": "Jeans", "price": 50} ]',
        'sample_output': '{"name": "Shirt", "price": 20}',
        'expected_output': '{"name": "Shirt", "price": 20}',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Recommend Similar Products',
        'slug': 'product-suggestions',
        'description': 'Given a product category, suggest similar products from a dictionary.',
        'difficulty': 'Medium',
        'category': 'E-Commerce',
        'input_format': '{"Electronics": ["Laptop", "Phone"], "Clothing": ["Shirt", "Jeans"]}, category="Clothing"',
        'output_format': '["Shirt", "Jeans"]',
        'constraints': 'Categories ≤ 100, Products per category ≤ 100',
        'sample_input': '{"Electronics": ["Laptop", "Phone"], "Clothing": ["Shirt", "Jeans"]}, "Clothing"',
        'sample_output': '["Shirt", "Jeans"]',
        'expected_output': '["Shirt", "Jeans"]',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Filter Products by Price Range',
        'slug': 'filter-products',
        'description': 'Filter products within a given price range.',
        'difficulty': 'Medium',
        'category': 'E-Commerce',
        'input_format': '[ {"name": "Shirt", "price": 20}, {"name": "Jeans", "price": 50} ], min=20, max=40',
        'output_format': '[ {"name": "Shirt", "price": 20} ]',
        'constraints': 'List length ≤ 10^5',
        'sample_input': '[ {"name": "Shirt", "price": 20}, {"name": "Jeans", "price": 50} ], 20, 40',
        'sample_output': '[ {"name": "Shirt", "price": 20} ]',
        'expected_output': '[ {"name": "Shirt", "price": 20} ]',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Sort Posts by Likes',
        'slug': 'sort-posts',
        'description': 'Sort a list of posts by the number of likes in descending order.',
        'difficulty': 'Basic',
        'category': 'Social Media',
        'input_format': '[ {"post": "Hello", "likes": 10}, {"post": "Hi", "likes": 20} ]',
        'output_format': '[ {"post": "Hi", "likes": 20}, {"post": "Hello", "likes": 10} ]',
        'constraints': 'Number of posts ≤ 1000',
        'sample_input': '[ {"post": "Hello", "likes": 10}, {"post": "Hi", "likes": 20} ]',
        'sample_output': '[ {"post": "Hi", "likes": 20}, {"post": "Hello", "likes": 10} ]',
        'expected_output': '[ {"post": "Hi", "likes": 20}, {"post": "Hello", "likes": 10} ]',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Count Total Messages',
        'slug': 'count-messages',
        'description': 'Given a list of messages, count the total number sent.',
        'difficulty': 'Basic',
        'category': 'Social Media',
        'input_format': '[ {"sender": "Alice", "message": "Hi"}, {"sender": "Bob", "message": "Hello"} ]',
        'output_format': '2',
        'constraints': 'Number of messages ≤ 10^5',
        'sample_input': '[ {"sender": "Alice", "message": "Hi"}, {"sender": "Bob", "message": "Hello"} ]',
        'sample_output': '2',
        'expected_output': '2',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Group Messages by Sender',
        'slug': 'group-messages',
        'description': 'Group messages by sender in a dictionary.',
        'difficulty': 'Medium',
        'category': 'Social Media',
        'input_format': '[ {"sender": "Alice", "message": "Hi"}, {"sender": "Alice", "message": "Hey"} ]',
        'output_format': '{ "Alice": ["Hi", "Hey"] }',
        'constraints': 'Number of messages ≤ 10^5',
        'sample_input': '[ {"sender": "Alice", "message": "Hi"}, {"sender": "Alice", "message": "Hey"} ]',
        'sample_output': '{ "Alice": ["Hi", "Hey"] }',
        'expected_output': '{ "Alice": ["Hi", "Hey"] }',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Most Active User',
        'slug': 'most-active-user',
        'description': 'Find the user who sent the most messages.',
        'difficulty': 'Medium',
        'category': 'Social Media',
        'input_format': '[ {"sender": "Alice", "message": "Hi"}, {"sender": "Bob", "message": "Hello"}, {"sender": "Alice", "message": "Hey"} ]',
        'output_format': '"Alice"',
        'constraints': 'Number of messages ≤ 10^5',
        'sample_input': '[ {"sender": "Alice", "message": "Hi"}, {"sender": "Bob", "message": "Hello"}, {"sender": "Alice", "message": "Hey"} ]',
        'sample_output': '"Alice"',
        'expected_output': '"Alice"',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Count Patients by Age Group',
        'slug': 'count-patients-age',
        'description': 'Count how many patients fall into age groups: Child (<18), Adult (18-65), Senior (>65).',
        'difficulty': 'Basic',
        'category': 'Healthcare',
        'input_format': '[ {"name": "Alice", "age": 25}, {"name": "Bob", "age": 70} ]',
        'output_format': '{ "Child": 0, "Adult": 1, "Senior": 1 }',
        'constraints': 'Number of patients ≤ 10^5',
        'sample_input': '[ {"name": "Alice", "age": 25}, {"name": "Bob", "age": 70} ]',
        'sample_output': '{ "Child": 0, "Adult": 1, "Senior": 1 }',
        'expected_output': '{ "Child": 0, "Adult": 1, "Senior": 1 }',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Find Available Appointments',
        'slug': 'available-appointments',
        'description': 'Given booked slots, find available time slots.',
        'difficulty': 'Medium',
        'category': 'Healthcare',
        'input_format': 'booked = ["10:00", "11:00"], all_slots = ["10:00", "11:00", "12:00"]',
        'output_format': '["12:00"]',
        'constraints': 'Number of slots ≤ 1000',
        'sample_input': '["10:00", "11:00"], ["10:00", "11:00", "12:00"]',
        'sample_output': '["12:00"]',
        'expected_output': '["12:00"]',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Calculate Total Balance',
        'slug': 'total-balance',
        'description': 'Given a list of transactions, compute the total balance.',
        'difficulty': 'Basic',
        'category': 'Banking',
        'input_format': '[100, -50, 200]',
        'output_format': '250',
        'constraints': 'Number of transactions ≤ 10^5',
        'sample_input': '[100, -50, 200]',
        'sample_output': '250',
        'expected_output': '250',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Detect High-Value Transactions',
        'slug': 'fraud-detection',
        'description': 'Flag transactions above a threshold as suspicious.',
        'difficulty': 'Medium',
        'category': 'Banking',
        'input_format': '[100, 5000, 200, 10000], threshold=5000',
        'output_format': '[5000, 10000]',
        'constraints': 'Number of transactions ≤ 10^5',
        'sample_input': '[100, 5000, 200, 10000], 5000',
        'sample_output': '[5000, 10000]',
        'expected_output': '[5000, 10000]',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Check Seat Availability',
        'slug': 'seat-availability',
        'description': 'Given booked seats, check if a seat is available.',
        'difficulty': 'Basic',
        'category': 'Booking System',
        'input_format': 'booked = ["A1", "B2"], seat="A1"',
        'output_format': 'False',
        'constraints': 'Number of seats ≤ 1000',
        'sample_input': '["A1", "B2"], "A1"',
        'sample_output': 'False',
        'expected_output': 'False',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
        'title': 'Recommend Movies by Genre',
        'slug': 'movie-recommendations',
        'description': 'Given a dictionary of movies by genre, return movies of a selected genre.',
        'difficulty': 'Medium',
        'category': 'Booking System',
        'input_format': '{"Action": ["Movie1", "Movie2"], "Comedy": ["Movie3"]}, genre="Action"',
        'output_format': '["Movie1", "Movie2"]',
        'constraints': 'Number of movies ≤ 1000',
        'sample_input': '{"Action": ["Movie1", "Movie2"], "Comedy": ["Movie3"]}, "Action"',
        'sample_output': '["Movie1", "Movie2"]',
        'expected_output': '["Movie1", "Movie2"]',
        'memory_limit': 64
    },
    {
        'title': 'Top K Frequently Bought Products',
        'slug': 'top-k-products',
        'description': 'Given a list of purchased products, return the top K most frequently bought items.',
        'difficulty': 'Medium',
        'category': 'E-Commerce',
        'input_format': '["Shirt", "Jeans", "Shirt", "Shoes"], K=2',
        'output_format': '["Shirt", "Jeans"]',
        'constraints': 'Number of products ≤ 10^5, 1 ≤ K ≤ 100',
        'sample_input': '["Shirt", "Jeans", "Shirt", "Shoes"], 2',
        'sample_output': '["Shirt", "Jeans"]',
        'memory_limit': 64
    },

    {
        'title': 'Movie Booking System',
        'slug': 'movie-booking',
        'description': 'Given available movies, book a movie and return remaining slots.',
        'difficulty': 'Medium',
        'category': 'Booking System',
        'input_format': '{"Action": ["Movie1", "Movie2"], "Comedy": ["Movie3"]}, genre="Action", booked="Movie1"',
        'output_format': '{"Action": ["Movie2"], "Comedy": ["Movie3"]}',
        'constraints': 'Number of movies ≤ 1000',
        'sample_input': '{"Action": ["Movie1", "Movie2"], "Comedy": ["Movie3"]}, "Action", "Movie1"',
        'sample_output': '{"Action": ["Movie2"], "Comedy": ["Movie3"]}',
        'expected_output': '{"Action": ["Movie2"], "Comedy": ["Movie3"]}',
        'time_limit': 1000,
        'memory_limit': 64
    },
    {
    'title': 'Apply Multiple Discounts',
    'slug': 'multi-discount',
    'description': 'Apply discounts based on cart total: 10% if total > $100, else 5%.',
    'difficulty': 'Medium',
    'category': 'E-Commerce',
    'input_format': '[{"name": str, "price": float}] (list of products)',
    'output_format': 'float (final price after discount)',
    'constraints': '1 ≤ number of products ≤ 1000, 0 < price ≤ 10^6',
    'sample_input': '[{"name": "Laptop", "price": 1000}]',
    'sample_output': '900.0',
    'expected_output': '900.0',
    'time_limit': 1000,
    'memory_limit': 64
},
{
    'title': 'Sort Posts by Engagement',
    'slug': 'sort-by-engagement',
    'description': 'Sort posts by total engagement (likes + comments) in descending order.',
    'difficulty': 'Medium',
    'category': 'Social Media',
    'input_format': '[{"post": str, "likes": int, "comments": int}]',
    'output_format': '[{"post": str, "likes": int, "comments": int}] (sorted)',
    'constraints': '1 ≤ number of posts ≤ 10^5, 0 ≤ likes, comments ≤ 10^6',
    'sample_input': '[{"post": "A", "likes": 10, "comments": 2}, {"post": "B", "likes": 5, "comments": 10}]',
    'sample_output': '[{"post": "B", "likes": 5, "comments": 10}, {"post": "A", "likes": 10, "comments": 2}]',
    'expected_output': '[{"post": "B", "likes": 5, "comments": 10}, {"post": "A", "likes": 10, "comments": 2}]',
    'time_limit': 1500,
    'memory_limit': 64
},
{
    'title': 'Detect Spam Messages',
    'slug': 'spam-detection',
    'description': 'Flag messages containing spam keywords (e.g., "buy", "promo", "free").',
    'difficulty': 'Medium',
    'category': 'Social Media',
    'input_format': '[{"sender": str, "message": str}], spam_words=[str]',
    'output_format': '[{"sender": str, "message": str, "is_spam": bool}]',
    'constraints': '1 ≤ messages ≤ 10^4, 1 ≤ spam_words ≤ 100',
    'sample_input': '[{"sender": "Alice", "message": "Buy now!"}, {"sender": "Bob", "message": "Hello"}], ["buy", "promo"]',
    'sample_output': '[{"sender": "Alice", "message": "Buy now!", "is_spam": true}]',
    'expected_output': '[{"sender": "Alice", "message": "Buy now!", "is_spam": true}]',
    'time_limit': 1000,
    'memory_limit': 64
},
{
    'title': 'Calculate Average Patient Age',
    'slug': 'average-patient-age',
    'description': 'Calculate the average age of patients from a list.',
    'difficulty': 'Basic',
    'category': 'Healthcare',
    'input_format': '[{"name": str, "age": int}]',
    'output_format': 'float (average age)',
    'constraints': '1 ≤ number of patients ≤ 1000, 0 ≤ age ≤ 120',
    'sample_input': '[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 40}]',
    'sample_output': '35.0',
    'expected_output': '35.0',
    'time_limit': 500,
    'memory_limit': 64
},
{
    'title': 'Find Patients with High BMI',
    'slug': 'high-bmi-patients',
    'description': 'Filter patients with BMI ≥ 30 (Obese). BMI = weight(kg) / height(m)^2.',
    'difficulty': 'Basic',
    'category': 'Healthcare',
    'input_format': '[{"name": str, "weight": float, "height": float}]',
    'output_format': '[{"name": str, "bmi": float}] (filtered)',
    'constraints': '1 ≤ number of patients ≤ 1000, 0 < weight, height ≤ 300',
    'sample_input': '[{"name": "Alice", "weight": 90, "height": 1.7}, {"name": "Bob", "weight": 70, "height": 1.8}]',
    'sample_output': '[{"name": "Alice", "bmi": 31.14}]',
    'expected_output': '[{"name": "Alice", "bmi": 31.14}]',
    'time_limit': 500,
    'memory_limit': 64
},
{
    'title': 'Merge Available Slots',
    'slug': 'merge-slots',
    'description': 'Merge overlapping time slots to show continuous availability.',
    'difficulty': 'Medium',
    'category': 'Scheduling',
    'input_format': '[[start1, end1], [start2, end2], ...] (list of time intervals)',
    'output_format': '[[merged_start, merged_end], ...]',
    'constraints': '1 ≤ number of slots ≤ 10^4, 0 ≤ start < end ≤ 24',
    'sample_input': '[[9, 11], [10, 12], [14, 16]]',
    'sample_output': '[[9, 12], [14, 16]]',
    'expected_output': '[[9, 12], [14, 16]]',
    'time_limit': 1000,
    'memory_limit': 64
},
{
    'title': 'Detect Duplicate Transactions',
    'slug': 'duplicate-transactions',
    'description': 'Flag transactions with the same amount and recipient within 10 minutes.',
    'difficulty': 'Medium',
    'category': 'Finance',
    'input_format': '[{"time": str (HH:MM), "amount": float, "recipient": str}]',
    'output_format': '[{"transaction": dict, "is_duplicate": bool}]',
    'constraints': '1 ≤ transactions ≤ 10^4, 0 < amount ≤ 10^6',
    'sample_input': '[{"time": "10:00", "amount": 100, "recipient": "Alice"}, {"time": "10:05", "amount": 100, "recipient": "Alice"}]',
    'sample_output': '[{"transaction": {"time": "10:05", "amount": 100, "recipient": "Alice"}, "is_duplicate": true}]',
    'expected_output': '[{"transaction": {"time": "10:05", "amount": 100, "recipient": "Alice"}, "is_duplicate": true}]',
    'time_limit': 1000,
    'memory_limit': 64
},
{
    'title': 'Calculate Daily Spending',
    'slug': 'daily-spending',
    'description': 'Sum all transactions for each day from a list.',
    'difficulty': 'Basic',
    'category': 'Finance',
    'input_format': '[{"date": str (YYYY-MM-DD), "amount": float}]',
    'output_format': '{"date": str, "total": float} (per day)',
    'constraints': '1 ≤ transactions ≤ 10^5, 0 < amount ≤ 10^6',
    'sample_input': '[{"date": "2023-01-01", "amount": 100}, {"date": "2023-01-01", "amount": 200}]',
    'sample_output': '{"2023-01-01": 300}',
    'expected_output': '{"2023-01-01": 300}',
    'time_limit': 1000,
    'memory_limit': 64
},
{
    'title': 'Seat Reservation System',
    'slug': 'seat-reservation',
    'description': 'Reserve seats in a row if they are contiguous and available.',
    'difficulty': 'Medium',
    'category': 'Ticketing',
    'input_format': 'row_seats: list[bool] (True = available), num_seats: int',
    'output_format': 'list[int] (indices of reserved seats) or [] if not possible',
    'constraints': '1 ≤ row_seats.length ≤ 10^4, 1 ≤ num_seats ≤ 100',
    'sample_input': '[True, False, True, True, False], 2',
    'sample_output': '[2, 3]',
    'expected_output': '[2, 3]',
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