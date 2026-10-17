from techphile_exams.explore_courses.populate_base import *
import numpy as np

def populate():
    admin_user = get_admin_user()
    dl_topic =Topic.objects.get_or_create (name="DL")[0]
    
    # Simple datasets
    xor_data = """input1,input2,output
0,0,0
0,1,1
1,0,1
1,1,0
"""
    xor_dataset = create_dataset(
        "XOR Problem", xor_data, "xor.csv",
        "Simple XOR logic problem dataset", admin_user
    )
    
    linear_data = """x,y
1,2
2,4
3,6
4,8
5,10
"""
    linear_dataset = create_dataset(
        "Linear Data", linear_data, "linear.csv",
        "Simple linear relationship y=2x", admin_user
    )
    
    # Deep Learning Problems
    problems = [
        # Basic Concepts (1-5)
        {
            "title": "Import TensorFlow",
            "description": "Import TensorFlow and print its version.",
            "starter_code": '''# Your code here''',
            "expected_output": "TensorFlow version: 2.x.x",
            "solution": '''import tensorflow as tf
print(f"TensorFlow version: {tf.__version__}")''',
            "difficulty": "beginner",
            "points": 20,
            "dataset": None
        },
        {
            "title": "Create a Tensor",
            "description": "Create a constant tensor with value [1, 2, 3].",
            "starter_code": '''import tensorflow as tf\n# Your code here''',
            "expected_output": "tf.Tensor([1 2 3], shape=(3,), dtype=int32)",
            "solution": '''import tensorflow as tf
tensor = tf.constant([1, 2, 3])
print(tensor)''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        },
        {
            "title": "Simple Addition",
            "description": "Add two tensors [1,2] and [3,4].",
            "starter_code": '''import tensorflow as tf\n# Your code here''',
            "expected_output": "tf.Tensor([4 6], shape=(2,), dtype=int32)",
            "solution": '''import tensorflow as tf
a = tf.constant([1, 2])
b = tf.constant([3, 4])
print(tf.add(a, b))''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": None
        },
        {
            "title": "Matrix Multiplication",
            "description": "Multiply two 2x2 matrices.",
            "starter_code": '''import tensorflow as tf\n# Your code here''',
            "expected_output": "tf.Tensor([[19 22] [43 50]], shape=(2, 2), dtype=int32)",
            "solution": '''import tensorflow as tf
a = tf.constant([[1, 2], [3, 4]])
b = tf.constant([[5, 6], [7, 8]])
print(tf.matmul(a, b))''',
            "difficulty": "beginner",
            "points": 40,
            "dataset": None
        },
        {
            "title": "Create a Variable",
            "description": "Create a trainable variable initialized to 5.0.",
            "starter_code": '''import tensorflow as tf\n# Your code here''',
            "expected_output": "<tf.Variable 'Variable:0' shape=() dtype=float32, numpy=5.0>",
            "solution": '''import tensorflow as tf
var = tf.Variable(5.0)
print(var)''',
            "difficulty": "beginner",
            "points": 40,
            "dataset": None
        },
        
        # Basic Models (6-10)
        {
            "title": "Single Neuron Model",
            "description": "Create a model with just one dense layer (neuron).",
            "starter_code": '''from tensorflow.keras.models import Sequential
from tensorflow.keras import layers\n# Your code here''',
            "expected_output": "Model with 1 neuron created",
            "solution": '''from tensorflow.keras.models import Sequential
from tensorflow.keras import layers

model = Sequential([
    layers.Dense(1, input_shape=(1,))
])
print("Model with 1 neuron created")''',
            "difficulty": "beginner",
            "points": 50,
            "dataset": None
        },
        {
            "title": "Linear Regression Model",
            "description": "Create a model to solve y=2x problem.",
            "starter_code": '''from tensorflow.keras.models import Sequential
from tensorflow.keras import layers\n# Your code here''',
            "expected_output": "Linear regression model created",
            "solution": '''from tensorflow.keras.models import Sequential
from tensorflow.keras import layers

model = Sequential([
    layers.Dense(1, input_shape=(1,))
])
print("Linear regression model created")''',
            "difficulty": "beginner",
            "points": 50,
            "dataset": linear_dataset
        },
        {
            "title": "Binary Classification Model",
            "description": "Create a model for binary classification (XOR problem).",
            "starter_code": '''from tensorflow.keras.models import Sequential
from tensorflow.keras import layers\n# Your code here''',
            "expected_output": "Binary classification model created",
            "solution": '''from tensorflow.keras.models import Sequential
from tensorflow.keras import layers

model = Sequential([
    layers.Dense(4, activation='relu', input_shape=(2,)),
    layers.Dense(1, activation='sigmoid')
])
print("Binary classification model created")''',
            "difficulty": "beginner",
            "points": 60,
            "dataset": xor_dataset
        },
        {
            "title": "Model Summary",
            "description": "Create a simple model and print its summary.",
            "starter_code": '''from tensorflow.keras.models import Sequential
from tensorflow.keras import layers\n# Your code here''',
            "expected_output": "Model summary printed",
            "solution": '''from tensorflow.keras.models import Sequential
from tensorflow.keras import layers

model = Sequential([
    layers.Dense(10, input_shape=(5,))
])
model.summary()
print("Model summary printed")''',
            "difficulty": "beginner",
            "points": 40,
            "dataset": None
        },
        {
            "title": "Change Learning Rate",
            "description": "Create an optimizer with learning rate 0.001.",
            "starter_code": '''from tensorflow.keras.optimizers import Adam\n# Your code here''',
            "expected_output": "Optimizer with lr=0.001 created",
            "solution": '''from tensorflow.keras.optimizers import Adam

opt = Adam(learning_rate=0.001)
print("Optimizer with lr=0.001 created")''',
            "difficulty": "beginner",
            "points": 40,
            "dataset": None
        },
        
        # Training Basics (11-15)
        {
            "title": "Train for One Epoch",
            "description": "Train a model on dummy data for one epoch.",
            "starter_code": '''import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras import layers

X = np.array([[0], [1], [2]])
y = np.array([[0], [2], [4]])

model = Sequential([layers.Dense(1, input_shape=(1,))])
model.compile(optimizer='sgd', loss='mse')

# Your code here''',
            "expected_output": "Model trained for 1 epoch",
            "solution": '''import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras import layers

X = np.array([[0], [1], [2]])
y = np.array([[0], [2], [4]])

model = Sequential([layers.Dense(1, input_shape=(1,))])
model.compile(optimizer='sgd', loss='mse')

model.fit(X, y, epochs=1)
print("Model trained for 1 epoch")''',
            "difficulty": "beginner",
            "points": 60,
            "dataset": None
        },
        {
            "title": "Make a Prediction",
            "description": "Use a trained model to predict output for input 3.",
            "starter_code": '''import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras import layers

X = np.array([[0], [1], [2]])
y = np.array([[0], [2], [4]])

model = Sequential([layers.Dense(1, input_shape=(1,))])
model.compile(optimizer='sgd', loss='mse')
model.fit(X, y, epochs=10, verbose=0)

# Your code here''',
            "expected_output": "Prediction for input 3: approximately [[6.]]",
            "solution": '''import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras import layers

X = np.array([[0], [1], [2]])
y = np.array([[0], [2], [4]])

model = Sequential([layers.Dense(1, input_shape=(1,))])
model.compile(optimizer='sgd', loss='mse')
model.fit(X, y, epochs=10, verbose=0)

pred = model.predict([[3]])
print(f"Prediction for input 3: approximately {pred}")''',
            "difficulty": "beginner",
            "points": 60,
            "dataset": None
        },
        {
            "title": "Change Batch Size",
            "description": "Train a model with batch size of 2.",
            "starter_code": '''import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras import layers

X = np.array([[0], [1], [2], [3]])
y = np.array([[0], [2], [4], [6]])

model = Sequential([layers.Dense(1, input_shape=(1,))])
model.compile(optimizer='sgd', loss='mse')

# Your code here''',
            "expected_output": "Model trained with batch_size=2",
            "solution": '''import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras import layers

X = np.array([[0], [1], [2], [3]])
y = np.array([[0], [2], [4], [6]])

model = Sequential([layers.Dense(1, input_shape=(1,))])
model.compile(optimizer='sgd', loss='mse')

model.fit(X, y, epochs=1, batch_size=2)
print("Model trained with batch_size=2")''',
            "difficulty": "beginner",
            "points": 50,
            "dataset": None
        },
        {
            "title": "Use Different Loss Function",
            "description": "Compile a model with mean absolute error loss.",
            "starter_code": '''from tensorflow.keras.models import Sequential
from tensorflow.keras import layers

model = Sequential([layers.Dense(1, input_shape=(1,))])\n# Your code here''',
            "expected_output": "Model compiled with MAE loss",
            "solution": '''from tensorflow.keras.models import Sequential
from tensorflow.keras import layers

model = Sequential([layers.Dense(1, input_shape=(1,))])
model.compile(optimizer='sgd', loss='mae')
print("Model compiled with MAE loss")''',
            "difficulty": "beginner",
            "points": 40,
            "dataset": None
        },
        {
            "title": "Evaluate Model",
            "description": "Evaluate a trained model on test data.",
            "starter_code": '''import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras import layers

X_train = np.array([[0], [1], [2]])
y_train = np.array([[0], [2], [4]])
X_test = np.array([[3]])
y_test = np.array([[6]])

model = Sequential([layers.Dense(1, input_shape=(1,))])
model.compile(optimizer='sgd', loss='mse')
model.fit(X_train, y_train, epochs=10, verbose=0)

# Your code here''',
            "expected_output": "Model evaluated on test data",
            "solution": '''import numpy as np
from tensorflow.keras.models import Sequential
from tensorflow.keras import layers

X_train = np.array([[0], [1], [2]])
y_train = np.array([[0], [2], [4]])
X_test = np.array([[3]])
y_test = np.array([[6]])

model = Sequential([layers.Dense(1, input_shape=(1,))])
model.compile(optimizer='sgd', loss='mse')
model.fit(X_train, y_train, epochs=10, verbose=0)

loss = model.evaluate(X_test, y_test)
print(f"Model evaluated on test data with loss: {loss:.4f}")''',
            "difficulty": "beginner",
            "points": 60,
            "dataset": None
        },
        
        # Practical Basics (16-20)
        {
            "title": "Load CSV Data",
            "description": "Load data from a CSV file using pandas.",
            "starter_code": '''# Your code here to load xor.csv''',
            "expected_output": "Data loaded successfully (4 samples)",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/xor.csv')
print(f"Data loaded successfully ({len(df)} samples)")''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": xor_dataset
        },
        {
            "title": "Split Features and Labels",
            "description": "Split XOR data into features (inputs) and labels (output).",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/xor.csv')\n# Your code here''',
            "expected_output": "Features shape: (4, 2), Labels shape: (4,)",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/xor.csv')

X = df[['input1', 'input2']].values
y = df['output'].values

print(f"Features shape: {X.shape}, Labels shape: {y.shape}")''',
            "difficulty": "beginner",
            "points": 40,
            "dataset": xor_dataset
        },
        {
            "title": "Normalize Data",
            "description": "Normalize data to range [0, 1].",
            "starter_code": '''import numpy as np
X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])\n# Your code here''',
            "expected_output": "Data normalized (max value: 1.0)",
            "solution": '''import numpy as np
X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
X_normalized = X / X.max()
print(f"Data normalized (max value: {X_normalized.max():.1f})")''',
            "difficulty": "beginner",
            "points": 40,
            "dataset": None
        },
        {
            "title": "One-Hot Encoding",
            "description": "Convert labels [0, 1, 2] to one-hot encoding.",
            "starter_code": '''import numpy as np
from tensorflow.keras.utils import to_categorical\n# Your code here''',
            "expected_output": "[[1. 0. 0.] [0. 1. 0.] [0. 0. 1.]]",
            "solution": '''import numpy as np
from tensorflow.keras.utils import to_categorical

labels = np.array([0, 1, 2])
one_hot = to_categorical(labels)
print(one_hot)''',
            "difficulty": "beginner",
            "points": 50,
            "dataset": None
        },
        {
            "title": "Simple Save/Load Model",
            "description": "Save a model to file and load it back.",
            "starter_code": '''from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras import layers
import os

model = Sequential([layers.Dense(1, input_shape=(1,))])\n# Your code here''',
            "expected_output": "Model successfully saved and loaded",
            "solution": '''from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras import layers
import os

model = Sequential([layers.Dense(1, input_shape=(1,))])
model.save('temp_model.h5')
loaded_model = load_model('temp_model.h5')
os.remove('temp_model.h5')
print("Model successfully saved and loaded")''',
            "difficulty": "beginner",
            "points": 60,
            "dataset": None
        }
    ]
    
    for p in problems:
        Problem.objects.get_or_create(
            title=p["title"],
            topic=dl_topic,
            dataset=p.get("dataset"),
            difficulty=p["difficulty"],
            description=p["description"],
            starter_code=p["starter_code"],
            expected_output=p["expected_output"],
            solution=p["solution"],
            points=p["points"],
            created_by=admin_user
        )
    
    print("20 more basic deep learning problems populated successfully!")

if __name__ == '__main__':
    populate()