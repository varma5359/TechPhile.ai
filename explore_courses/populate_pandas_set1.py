from techphile_exams.explore_courses.populate_base import *
import pandas as pd

def populate():
    admin_user = get_admin_user()
    pandas_topic = Topic.objects.get_or_create(name="Pandas")[0]
    
    # Sample datasets
    student_data = """name,age,grade,score
Alice,18,A,95
Bob,17,B,80
Charlie,19,C,70
David,18,B,85
Eve,17,A,90
"""
    student_dataset = create_dataset(
        "Student Grades", student_data, "students.csv",
        "Sample student grade data", admin_user
    )
    
    sales_data = """product,month,revenue
Widget,Jan,1000
Widget,Feb,1200
Gadget,Jan,800
Gadget,Feb,950
Tool,Jan,500
Tool,Feb,600
"""
    sales_dataset = create_dataset(
        "Sales Data", sales_data, "sales.csv",
        "Simple product sales data", admin_user
    )
    
    # Pandas Problems
    problems = [
        # Basic DataFrame Operations (1-5)
        {
            "title": "Load CSV File",
            "description": "Load the students.csv file into a pandas DataFrame.",
            "starter_code": '''# Your code here''',
            "expected_output": "DataFrame with 5 rows and 4 columns loaded",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')
print(f"DataFrame with {df.shape[0]} rows and {df.shape[1]} columns loaded")''',
            "difficulty": "beginner",
            "points": 20,
            "dataset": student_dataset
        },
        {
            "title": "Display First 3 Rows",
            "description": "Show the first 3 rows of the students DataFrame.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')\n# Your code here''',
            "expected_output": "First 3 rows displayed",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')
print(df.head(3))''',
            "difficulty": "beginner",
            "points": 20,
            "dataset": student_dataset
        },
        {
            "title": "Get DataFrame Shape",
            "description": "Print the shape (rows, columns) of the students DataFrame.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')\n# Your code here''',
            "expected_output": "(5, 4)",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')
print(df.shape)''',
            "difficulty": "beginner",
            "points": 20,
            "dataset": student_dataset
        },
        {
            "title": "Select Single Column",
            "description": "Select and display just the 'name' column from the students DataFrame.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')\n# Your code here''',
            "expected_output": "0      Alice\n1        Bob\n2    Charlie\n3      David\n4        Eve",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')
print(df['name'])''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": student_dataset
        },
        {
            "title": "Select Multiple Columns",
            "description": "Select and display just the 'name' and 'grade' columns.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')\n# Your code here''',
            "expected_output": "      name grade\n0    Alice     A\n1      Bob     B\n2  Charlie     C\n3    David     B\n4      Eve     A",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')
print(df[['name', 'grade']])''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": student_dataset
        },
        
        # Filtering and Sorting (6-10)
        {
            "title": "Filter Rows by Condition",
            "description": "Show students with score greater than 85.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')\n# Your code here''',
            "expected_output": "    name  age grade  score\n0  Alice   18     A     95\n4    Eve   17     A     90",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')
print(df[df['score'] > 85])''',
            "difficulty": "beginner",
            "points": 40,
            "dataset": student_dataset
        },
        {
            "title": "Sort by Column",
            "description": "Sort the students DataFrame by age in ascending order.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')\n# Your code here''',
            "expected_output": "      name  age grade  score\n1      Bob   17     B     80\n4      Eve   17     A     90\n0    Alice   18     A     95\n3    David   18     B     85\n2  Charlie   19     C     70",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')
print(df.sort_values('age'))''',
            "difficulty": "beginner",
            "points": 40,
            "dataset": student_dataset
        },
        {
            "title": "Sort Descending",
            "description": "Sort the students DataFrame by score in descending order.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')\n# Your code here''',
            "expected_output": "      name  age grade  score\n0    Alice   18     A     95\n4      Eve   17     A     90\n3    David   18     B     85\n1      Bob   17     B     80\n2  Charlie   19     C     70",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')
print(df.sort_values('score', ascending=False))''',
            "difficulty": "beginner",
            "points": 40,
            "dataset": student_dataset
        },
        {
            "title": "Filter with Multiple Conditions",
            "description": "Show students who are 18 years old AND have grade 'A'.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')\n# Your code here''',
            "expected_output": "    name  age grade  score\n0  Alice   18     A     95",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')
print(df[(df['age'] == 18) & (df['grade'] == 'A')])''',
            "difficulty": "beginner",
            "points": 50,
            "dataset": student_dataset
        },
        {
            "title": "Use isin() Method",
            "description": "Show students whose names are either Alice or Bob.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')\n# Your code here''',
            "expected_output": "    name  age grade  score\n0  Alice   18     A     95\n1    Bob   17     B     80",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')
print(df[df['name'].isin(['Alice', 'Bob'])])''',
            "difficulty": "beginner",
            "points": 50,
            "dataset": student_dataset
        },
        
        # Basic Analysis (11-15)
        {
            "title": "Calculate Mean Score",
            "description": "Calculate and print the average score of all students.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')\n# Your code here''',
            "expected_output": "84.0",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')
print(df['score'].mean())''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": student_dataset
        },
        {
            "title": "Find Maximum Age",
            "description": "Find and print the maximum age in the students DataFrame.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')\n# Your code here''',
            "expected_output": "19",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')
print(df['age'].max())''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": student_dataset
        },
        {
            "title": "Count Students by Grade",
            "description": "Count how many students have each grade.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')\n# Your code here''',
            "expected_output": "A    2\nB    2\nC    1",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')
print(df['grade'].value_counts())''',
            "difficulty": "beginner",
            "points": 40,
            "dataset": student_dataset
        },
        {
            "title": "Group by and Mean",
            "description": "Calculate average score by grade.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')\n# Your code here''',
            "expected_output": "grade\nA    92.5\nB    82.5\nC    70.0",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')
print(df.groupby('grade')['score'].mean())''',
            "difficulty": "beginner",
            "points": 50,
            "dataset": student_dataset
        },
        {
            "title": "Basic Pivot Table",
            "description": "Create a pivot table showing total revenue by product and month.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/sales.csv')\n# Your code here''',
            "expected_output": "month    Feb   Jan\nproduct           \nGadget   950   800\nTool     600   500\nWidget  1200  1000",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/sales.csv')
print(pd.pivot_table(df, values='revenue', index='product', columns='month', aggfunc='sum'))''',
            "difficulty": "beginner",
            "points": 60,
            "dataset": sales_dataset
        },
        
        # Data Manipulation (16-20)
        {
            "title": "Add New Column",
            "description": "Add a new column 'passing' that is True if score >= 80.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')\n# Your code here''',
            "expected_output": "      name  age grade  score  passing\n0    Alice   18     A     95     True\n1      Bob   17     B     80     True\n2  Charlie   19     C     70    False\n3    David   18     B     85     True\n4      Eve   17     A     90     True",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')
df['passing'] = df['score'] >= 80
print(df)''',
            "difficulty": "beginner",
            "points": 50,
            "dataset": student_dataset
        },
        {
            "title": "Rename Columns",
            "description": "Rename the 'grade' column to 'letter_grade'.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')\n# Your code here''',
            "expected_output": "      name  age letter_grade  score\n0    Alice   18            A     95\n1      Bob   17            B     80\n2  Charlie   19            C     70\n3    David   18            B     85\n4      Eve   17            A     90",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')
df = df.rename(columns={'grade': 'letter_grade'})
print(df)''',
            "difficulty": "beginner",
            "points": 40,
            "dataset": student_dataset
        },
        {
            "title": "Drop Column",
            "description": "Drop the 'age' column from the DataFrame.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')\n# Your code here''',
            "expected_output": "      name grade  score\n0    Alice     A     95\n1      Bob     B     80\n2  Charlie     C     70\n3    David     B     85\n4      Eve     A     90",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')
df = df.drop('age', axis=1)
print(df)''',
            "difficulty": "beginner",
            "points": 40,
            "dataset": student_dataset
        },
        {
            "title": "Handle Missing Data",
            "description": "Fill missing values in a DataFrame with 0.",
            "starter_code": '''import pandas as pd
import numpy as np

df = pd.DataFrame({'A': [1, 2, np.nan], 'B': [np.nan, 1, 1]})\n# Your code here''',
            "expected_output": "     A    B\n0  1.0  0.0\n1  2.0  1.0\n2  0.0  1.0",
            "solution": '''import pandas as pd
import numpy as np

df = pd.DataFrame({'A': [1, 2, np.nan], 'B': [np.nan, 1, 1]})
df = df.fillna(0)
print(df)''',
            "difficulty": "beginner",
            "points": 50,
            "dataset": None
        },
        {
            "title": "Apply Simple Function",
            "description": "Create a new column with score percentages (score/100).",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')\n# Your code here''',
            "expected_output": "      name  age grade  score  percentage\n0    Alice   18     A     95        0.95\n1      Bob   17     B     80        0.80\n2  Charlie   19     C     70        0.70\n3    David   18     B     85        0.85\n4      Eve   17     A     90        0.90",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/students.csv')
df['percentage'] = df['score'].apply(lambda x: x/100)
print(df)''',
            "difficulty": "beginner",
            "points": 50,
            "dataset": student_dataset
        }
    ]
    
    for p in problems:
        Problem.objects.get_or_create(
            title=p["title"],
            topic=pandas_topic,
            dataset=p.get("dataset"),
            difficulty=p["difficulty"],
            description=p["description"],
            starter_code=p["starter_code"],
            expected_output=p["expected_output"],
            solution=p["solution"],
            points=p["points"],
            created_by=admin_user
        )
    
    print("20 basic pandas problems populated successfully!")

if __name__ == '__main__':
    populate()