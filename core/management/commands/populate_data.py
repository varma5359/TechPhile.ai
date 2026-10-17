from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Topic, Problem, Dataset, Leaderboard


class Command(BaseCommand):
    help = 'Populate database with sample AI/ML topics and problems'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample data...')
        
        # Create topics
        topics_data = [
            {
                'name': 'Machine Learning',
                'description': 'Learn supervised and unsupervised learning algorithms using scikit-learn.',
                'icon': 'brain',
                'color': '#3b82f6',
                'sort_order': 1
            },
            {
                'name': 'Deep Learning',
                'description': 'Build neural networks with TensorFlow and PyTorch for complex problems.',
                'icon': 'network-wired',
                'color': '#8b5cf6',
                'sort_order': 2
            },
            {
                'name': 'Computer Vision',
                'description': 'Process and analyze images using OpenCV and deep learning techniques.',
                'icon': 'eye',
                'color': '#06b6d4',
                'sort_order': 3
            },
            {
                'name': 'Natural Language Processing',
                'description': 'Work with text data using NLTK, spaCy, and transformer models.',
                'icon': 'comments',
                'color': '#10b981',
                'sort_order': 4
            },
            {
                'name': 'Data Science',
                'description': 'Analyze data with pandas, NumPy, and visualization libraries.',
                'icon': 'chart-bar',
                'color': '#f59e0b',
                'sort_order': 5
            }
        ]
        
        for topic_data in topics_data:
            topic, created = Topic.objects.get_or_create(
                name=topic_data['name'],
                defaults=topic_data
            )
            if created:
                self.stdout.write(f'Created topic: {topic.name}')
        
        # Create problems
        ml_topic = Topic.objects.get(name='Machine Learning')
        dl_topic = Topic.objects.get(name='Deep Learning')
        cv_topic = Topic.objects.get(name='Computer Vision')
        nlp_topic = Topic.objects.get(name='Natural Language Processing')
        ds_topic = Topic.objects.get(name='Data Science')
        
        problems_data = [
            # Machine Learning
            {
                'title': 'Linear Regression Basics',
                'description': 'Implement a simple linear regression model from scratch using NumPy. Given a dataset of house prices, predict the price based on square footage.',
                'starter_code': '''import numpy as np
import matplotlib.pyplot as plt

# Dataset: [square_feet, price]
data = np.array([
    [1000, 200000],
    [1500, 300000],
    [2000, 400000],
    [2500, 500000],
    [3000, 600000]
])

# Your task: Implement linear regression
# Calculate slope and intercept, then predict price for 1800 sq ft

''',
                'expected_output': '360000',
                'difficulty': 'beginner',
                'topic': ml_topic,
                'points': 100,
                'sort_order': 1
            },
            {
                'title': 'K-Means Clustering',
                'description': 'Implement K-means clustering algorithm to group customer data into segments based on age and income.',
                'starter_code': '''import numpy as np
from sklearn.datasets import make_blobs
import matplotlib.pyplot as plt

# Generate sample customer data
X, _ = make_blobs(n_samples=300, centers=3, n_features=2, 
                  random_state=42, cluster_std=1.5)

# Your task: Implement K-means clustering with k=3
# Return the final cluster centers

''',
                'expected_output': '3',
                'difficulty': 'intermediate',
                'topic': ml_topic,
                'points': 150,
                'sort_order': 2
            },
            # Deep Learning
            {
                'title': 'Neural Network from Scratch',
                'description': 'Build a simple neural network with one hidden layer to classify XOR gates. Use sigmoid activation and backpropagation.',
                'starter_code': '''import numpy as np

# XOR dataset
X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
y = np.array([[0], [1], [1], [0]])

def sigmoid(x):
    return 1 / (1 + np.exp(-x))

def sigmoid_derivative(x):
    return x * (1 - x)

# Your task: Implement neural network with 2-2-1 architecture
# Train for 10000 epochs and return final predictions

''',
                'expected_output': '[0, 1, 1, 0]',
                'difficulty': 'advanced',
                'topic': dl_topic,
                'points': 200,
                'sort_order': 1
            },
            # Computer Vision
            {
                'title': 'Image Edge Detection',
                'description': 'Implement Sobel edge detection filter to detect edges in a grayscale image.',
                'starter_code': '''import numpy as np

# Sample 5x5 grayscale image
image = np.array([
    [0, 0, 0, 0, 0],
    [0, 255, 255, 255, 0],
    [0, 255, 255, 255, 0],
    [0, 255, 255, 255, 0],
    [0, 0, 0, 0, 0]
])

# Sobel kernels
sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]])
sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]])

# Your task: Apply Sobel edge detection
# Return the magnitude of gradients at center pixel (2,2)

''',
                'expected_output': '1020',
                'difficulty': 'intermediate',
                'topic': cv_topic,
                'points': 120,
                'sort_order': 1
            },
            # Natural Language Processing
            {
                'title': 'Text Sentiment Analysis',
                'description': 'Create a simple sentiment classifier using word frequency analysis. Classify text as positive or negative.',
                'starter_code': '''# Positive and negative word lists
positive_words = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic']
negative_words = ['bad', 'terrible', 'awful', 'horrible', 'disappointing', 'worst']

def analyze_sentiment(text):
    # Your task: Count positive and negative words
    # Return 'positive' if more positive words, 'negative' if more negative
    # Return 'neutral' if equal or no sentiment words
    pass

# Test with: "This movie is really good and amazing!"
test_text = "This movie is really good and amazing!"
print(analyze_sentiment(test_text))

''',
                'expected_output': 'positive',
                'difficulty': 'beginner',
                'topic': nlp_topic,
                'points': 80,
                'sort_order': 1
            },
            # Data Science
            {
                'title': 'Data Analysis with Pandas',
                'description': 'Analyze sales data to find the month with highest total sales and calculate the average sale per month.',
                'starter_code': '''import pandas as pd
import numpy as np

# Sample sales data
data = {
    'month': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    'sales': [25000, 30000, 28000, 35000, 40000, 32000]
}

df = pd.DataFrame(data)

# Your task: 
# 1. Find month with highest sales
# 2. Calculate average monthly sales
# Print: "May,31666.67"

''',
                'expected_output': 'May,31666.67',
                'difficulty': 'beginner',
                'topic': ds_topic,
                'points': 90,
                'sort_order': 1
            }
        ]
        
        for problem_data in problems_data:
            problem, created = Problem.objects.get_or_create(
                title=problem_data['title'],
                defaults=problem_data
            )
            if created:
                self.stdout.write(f'Created problem: {problem.title}')
        
        self.stdout.write(self.style.SUCCESS('Successfully populated database with sample data!'))
        self.stdout.write(f'Created {Topic.objects.count()} topics and {Problem.objects.count()} problems.')