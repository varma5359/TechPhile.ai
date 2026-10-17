from explore_courses.populate_base import *

def populate():
    admin_user = get_admin_user()
    ai_topic = Topic.objects.get_or_create(name="Artificial Intelligence")[0]
    
    # Create simple datasets
    xor_data = """x1,x2,y
0,0,0
0,1,1
1,0,1
1,1,0
"""
    xor_dataset = create_dataset(
        "XOR Problem", xor_data, "xor.csv",
        "Simple XOR dataset for neural network training", admin_user
    )
    
    # Basic AI Problems
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
        },
        {
            "title": "Calculate Hamming Distance",
            "description": "Calculate the Hamming distance between two binary strings.",
            "starter_code": '''def hamming_distance(str1, str2):
    # Your code here
    return distance

print(hamming_distance("1010", "1001"))''',
            "solution": '''def hamming_distance(str1, str2):
    return sum(c1 != c2 for c1, c2 in zip(str1, str2))

print(hamming_distance("1010", "1001"))''',
            "expected_output": "2",
            "difficulty": "beginner",
            "points": 60
        },
        {
            "title": "Simple Perceptron",
            "description": "Implement a perceptron for AND gate with weights [0.5, 0.5] and bias -0.7.",
            "starter_code": '''import numpy as np

def perceptron(x1, x2):
    weights = np.array([0.5, 0.5])
    bias = -0.7
    # Your code here
    return output

print(perceptron(1, 1))''',
            "solution": '''import numpy as np

def perceptron(x1, x2):
    weights = np.array([0.5, 0.5])
    bias = -0.7
    inputs = np.array([x1, x2])
    summation = np.dot(weights, inputs) + bias
    return 1 if summation > 0 else 0

print(perceptron(1, 1))''',
            "expected_output": "1",
            "difficulty": "beginner",
            "points": 80
        },
        {
            "title": "Step Activation Function",
            "description": "Implement a step activation function with threshold 0.",
            "starter_code": '''def step_function(x):
    # Your code here
    return output

print(step_function(0.5))''',
            "solution": '''def step_function(x):
    return 1 if x > 0 else 0

print(step_function(0.5))''',
            "expected_output": "1",
            "difficulty": "beginner",
            "points": 50
        },
        {
            "title": "Sigmoid Activation Function",
            "description": "Implement the sigmoid activation function.",
            "starter_code": '''import math
def sigmoid(x):
    # Your code here
    return output

print(sigmoid(0))''',
            "solution": '''import math
def sigmoid(x):
    return 1 / (1 + math.exp(-x))

print(sigmoid(0))''',
            "expected_output": "0.5",
            "difficulty": "beginner",
            "points": 60
        },
        {
            "title": "Mean Squared Error",
            "description": "Calculate mean squared error between predicted and actual values.",
            "starter_code": '''import numpy as np
def mse(y_true, y_pred):
    # Your code here
    return error

print(mse(np.array([1, 0, 1]), np.array([0.9, 0.2, 0.8])))''',
            "solution": '''import numpy as np
def mse(y_true, y_pred):
    return np.mean((y_true - y_pred)**2)

print(mse(np.array([1, 0, 1]), np.array([0.9, 0.2, 0.8])))''',
            "expected_output": "0.023333333333333334",
            "difficulty": "beginner",
            "points": 70
        },
        {
            "title": "One-Hot Encoding",
            "description": "Convert categorical labels to one-hot encoded vectors.",
            "starter_code": '''import numpy as np
def one_hot_encode(labels, num_classes):
    # Your code here
    return encoded

print(one_hot_encode([0, 1, 2], 3))''',
            "solution": '''import numpy as np
def one_hot_encode(labels, num_classes):
    return np.eye(num_classes)[labels]

print(one_hot_encode([0, 1, 2], 3))''',
            "expected_output": "[[1. 0. 0.]\n [0. 1. 0.]\n [0. 0. 1.]]",
            "difficulty": "beginner",
            "points": 70
        },
        {
            "title": "Simple Linear Regression",
            "description": "Implement a simple linear regression model (y = wx + b).",
            "starter_code": '''import numpy as np
class LinearRegression:
    def __init__(self):
        self.w = None
        self.b = None
    
    def fit(self, X, y):
        # Your code here
        pass
    
    def predict(self, X):
        # Your code here
        return y_pred

# Test
X = np.array([1, 2, 3])
y = np.array([2, 4, 6])
model = LinearRegression()
model.fit(X, y)
print(model.predict(4))''',
            "solution": '''import numpy as np
class LinearRegression:
    def __init__(self):
        self.w = None
        self.b = None
    
    def fit(self, X, y):
        X_mean = np.mean(X)
        y_mean = np.mean(y)
        numerator = np.sum((X - X_mean) * (y - y_mean))
        denominator = np.sum((X - X_mean) ** 2)
        self.w = numerator / denominator
        self.b = y_mean - self.w * X_mean
    
    def predict(self, X):
        return self.w * X + self.b

# Test
X = np.array([1, 2, 3])
y = np.array([2, 4, 6])
model = LinearRegression()
model.fit(X, y)
print(model.predict(4))''',
            "expected_output": "8.0",
            "difficulty": "intermediate",
            "points": 100
        },
        {
            "title": "K-Nearest Neighbors Classifier",
            "description": "Implement a simple KNN classifier with k=3.",
            "starter_code": '''import numpy as np
from collections import Counter

class KNN:
    def __init__(self, k=3):
        self.k = k
    
    def fit(self, X, y):
        # Your code here
        pass
    
    def predict(self, X_test):
        # Your code here
        return predictions

# Test
X_train = np.array([[1, 2], [2, 3], [3, 4]])
y_train = np.array([0, 0, 1])
knn = KNN(k=3)
knn.fit(X_train, y_train)
print(knn.predict(np.array([[2, 3.5]])))''',
            "solution": '''import numpy as np
from collections import Counter
from sklearn.metrics.pairwise import euclidean_distances

class KNN:
    def __init__(self, k=3):
        self.k = k
    
    def fit(self, X, y):
        self.X_train = X
        self.y_train = y
    
    def predict(self, X_test):
        distances = euclidean_distances(X_test, self.X_train)
        k_indices = np.argsort(distances)[:, :self.k]
        k_labels = self.y_train[k_indices]
        predictions = [Counter(labels).most_common(1)[0][0] for labels in k_labels]
        return np.array(predictions)

# Test
X_train = np.array([[1, 2], [2, 3], [3, 4]])
y_train = np.array([0, 0, 1])
knn = KNN(k=3)
knn.fit(X_train, y_train)
print(knn.predict(np.array([[2, 3.5]])))''',
            "expected_output": "[0]",
            "difficulty": "intermediate",
            "points": 120
        },
        {
            "title": "Decision Stump Classifier",
            "description": "Implement a decision stump (1-level decision tree).",
            "starter_code": '''import numpy as np
class DecisionStump:
    def fit(self, X, y):
        # Your code here
        pass
    
    def predict(self, X):
        # Your code here
        return predictions

# Test
X = np.array([1, 2, 3, 4, 5]).reshape(-1, 1)
y = np.array([0, 0, 1, 1, 1])
model = DecisionStump()
model.fit(X, y)
print(model.predict(np.array([2.5]).reshape(-1, 1)))''',
            "solution": '''import numpy as np
class DecisionStump:
    def fit(self, X, y):
        self.threshold = np.median(X)
    
    def predict(self, X):
        return (X > self.threshold).astype(int)

# Test
X = np.array([1, 2, 3, 4, 5]).reshape(-1, 1)
y = np.array([0, 0, 1, 1, 1])
model = DecisionStump()
model.fit(X, y)
print(model.predict(np.array([2.5]).reshape(-1, 1)))''',
            "expected_output": "[1]",
            "difficulty": "intermediate",
            "points": 100
        },
        {
            "title": "XOR Problem with MLP",
            "description": "Train a simple MLP to solve the XOR problem.",
            "starter_code": '''import numpy as np
from sklearn.neural_network import MLPClassifier

# XOR dataset
X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
y = np.array([0, 1, 1, 0])

# Your code here''',
            "solution": '''import numpy as np
from sklearn.neural_network import MLPClassifier

# XOR dataset
X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
y = np.array([0, 1, 1, 0])

# Create and train MLP
mlp = MLPClassifier(hidden_layer_sizes=(2,), activation='logistic', max_iter=10000)
mlp.fit(X, y)

# Test
print(mlp.predict(X))''',
            "expected_output": "[0 1 1 0]",
            "difficulty": "intermediate",
            "points": 150,
            "dataset": xor_dataset
        },
        {
            "title": "Simple Genetic Algorithm",
            "description": "Implement a genetic algorithm to maximize f(x) = x^2.",
            "starter_code": '''import numpy as np

def fitness(x):
    return x**2

def genetic_algorithm(pop_size=10, num_generations=5):
    # Your code here
    return best_solution

print(genetic_algorithm())''',
            "solution": '''import numpy as np

def fitness(x):
    return x**2

def genetic_algorithm(pop_size=10, num_generations=5):
    population = np.random.randint(0, 32, pop_size)
    
    for _ in range(num_generations):
        # Selection
        fitness_scores = [fitness(x) for x in population]
        parents = np.random.choice(population, size=pop_size, p=np.array(fitness_scores)/sum(fitness_scores))
        
        # Crossover
        children = []
        for i in range(0, pop_size, 2):
            parent1, parent2 = parents[i], parents[i+1]
            child1 = (parent1 + parent2) // 2
            child2 = (parent1 + parent2 + 1) // 2
            children.extend([child1, child2])
        
        # Mutation
        for i in range(len(children)):
            if np.random.rand() < 0.1:
                children[i] = np.random.randint(0, 32)
        
        population = np.array(children)
    
    return max(population, key=fitness)

print(genetic_algorithm())''',
            "expected_output": "A number close to 31",
            "difficulty": "intermediate",
            "points": 150
        },
        {
            "title": "Q-Learning Table",
            "description": "Implement a simple Q-learning table for a grid world.",
            "starter_code": '''import numpy as np

class QLearning:
    def __init__(self, states, actions):
        # Your code here
        pass
    
    def update(self, state, action, reward, next_state):
        # Your code here
        pass

# Test
states = [0, 1, 2]
actions = ['left', 'right']
q = QLearning(states, actions)
q.update(0, 'right', 1, 1)
print(q.q_table)''',
            "solution": '''import numpy as np

class QLearning:
    def __init__(self, states, actions):
        self.q_table = np.zeros((len(states), len(actions)))
        self.actions = actions
        self.learning_rate = 0.1
        self.discount_factor = 0.9
    
    def update(self, state, action, reward, next_state):
        action_idx = self.actions.index(action)
        current_q = self.q_table[state, action_idx]
        max_next_q = np.max(self.q_table[next_state])
        new_q = current_q + self.learning_rate * (reward + self.discount_factor * max_next_q - current_q)
        self.q_table[state, action_idx] = new_q

# Test
states = [0, 1, 2]
actions = ['left', 'right']
q = QLearning(states, actions)
q.update(0, 'right', 1, 1)
print(q.q_table)''',
            "expected_output": "Q-table with updated values",
            "difficulty": "intermediate",
            "points": 150
        },
        {
            "title": "Naive Bayes Classifier",
            "description": "Implement a Gaussian Naive Bayes classifier from scratch.",
            "starter_code": '''import numpy as np
from collections import defaultdict

class NaiveBayes:
    def fit(self, X, y):
        # Your code here
        pass
    
    def predict(self, X):
        # Your code here
        return predictions

# Test
X = np.array([[1, 2], [2, 3], [3, 4], [4, 5]])
y = np.array([0, 0, 1, 1])
nb = NaiveBayes()
nb.fit(X, y)
print(nb.predict(np.array([[2.5, 3.5]])))''',
            "solution": '''import numpy as np
from collections import defaultdict

class NaiveBayes:
    def fit(self, X, y):
        self.classes = np.unique(y)
        self.parameters = {}
        
        for c in self.classes:
            X_c = X[y == c]
            self.parameters[c] = {
                'mean': X_c.mean(axis=0),
                'var': X_c.var(axis=0),
                'prior': len(X_c) / len(X)
            }
    
    def _pdf(self, x, mean, var):
        return np.exp(-(x - mean)**2 / (2 * var)) / np.sqrt(2 * np.pi * var)
    
    def predict(self, X):
        predictions = []
        for x in X:
            posteriors = []
            for c in self.classes:
                prior = np.log(self.parameters[c]['prior'])
                likelihood = np.sum(np.log(self._pdf(x, self.parameters[c]['mean'], self.parameters[c]['var'])))
                posterior = prior + likelihood
                posteriors.append(posterior)
            predictions.append(self.classes[np.argmax(posteriors)])
        return np.array(predictions)

# Test
X = np.array([[1, 2], [2, 3], [3, 4], [4, 5]])
y = np.array([0, 0, 1, 1])
nb = NaiveBayes()
nb.fit(X, y)
print(nb.predict(np.array([[2.5, 3.5]])))''',
            "expected_output": "[0]",
            "difficulty": "intermediate",
            "points": 150
        },
        {
            "title": "K-Means Clustering",
            "description": "Implement K-means clustering with K=2.",
            "starter_code": '''import numpy as np

class KMeans:
    def __init__(self, k=2):
        # Your code here
        pass
    
    def fit(self, X):
        # Your code here
        pass

# Test
X = np.array([[1, 2], [1, 4], [1, 0], [4, 2], [4, 4], [4, 0]])
kmeans = KMeans(k=2)
kmeans.fit(X)
print(kmeans.centroids)''',
            "solution": '''import numpy as np

class KMeans:
    def __init__(self, k=2):
        self.k = k
    
    def fit(self, X, max_iters=100):
        # Randomly initialize centroids
        self.centroids = X[np.random.choice(len(X), self.k, replace=False)]
        
        for _ in range(max_iters):
            # Assign clusters
            distances = np.sqrt(((X - self.centroids[:, np.newaxis])**2).sum(axis=2))
            self.labels = np.argmin(distances, axis=0)
            
            # Update centroids
            new_centroids = np.array([X[self.labels == i].mean(axis=0) for i in range(self.k)])
            
            # Check convergence
            if np.allclose(self.centroids, new_centroids):
                break
                
            self.centroids = new_centroids

# Test
X = np.array([[1, 2], [1, 4], [1, 0], [4, 2], [4, 4], [4, 0]])
kmeans = KMeans(k=2)
kmeans.fit(X)
print(kmeans.centroids)''',
            "expected_output": "Two cluster centroids",
            "difficulty": "intermediate",
            "points": 150
        },
        {
            "title": "Simple Recommender System",
            "description": "Implement a cosine similarity-based recommender system.",
            "starter_code": '''import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class Recommender:
    def __init__(self, data):
        # Your code here
        pass
    
    def recommend(self, item_id, n=3):
        # Your code here
        return recommendations

# Test
data = np.array([
    [5, 3, 0, 1],
    [4, 0, 0, 1],
    [1, 1, 0, 5],
    [1, 0, 0, 4],
    [0, 1, 5, 4]
])
rec = Recommender(data)
print(rec.recommend(0))''',
            "solution": '''import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class Recommender:
    def __init__(self, data):
        self.similarity = cosine_similarity(data)
    
    def recommend(self, item_id, n=3):
        similar_items = np.argsort(self.similarity[item_id])[::-1]
        return similar_items[1:n+1]

# Test
data = np.array([
    [5, 3, 0, 1],
    [4, 0, 0, 1],
    [1, 1, 0, 5],
    [1, 0, 0, 4],
    [0, 1, 5, 4]
])
rec = Recommender(data)
print(rec.recommend(0))''',
            "expected_output": "[1 2 3]",
            "difficulty": "intermediate",
            "points": 150
        },
        {
            "title": "MiniMax Algorithm",
            "description": "Implement the MiniMax algorithm for Tic-Tac-Toe.",
            "starter_code": '''def minimax(board, depth, is_maximizing):
    # Your code here
    return best_score

# Test board (0=empty, 1=X, 2=O)
board = [
    [1, 0, 2],
    [0, 1, 0],
    [0, 0, 0]
]
print(minimax(board, 3, True))''',
            "solution": '''def evaluate(board):
    # Check rows
    for row in board:
        if all(cell == 1 for cell in row):
            return 10
        if all(cell == 2 for cell in row):
            return -10
    
    # Check columns
    for col in range(3):
        if all(board[row][col] == 1 for row in range(3)):
            return 10
        if all(board[row][col] == 2 for row in range(3)):
            return -10
    
    # Check diagonals
    if board[0][0] == board[1][1] == board[2][2]:
        if board[0][0] == 1: return 10
        if board[0][0] == 2: return -10
    if board[0][2] == board[1][1] == board[2][0]:
        if board[0][2] == 1: return 10
        if board[0][2] == 2: return -10
    
    return 0

def minimax(board, depth, is_maximizing):
    score = evaluate(board)
    if score != 0:
        return score
    
    if depth == 0:
        return 0
    
    if is_maximizing:
        best = -float('inf')
        for i in range(3):
            for j in range(3):
                if board[i][j] == 0:
                    board[i][j] = 1
                    best = max(best, minimax(board, depth-1, False))
                    board[i][j] = 0
        return best
    else:
        best = float('inf')
        for i in range(3):
            for j in range(3):
                if board[i][j] == 0:
                    board[i][j] = 2
                    best = min(best, minimax(board, depth-1, True))
                    board[i][j] = 0
        return best

# Test board (0=empty, 1=X, 2=O)
board = [
    [1, 0, 2],
    [0, 1, 0],
    [0, 0, 0]
]
print(minimax(board, 3, True))''',
            "expected_output": "10 (or similar evaluation score)",
            "difficulty": "intermediate",
            "points": 150
        },
        {
            "title": "Activation Function Derivatives",
            "description": "Implement derivatives for sigmoid and ReLU activation functions.",
            "starter_code": '''import numpy as np

def sigmoid_derivative(x):
    # Your code here
    return derivative

def relu_derivative(x):
    # Your code here
    return derivative

print(sigmoid_derivative(0))
print(relu_derivative(1))''',
            "solution": '''import numpy as np

def sigmoid_derivative(x):
    s = 1 / (1 + np.exp(-x))
    return s * (1 - s)

def relu_derivative(x):
    return 1 if x > 0 else 0

print(sigmoid_derivative(0))
print(relu_derivative(1))''',
            "expected_output": "0.25\n1",
            "difficulty": "beginner",
            "points": 80
        }
    ]

    # Create Problem entries
    for p in problems:
        Problem.objects.get_or_create(
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
        )
    
    print("✅ 20 Basic AI problems populated.")

if __name__ == '__main__':
    populate()