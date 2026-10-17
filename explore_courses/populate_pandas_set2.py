from techphile_exams.explore_courses.populate_base import *
import pandas as pd

def populate():
    admin_user = get_admin_user()
    pandas_topic = Topic.objects.get_or_create(name="Pandas")[0]
    
    # Sample datasets
    employee_data = """id,name,department,salary
1,John,HR,50000
2,Sarah,IT,65000
3,Mike,IT,70000
4,Lisa,HR,55000
5,David,Finance,60000
"""
    employee_dataset = create_dataset(
        "Employee Data", employee_data, "employees.csv",
        "Sample employee records", admin_user
    )
    
    product_data = """product_id,name,category,price,stock
1001,Laptop,Electronics,999,15
1002,Phone,Electronics,699,30
1003,Desk,Furniture,250,10
1004,Chair,Furniture,120,25
1005,Printer,Electronics,200,8
"""
    product_dataset = create_dataset(
        "Product Inventory", product_data, "products.csv",
        "Simple product inventory data", admin_user
    )
    
    # Pandas Problems
    problems = [
        # Basic Inspection (1-5)
        {
            "title": "Show DataFrame Info",
            "description": "Display the info() of the employees DataFrame.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/employees.csv')\n# Your code here''',
            "expected_output": "<class 'pandas.core.frame.DataFrame'>\nRangeIndex: 5 entries, 0 to 4\nData columns (total 4 columns)...",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/employees.csv')
print(df.info())''',
            "difficulty": "beginner",
            "points": 20,
            "dataset": employee_dataset
        },
        {
            "title": "Display Column Names",
            "description": "Print the column names of the employees DataFrame.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/employees.csv')\n# Your code here''',
            "expected_output": "Index(['id', 'name', 'department', 'salary'], dtype='object')",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/employees.csv')
print(df.columns)''',
            "difficulty": "beginner",
            "points": 20,
            "dataset": employee_dataset
        },
        {
            "title": "Show Data Types",
            "description": "Display the data types of each column in the products DataFrame.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/products.csv')\n# Your code here''',
            "expected_output": "product_id      int64\nname          object\ncategory      object\nprice          int64\nstock          int64",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/products.csv')
print(df.dtypes)''',
            "difficulty": "beginner",
            "points": 20,
            "dataset": product_dataset
        },
        {
            "title": "Count Non-Null Values",
            "description": "Count non-null values in each column of the products DataFrame.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/products.csv')\n# Your code here''',
            "expected_output": "product_id    5\nname          5\ncategory      5\nprice         5\nstock         5",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/products.csv')
print(df.count())''',
            "difficulty": "beginner",
            "points": 20,
            "dataset": product_dataset
        },
        {
            "title": "Display Last 2 Rows",
            "description": "Show the last 2 rows of the products DataFrame.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/products.csv')\n# Your code here''',
            "expected_output": "   product_id     name    category  price  stock\n3        1004    Chair   Furniture    120     25\n4        1005  Printer  Electronics    200      8",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/products.csv')
print(df.tail(2))''',
            "difficulty": "beginner",
            "points": 20,
            "dataset": product_dataset
        },
        
        # Selection and Indexing (6-10)
        {
            "title": "Select Row by Index",
            "description": "Select and display the row at index 2 from the employees DataFrame.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/employees.csv')\n# Your code here''',
            "expected_output": "id          3\nname     Mike\ndepartment IT\nsalary  70000",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/employees.csv')
print(df.iloc[2])''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": employee_dataset
        },
        {
            "title": "Select Cell by Row/Column",
            "description": "Select the salary of employee at index 1 (second row).",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/employees.csv')\n# Your code here''',
            "expected_output": "65000",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/employees.csv')
print(df.iloc[1]['salary'])''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": employee_dataset
        },
        {
            "title": "Select Rows by Position",
            "description": "Select first 3 rows of the products DataFrame.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/products.csv')\n# Your code here''',
            "expected_output": "   product_id   name    category  price  stock\n0        1001  Laptop  Electronics    999     15\n1        1002   Phone  Electronics    699     30\n2        1003    Desk   Furniture    250     10",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/products.csv')
print(df.iloc[:3])''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": product_dataset
        },
        {
            "title": "Select Columns by Position",
            "description": "Select first 2 columns of the employees DataFrame.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/employees.csv')\n# Your code here''',
            "expected_output": "   id   name\n0   1   John\n1   2  Sarah\n2   3   Mike\n3   4   Lisa\n4   5  David",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/employees.csv')
print(df.iloc[:, :2])''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": employee_dataset
        },
        {
            "title": "Select Specific Rows and Columns",
            "description": "Select name and price for first 2 products.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/products.csv')\n# Your code here''',
            "expected_output": "    name  price\n0  Laptop    999\n1   Phone    699",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/products.csv')
print(df.loc[:1, ['name', 'price']])''',
            "difficulty": "beginner",
            "points": 40,
            "dataset": product_dataset
        },
        
        # Basic Operations (11-15)
        {
            "title": "Calculate Total Salary",
            "description": "Calculate the total salary of all employees.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/employees.csv')\n# Your code here''',
            "expected_output": "300000",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/employees.csv')
print(df['salary'].sum())''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": employee_dataset
        },
        {
            "title": "Find Average Price",
            "description": "Calculate the average price of all products.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/products.csv')\n# Your code here''',
            "expected_output": "453.6",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/products.csv')
print(df['price'].mean())''',
            "difficulty": "beginner",
            "points": 30,
            "dataset": product_dataset
        },
        {
            "title": "Count Products by Category",
            "description": "Count how many products are in each category.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/products.csv')\n# Your code here''',
            "expected_output": "category\nElectronics    3\nFurniture      2",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/products.csv')
print(df['category'].value_counts())''',
            "difficulty": "beginner",
            "points": 40,
            "dataset": product_dataset
        },
        {
            "title": "Find Minimum Stock",
            "description": "Find the product with the lowest stock quantity.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/products.csv')\n# Your code here''',
            "expected_output": "   product_id     name    category  price  stock\n4        1005  Printer  Electronics    200      8",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/products.csv')
print(df[df['stock'] == df['stock'].min()])''',
            "difficulty": "beginner",
            "points": 40,
            "dataset": product_dataset
        },
        {
            "title": "Calculate Total Inventory Value",
            "description": "Calculate total value (price * stock) for each product.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/products.csv')\n# Your code here''',
            "expected_output": "0    14985\n1    20970\n2     2500\n3     3000\n4     1600",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/products.csv')
print(df['price'] * df['stock'])''',
            "difficulty": "beginner",
            "points": 50,
            "dataset": product_dataset
        },
        
        # Data Manipulation (16-20)
        {
            "title": "Add New Employee",
            "description": "Add a new employee to the DataFrame.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/employees.csv')\n# Your code here''',
            "expected_output": "   id   name department  salary\n0   1   John         HR   50000\n1   2  Sarah         IT   65000\n2   3   Mike         IT   70000\n3   4   Lisa         HR   55000\n4   5  David     Finance   60000\n5   6   Emma     Finance   58000",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/employees.csv')
new_employee = pd.DataFrame({'id': [6], 'name': ['Emma'], 
                           'department': ['Finance'], 'salary': [58000]})
df = pd.concat([df, new_employee], ignore_index=True)
print(df)''',
            "difficulty": "beginner",
            "points": 50,
            "dataset": employee_dataset
        },
        {
            "title": "Update Employee Salary",
            "description": "Increase John's salary by 10%.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/employees.csv')\n# Your code here''',
            "expected_output": "   id   name department  salary\n0   1   John         HR   55000\n1   2  Sarah         IT   65000\n2   3   Mike         IT   70000\n3   4   Lisa         HR   55000\n4   5  David     Finance   60000",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/employees.csv')
df.loc[df['name'] == 'John', 'salary'] *= 1.1
print(df)''',
            "difficulty": "beginner",
            "points": 50,
            "dataset": employee_dataset
        },
        {
            "title": "Delete Row by Index",
            "description": "Remove the employee at index 3 from the DataFrame.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/employees.csv')\n# Your code here''',
            "expected_output": "   id   name department  salary\n0   1   John         HR   50000\n1   2  Sarah         IT   65000\n2   3   Mike         IT   70000\n4   5  David     Finance   60000",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/employees.csv')
df = df.drop(3)
print(df)''',
            "difficulty": "beginner",
            "points": 40,
            "dataset": employee_dataset
        },
        {
            "title": "Filter and Select Columns",
            "description": "Show names of IT department employees.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/employees.csv')\n# Your code here''',
            "expected_output": "1    Sarah\n2     Mike",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/employees.csv')
print(df[df['department'] == 'IT']['name'])''',
            "difficulty": "beginner",
            "points": 40,
            "dataset": employee_dataset
        },
        {
            "title": "Rename Index",
            "description": "Change the DataFrame index to employee IDs.",
            "starter_code": '''import pandas as pd
df = pd.read_csv('/datasets/employees.csv')\n# Your code here''',
            "expected_output": "   name department  salary\nid                        \n1   John         HR   50000\n2  Sarah         IT   65000\n3   Mike         IT   70000\n4   Lisa         HR   55000\n5  David     Finance   60000",
            "solution": '''import pandas as pd
df = pd.read_csv('/datasets/employees.csv')
df = df.set_index('id')
print(df)''',
            "difficulty": "beginner",
            "points": 40,
            "dataset": employee_dataset
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
    
    print("20 more basic pandas problems populated successfully!")

if __name__ == '__main__':
    populate()