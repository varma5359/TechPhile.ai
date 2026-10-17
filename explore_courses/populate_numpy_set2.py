from techphile_exams.explore_courses.populate_base import *

def populate():
    admin_user = get_admin_user()
    numpy_topic = Topic.objects.get_or_create(name="NumPy")[0]
    
    # More Basic NumPy Problems
    problems = [
        {
            "title": "Array with Linspace",
            "description": "Create an array with 5 evenly spaced numbers between 1 and 2.",
            "starter_code": "import numpy as np\n# Your code here",
            "solution": "arr = np.linspace(1, 2, 5)\nprint(arr)",
            "expected_output": "[1.   1.25 1.5  1.75 2.  ]",
            "difficulty": "beginner",
            "points": 50
        },
        {
            "title": "Array with Logspace",
            "description": "Create an array with 4 logarithmically spaced numbers between 10^1 and 10^2.",
            "starter_code": "import numpy as np\n# Your code here",
            "solution": "arr = np.logspace(1, 2, 4)\nprint(arr)",
            "expected_output": "[ 10.          21.5443469    46.41588834 100.        ]",
            "difficulty": "beginner",
            "points": 50
        },
        {
            "title": "Array with Full",
            "description": "Create a 2x2 array filled with 7s.",
            "starter_code": "import numpy as np\n# Your code here",
            "solution": "arr = np.full((2, 2), 7)\nprint(arr)",
            "expected_output": "[[7 7]\n [7 7]]",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Array with Diag",
            "description": "Create a diagonal matrix from a 1D array.",
            "starter_code": "import numpy as np\narr = np.array([1, 2, 3])\n# Your code here",
            "solution": "diag_arr = np.diag(arr)\nprint(diag_arr)",
            "expected_output": "[[1 0 0]\n [0 2 0]\n [0 0 3]]",
            "difficulty": "beginner",
            "points": 50
        },
        {
            "title": "Array Copy",
            "description": "Create a copy of an array (not a view).",
            "starter_code": '''import numpy as np
arr = np.array([1, 2, 3])

# Your code here''',
            "solution": "arr_copy = arr.copy()\nprint(arr_copy)",
            "expected_output": "[1 2 3]",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Array Transpose",
            "description": "Transpose a 2D array.",
            "starter_code": '''import numpy as np
arr = np.array([[1, 2], [3, 4], [5, 6]])

# Your code here''',
            "solution": "print(arr.T)",
            "expected_output": "[[1 3 5]\n [2 4 6]]",
            "difficulty": "beginner",
            "points": 50
        },
        {
            "title": "Array Flatten",
            "description": "Flatten a 2D array to 1D.",
            "starter_code": '''import numpy as np
arr = np.array([[1, 2], [3, 4]])

# Your code here''',
            "solution": "print(arr.flatten())",
            "expected_output": "[1 2 3 4]",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Array Ravel",
            "description": "Convert a 2D array to 1D using ravel.",
            "starter_code": '''import numpy as np
arr = np.array([[1, 2], [3, 4]])

# Your code here''',
            "solution": "print(arr.ravel())",
            "expected_output": "[1 2 3 4]",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Array Stack Vertically",
            "description": "Stack two 1D arrays vertically.",
            "starter_code": '''import numpy as np
arr1 = np.array([1, 2, 3])
arr2 = np.array([4, 5, 6])

# Your code here''',
            "solution": "print(np.vstack((arr1, arr2)))",
            "expected_output": "[[1 2 3]\n [4 5 6]]",
            "difficulty": "beginner",
            "points": 50
        },
        {
            "title": "Array Stack Horizontally",
            "description": "Stack two 1D arrays horizontally.",
            "starter_code": '''import numpy as np
arr1 = np.array([1, 2, 3])
arr2 = np.array([4, 5, 6])

# Your code here''',
            "solution": "print(np.hstack((arr1, arr2)))",
            "expected_output": "[1 2 3 4 5 6]",
            "difficulty": "beginner",
            "points": 50
        },
        {
            "title": "Array Split",
            "description": "Split a 1D array into 3 equal parts.",
            "starter_code": '''import numpy as np
arr = np.array([1, 2, 3, 4, 5, 6])

# Your code here''',
            "solution": "print(np.array_split(arr, 3))",
            "expected_output": "[array([1, 2]), array([3, 4]), array([5, 6])]",
            "difficulty": "beginner",
            "points": 50
        },
        {
            "title": "Array Unique Elements",
            "description": "Find unique elements in an array.",
            "starter_code": '''import numpy as np
arr = np.array([1, 2, 1, 3, 2, 4])

# Your code here''',
            "solution": "print(np.unique(arr))",
            "expected_output": "[1 2 3 4]",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Array Sorting",
            "description": "Sort an array in ascending order.",
            "starter_code": '''import numpy as np
arr = np.array([3, 1, 4, 2])

# Your code here''',
            "solution": "print(np.sort(arr))",
            "expected_output": "[1 2 3 4]",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Array Concatenation (Axis=1)",
            "description": "Concatenate two 2D arrays column-wise.",
            "starter_code": '''import numpy as np
arr1 = np.array([[1, 2], [3, 4]])
arr2 = np.array([[5, 6], [7, 8]])

# Your code here''',
            "solution": "print(np.concatenate((arr1, arr2), axis=1))",
            "expected_output": "[[1 2 5 6]\n [3 4 7 8]]",
            "difficulty": "beginner",
            "points": 50
        },
        {
            "title": "Array Standard Deviation",
            "description": "Calculate standard deviation of array elements.",
            "starter_code": '''import numpy as np
arr = np.array([1, 2, 3, 4])

# Your code here''',
            "solution": "print(np.std(arr))",
            "expected_output": "1.118033988749895",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Array Variance",
            "description": "Calculate variance of array elements.",
            "starter_code": '''import numpy as np
arr = np.array([1, 2, 3, 4])

# Your code here''',
            "solution": "print(np.var(arr))",
            "expected_output": "1.25",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Boolean Indexing",
            "description": "Select elements greater than 2 from an array.",
            "starter_code": '''import numpy as np
arr = np.array([1, 2, 3, 4, 5])

# Your code here''',
            "solution": "print(arr[arr > 2])",
            "expected_output": "[3 4 5]",
            "difficulty": "beginner",
            "points": 50
        },
        {
            "title": "Array Broadcasting",
            "description": "Add a scalar to each element of an array.",
            "starter_code": '''import numpy as np
arr = np.array([1, 2, 3])

# Your code here''',
            "solution": "print(arr + 5)",
            "expected_output": "[6 7 8]",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Array Comparison",
            "description": "Compare two arrays element-wise.",
            "starter_code": '''import numpy as np
arr1 = np.array([1, 2, 3])
arr2 = np.array([1, 4, 3])

# Your code here''',
            "solution": "print(arr1 == arr2)",
            "expected_output": "[ True False  True]",
            "difficulty": "beginner",
            "points": 40
        },
        {
            "title": "Array Slicing with Steps",
            "description": "Select every other element from an array.",
            "starter_code": '''import numpy as np
arr = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9])

# Your code here''',
            "solution": "print(arr[::2])",
            "expected_output": "[0 2 4 6 8]",
            "difficulty": "beginner",
            "points": 40
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
    
    print("✅ 20 More Basic NumPy problems populated.")

if __name__ == '__main__':
    populate()