from techphile_exams.explore_courses.populate_base import *
def populate():
    admin_user = get_admin_user()
    ai_topic = Topic.objects.get_or_create(name="Artificial Intelligence")[0]
    
    # More Basic AI Problems
    problems = [
        {
            "title": "Binary Classification with Perceptron",
            "description": "Implement a perceptron for binary classification with given weights [0.6, -0.4] and bias 0.3.",
            "starter_code": '''import numpy as np

def perceptron(x1, x2):
    weights = np.array([0.6, -0.4])
    bias = 0.3
    # Your code here
    return output

print(perceptron(1, 0))''',
            "solution": '''import numpy as np

def perceptron(x1, x2):
    weights = np.array([0.6, -0.4])
    bias = 0.3
    inputs = np.array([x1, x2])
    summation = np.dot(weights, inputs) + bias
    return 1 if summation > 0 else 0

print(perceptron(1, 0))''',
            "expected_output": "1",
            "difficulty": "beginner",
            "points": 70
        },
        {
            "title": "ReLU Activation Function",
            "description": "Implement the ReLU activation function.",
            "starter_code": '''def relu(x):
    # Your code here
    return output

print(relu(-0.5))
print(relu(2.0))''',
            "solution": '''def relu(x):
    return max(0, x)

print(relu(-0.5))
print(relu(2.0))''',
            "expected_output": "0\n2.0",
            "difficulty": "beginner",
            "points": 50
        },
        {
            "title": "Binary Cross Entropy Loss",
            "description": "Calculate binary cross entropy loss between true and predicted values.",
            "starter_code": '''import numpy as np
def binary_cross_entropy(y_true, y_pred):
    # Your code here
    return loss

print(binary_cross_entropy(np.array([1, 0]), np.array([0.9, 0.1])))''',
            "solution": '''import numpy as np
def binary_cross_entropy(y_true, y_pred):
    return -np.mean(y_true * np.log(y_pred) + (1 - y_true) * np.log(1 - y_pred))

print(binary_cross_entropy(np.array([1, 0]), np.array([0.9, 0.1])))''',
            "expected_output": "0.10536051565782628",
            "difficulty": "beginner",
            "points": 80
        },
        {
            "title": "Softmax Function",
            "description": "Implement the softmax function for multi-class classification.",
            "starter_code": '''import numpy as np
def softmax(x):
    # Your code here
    return output

print(softmax(np.array([1.0, 2.0, 3.0])))''',
            "solution": '''import numpy as np
def softmax(x):
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum()

print(softmax(np.array([1.0, 2.0, 3.0])))''',
            "expected_output": "[0.09003057 0.24472847 0.66524096]",
            "difficulty": "beginner",
            "points": 70
        },
        {
            "title": "Euclidean Distance",
            "description": "Calculate Euclidean distance between two points.",
            "starter_code": '''import numpy as np
def euclidean_distance(a, b):
    # Your code here
    return distance

print(euclidean_distance(np.array([1, 2]), np.array([4, 6])))''',
            "solution": '''import numpy as np
def euclidean_distance(a, b):
    return np.sqrt(np.sum((a - b)**2))

print(euclidean_distance(np.array([1, 2]), np.array([4, 6])))''',
            "expected_output": "5.0",
            "difficulty": "beginner",
            "points": 60
        },
        {
            "title": "Manhattan Distance",
            "description": "Calculate Manhattan distance between two points.",
            "starter_code": '''import numpy as np
def manhattan_distance(a, b):
    # Your code here
    return distance

print(manhattan_distance(np.array([1, 2]), np.array([4, 6])))''',
            "solution": '''import numpy as np
def manhattan_distance(a, b):
    return np.sum(np.abs(a - b))

print(manhattan_distance(np.array([1, 2]), np.array([4, 6])))''',
            "expected_output": "7",
            "difficulty": "beginner",
            "points": 60
        },
        {
            "title": "Feature Scaling (Normalization)",
            "description": "Implement feature scaling to normalize data between 0 and 1.",
            "starter_code": '''import numpy as np
def normalize(X):
    # Your code here
    return normalized

print(normalize(np.array([10, 20, 30])))''',
            "solution": '''import numpy as np
def normalize(X):
    return (X - X.min()) / (X.max() - X.min())

print(normalize(np.array([10, 20, 30])))''',
            "expected_output": "[0.  0.5 1. ]",
            "difficulty": "beginner",
            "points": 70
        },
        {
            "title": "Standardization (Z-score)",
            "description": "Implement standardization using z-score normalization.",
            "starter_code": '''import numpy as np
def standardize(X):
    # Your code here
    return standardized

print(standardize(np.array([1, 2, 3])))''',
            "solution": '''import numpy as np
def standardize(X):
    return (X - np.mean(X)) / np.std(X)

print(standardize(np.array([1, 2, 3])))''',
            "expected_output": "[-1.22474487  0.          1.22474487]",
            "difficulty": "beginner",
            "points": 70
        },
        {
            "title": "Confusion Matrix",
            "description": "Create a confusion matrix from true and predicted labels.",
            "starter_code": '''import numpy as np
def confusion_matrix(y_true, y_pred, num_classes):
    # Your code here
    return cm

print(confusion_matrix(np.array([0, 1, 0, 1]), np.array([0, 1, 1, 0]), 2))''',
            "solution": '''import numpy as np
def confusion_matrix(y_true, y_pred, num_classes):
    cm = np.zeros((num_classes, num_classes), dtype=int)
    for t, p in zip(y_true, y_pred):
        cm[t][p] += 1
    return cm

print(confusion_matrix(np.array([0, 1, 0, 1]), np.array([0, 1, 1, 0]), 2))''',
            "expected_output": "[[1 1]\n [1 1]]",
            "difficulty": "beginner",
            "points": 80
        },
        {
            "title": "Accuracy Score",
            "description": "Calculate accuracy score from true and predicted labels.",
            "starter_code": '''import numpy as np
def accuracy_score(y_true, y_pred):
    # Your code here
    return accuracy

print(accuracy_score(np.array([0, 1, 0, 1]), np.array([0, 1, 1, 0])))''',
            "solution": '''import numpy as np
def accuracy_score(y_true, y_pred):
    return np.mean(y_true == y_pred)

print(accuracy_score(np.array([0, 1, 0, 1]), np.array([0, 1, 1, 0])))''',
            "expected_output": "0.5",
            "difficulty": "beginner",
            "points": 60
        },
        {
            "title": "Precision Score",
            "description": "Calculate precision score for binary classification.",
            "starter_code": '''import numpy as np
def precision_score(y_true, y_pred):
    # Your code here
    return precision

print(precision_score(np.array([0, 1, 0, 1]), np.array([0, 1, 1, 0])))''',
            "solution": '''import numpy as np
def precision_score(y_true, y_pred):
    tp = np.sum((y_true == 1) & (y_pred == 1))
    fp = np.sum((y_true == 0) & (y_pred == 1))
    return tp / (tp + fp)

print(precision_score(np.array([0, 1, 0, 1]), np.array([0, 1, 1, 0])))''',
            "expected_output": "0.5",
            "difficulty": "beginner",
            "points": 70
        },
        {
            "title": "Recall Score",
            "description": "Calculate recall score for binary classification.",
            "starter_code": '''import numpy as np
def recall_score(y_true, y_pred):
    # Your code here
    return recall

print(recall_score(np.array([0, 1, 0, 1]), np.array([0, 1, 1, 0])))''',
            "solution": '''import numpy as np
def recall_score(y_true, y_pred):
    tp = np.sum((y_true == 1) & (y_pred == 1))
    fn = np.sum((y_true == 1) & (y_pred == 0))
    return tp / (tp + fn)

print(recall_score(np.array([0, 1, 0, 1]), np.array([0, 1, 1, 0])))''',
            "expected_output": "0.5",
            "difficulty": "beginner",
            "points": 70
        },
        {
            "title": "F1 Score",
            "description": "Calculate F1 score for binary classification.",
            "starter_code": '''import numpy as np
def f1_score(y_true, y_pred):
    # Your code here
    return f1

print(f1_score(np.array([0, 1, 0, 1]), np.array([0, 1, 1, 0])))''',
            "solution": '''import numpy as np
def f1_score(y_true, y_pred):
    precision = precision_score(y_true, y_pred)
    recall = recall_score(y_true, y_pred)
    return 2 * (precision * recall) / (precision + recall)

print(f1_score(np.array([0, 1, 0, 1]), np.array([0, 1, 1, 0])))''',
            "expected_output": "0.5",
            "difficulty": "beginner",
            "points": 80
        },
        {
            "title": "Simple Gradient Descent",
            "description": "Implement gradient descent to find the minimum of f(x) = x^2.",
            "starter_code": '''def gradient_descent(learning_rate=0.1, n_iter=10):
    x = 5  # Initial guess
    # Your code here
    return x

print(gradient_descent())''',
            "solution": '''def gradient_descent(learning_rate=0.1, n_iter=10):
    x = 5  # Initial guess
    for _ in range(n_iter):
        gradient = 2 * x
        x = x - learning_rate * gradient
    return x

print(gradient_descent())''',
            "expected_output": "A number close to 0",
            "difficulty": "beginner",
            "points": 90
        },
        {
            "title": "Linear Regression Prediction",
            "description": "Make predictions using a trained linear regression model (y = 2x + 1).",
            "starter_code": '''def predict(x):
    # Model parameters
    w = 2
    b = 1
    # Your code here
    return y

print(predict(3))''',
            "solution": '''def predict(x):
    # Model parameters
    w = 2
    b = 1
    return w * x + b

print(predict(3))''',
            "expected_output": "7",
            "difficulty": "beginner",
            "points": 50
        },
        {
            "title": "Logistic Regression Prediction",
            "description": "Make predictions using a trained logistic regression model.",
            "starter_code": '''import numpy as np
def sigmoid(x):
    return 1 / (1 + np.exp(-x))

def predict(x):
    # Model parameters
    w = np.array([0.5, -0.5])
    b = 0.1
    # Your code here
    return prediction

print(predict(np.array([1, 2])))''',
            "solution": '''import numpy as np
def sigmoid(x):
    return 1 / (1 + np.exp(-x))

def predict(x):
    # Model parameters
    w = np.array([0.5, -0.5])
    b = 0.1
    z = np.dot(w, x) + b
    return 1 if sigmoid(z) > 0.5 else 0

print(predict(np.array([1, 2])))''',
            "expected_output": "0",
            "difficulty": "beginner",
            "points": 80
        },
        {
            "title": "Simple Bag-of-Words",
            "description": "Create a simple bag-of-words representation from text.",
            "starter_code": '''from collections import defaultdict
def bag_of_words(texts):
    # Your code here
    return bow

print(bag_of_words(["hello world", "world of python"]))''',
            "solution": '''from collections import defaultdict
def bag_of_words(texts):
    vocab = defaultdict(int)
    for text in texts:
        for word in text.split():
            vocab[word] += 1
    return vocab

print(bag_of_words(["hello world", "world of python"]))''',
            "expected_output": "defaultdict(<class 'int'>, {'hello': 1, 'world': 2, 'of': 1, 'python': 1})",
            "difficulty": "beginner",
            "points": 80
        },
        {
            "title": "Tokenize Text",
            "description": "Implement a simple text tokenizer that splits on whitespace.",
            "starter_code": '''def tokenize(text):
    # Your code here
    return tokens

print(tokenize("This is a sample sentence."))''',
            "solution": '''def tokenize(text):
    return text.split()

print(tokenize("This is a sample sentence."))''',
            "expected_output": "['This', 'is', 'a', 'sample', 'sentence.']",
            "difficulty": "beginner",
            "points": 50
        },
        {
            "title": "Count Vectorizer",
            "description": "Implement a simple count vectorizer for text data.",
            "starter_code": '''from collections import defaultdict
def count_vectorize(texts):
    # Your code here
    return vectors

print(count_vectorize(["apple banana", "banana orange"]))''',
            "solution": '''from collections import defaultdict
def count_vectorize(texts):
    vocab = defaultdict(int)
    vocab.default_factory = lambda: len(vocab)
    vectors = []
    for text in texts:
        vector = defaultdict(int)
        for word in text.split():
            vector[vocab[word]] += 1
        vectors.append(dict(vector))
    return vectors

print(count_vectorize(["apple banana", "banana orange"]))''',
            "expected_output": "[{0: 1, 1: 1}, {1: 1, 2: 1}]",
            "difficulty": "beginner",
            "points": 90
        },
        {
            "title": "Jaccard Similarity",
            "description": "Calculate Jaccard similarity between two sets.",
            "starter_code": '''def jaccard_similarity(set1, set2):
    # Your code here
    return similarity

print(jaccard_similarity({1, 2, 3}, {2, 3, 4}))''',
            "solution": '''def jaccard_similarity(set1, set2):
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union

print(jaccard_similarity({1, 2, 3}, {2, 3, 4}))''',
            "expected_output": "0.5",
            "difficulty": "beginner",
            "points": 70
        },
        {
            "title": "Simple Moving Average",
            "description": "Calculate simple moving average for a time series.",
            "starter_code": '''import numpy as np
def moving_average(data, window_size):
    # Your code here
    return ma

print(moving_average(np.array([1, 2, 3, 4, 5]), 3))''',
            "solution": '''import numpy as np
def moving_average(data, window_size):
    return np.convolve(data, np.ones(window_size)/window_size, mode='valid')

print(moving_average(np.array([1, 2, 3, 4, 5]), 3))''',
            "expected_output": "[2. 3. 4.]",
            "difficulty": "beginner",
            "points": 80
        }
    ]

    # Create Problem entries
    for p in problems:
        Problem.objects.get_or_create(
            title=p["title"],
            topic=ai_topic,
            difficulty=p["difficulty"],
            description=p["description"],
            starter_code=p["starter_code"],
            expected_output=p["expected_output"],
            solution=p["solution"],
            points=p["points"],
            created_by=admin_user
        )
    
    print("✅ 20 More Basic AI problems populated.")

if __name__ == '__main__':
    populate()