from techphile_exams.explore_courses.populate_base import *

def populate():
    admin_user = get_admin_user()
    numpy_topic = Topic.objects.get_or_create(name="NumPy")[0]
    
    # Basic NumPy Problems
    problems = [
        {
            "title": "Create 1D Array",
            "description": "Create a 1D NumPy array with numbers 1 through 5.",
            "starter_code": "import numpy as np\n# Your code here",
            "solution": "arr = np.array([1, 2, 3, 4, 5])\nprint(arr)",
            "expected_output": "[1 2 3 4 5]",
            "difficulty": "beginner",
            "points": 30
        },
        {
            "title": "Create 2D Array",
            "description": "Create a 2x3 2D NumPy array with numbers 1 through 6.",
            "starter_code": "import numpy as np\n# Your code here",
            "solution": "arr = np.array([[1, 2, 3], [4, 5, 6]])\nprint(arr)",
            "expected_output": "[[1 2 3]\n [4 5 6]]",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Array with Zeros",
            "description": "Create a 3x3 array filled with zeros.",
            "starter_code": "import numpy as np\n# Your code here",
            "solution": "arr = np.zeros((3, 3))\nprint(arr)",
            "expected_output": "[[0. 0. 0.]\n [0. 0. 0.]\n [0. 0. 0.]]",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Array with Ones",
            "description": "Create a 2x4 array filled with ones.",
            "starter_code": "import numpy as np\n# Your code here",
            "solution": "arr = np.ones((2, 4))\nprint(arr)",
            "expected_output": "[[1. 1. 1. 1.]\n [1. 1. 1. 1.]]",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Identity Matrix",
            "description": "Create a 4x4 identity matrix.",
            "starter_code": "import numpy as np\n# Your code here",
            "solution": "arr = np.eye(4)\nprint(arr)",
            "expected_output": "[[1. 0. 0. 0.]\n [0. 1. 0. 0.]\n [0. 0. 1. 0.]\n [0. 0. 0. 1.]]",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Array with Range",
            "description": "Create an array with numbers from 0 to 9.",
            "starter_code": "import numpy as np\n# Your code here",
            "solution": "arr = np.arange(10)\nprint(arr)",
            "expected_output": "[0 1 2 3 4 5 6 7 8 9]",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Array with Step",
            "description": "Create an array with even numbers from 2 to 10.",
            "starter_code": "import numpy as np\n# Your code here",
            "solution": "arr = np.arange(2, 11, 2)\nprint(arr)",
            "expected_output": "[ 2  4  6  8 10]",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Random Array",
            "description": "Create a 1D array with 5 random numbers between 0 and 1.",
            "starter_code": "import numpy as np\n# Your code here",
            "solution": "arr = np.random.rand(5)\nprint(arr)",
            "expected_output": "5 random numbers between 0 and 1",
            "difficulty": "beginner",
            "points": 50
        },
        {
            "title": "Array Shape",
            "description": "Get the shape of a 2x3 array.",
            "starter_code": '''import numpy as np
arr = np.array([[1, 2, 3], [4, 5, 6]])

# Your code here''',
            "solution": "print(arr.shape)",
            "expected_output": "(2, 3)",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Reshape Array",
            "description": "Reshape a 1x6 array to 2x3.",
            "starter_code": '''import numpy as np
arr = np.array([1, 2, 3, 4, 5, 6])

# Your code here''',
            "solution": "reshaped = arr.reshape(2, 3)\nprint(reshaped)",
            "expected_output": "[[1 2 3]\n [4 5 6]]",
            "difficulty": "beginner",
            "points": 50
        },
        {
            "title": "Array Sum",
            "description": "Calculate the sum of all elements in an array.",
            "starter_code": '''import numpy as np
arr = np.array([1, 2, 3, 4])

# Your code here''',
            "solution": "print(np.sum(arr))",
            "expected_output": "10",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Array Mean",
            "description": "Calculate the mean of array elements.",
            "starter_code": '''import numpy as np
arr = np.array([1, 2, 3, 4])

# Your code here''',
            "solution": "print(np.mean(arr))",
            "expected_output": "2.5",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Array Max/Min",
            "description": "Find the maximum and minimum values in an array.",
            "starter_code": '''import numpy as np
arr = np.array([3, 1, 4, 2])

# Your code here''',
            "solution": "print(f'Max: {np.max(arr)}, Min: {np.min(arr)}')",
            "expected_output": "Max: 4, Min: 1",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Array Indexing",
            "description": "Access the 3rd element in a 1D array.",
            "starter_code": '''import numpy as np
arr = np.array([10, 20, 30, 40])

# Your code here''',
            "solution": "print(arr[2])",
            "expected_output": "30",
            "difficulty": "beginner",
            "points": 30
        },
        {
            "title": "Array Slicing",
            "description": "Get elements from index 1 to 3 in a 1D array.",
            "starter_code": '''import numpy as np
arr = np.array([10, 20, 30, 40, 50])

# Your code here''',
            "solution": "print(arr[1:4])",
            "expected_output": "[20 30 40]",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "2D Array Indexing",
            "description": "Access the element at row 1, column 2 in a 2D array.",
            "starter_code": '''import numpy as np
arr = np.array([[1, 2, 3], [4, 5, 6]])

# Your code here''',
            "solution": "print(arr[1, 2])",
            "expected_output": "6",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Array Concatenation",
            "description": "Concatenate two 1D arrays.",
            "starter_code": '''import numpy as np
arr1 = np.array([1, 2, 3])
arr2 = np.array([4, 5, 6])

# Your code here''',
            "solution": "print(np.concatenate((arr1, arr2)))",
            "expected_output": "[1 2 3 4 5 6]",
            "difficulty": "beginner",
            "points": 50
        },
        {
            "title": "Element-wise Addition",
            "description": "Add two arrays element-wise.",
            "starter_code": '''import numpy as np
arr1 = np.array([1, 2, 3])
arr2 = np.array([4, 5, 6])

# Your code here''',
            "solution": "print(arr1 + arr2)",
            "expected_output": "[5 7 9]",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Array Multiplication",
            "description": "Multiply each element in an array by 2.",
            "starter_code": '''import numpy as np
arr = np.array([1, 2, 3])

# Your code here''',
            "solution": "print(arr * 2)",
            "expected_output": "[2 4 6]",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Dot Product",
            "description": "Calculate the dot product of two arrays.",
            "starter_code": '''import numpy as np
arr1 = np.array([1, 2, 3])
arr2 = np.array([4, 5, 6])

# Your code here''',
            "solution": "print(np.dot(arr1, arr2))",
            "expected_output": "32",
            "difficulty": "beginner",
            "points": 50
        }
    ]

    # Create Problem entries
    for p in problems:
        Problem.objects.get_or_create(
            title=p["title"],
            topic=numpy_topic,
            dataset=None,
            difficulty=p["difficulty"],
            description=p["description"],
            starter_code=p["starter_code"],
            expected_output=p["expected_output"],
            solution=p["solution"],
            points=p["points"],
            created_by=admin_user
        )
    
    print("✅ 20 Basic NumPy problems populated.")

if __name__ == '__main__':
    populate()