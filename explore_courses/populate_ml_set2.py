from techphile_exams.explore_courses.populate_base import *
import pandas as pd
import numpy as np

def populate():
    admin_user = get_admin_user()
    ml_topic = Topic.objects.get_or_create(name="ML")[0]
    
    # House Prices Dataset
    house_data = """size_sqft,bedrooms,bathrooms,price
1500,3,2,300000
2000,4,3,400000
1200,2,1,250000
1800,3,2,350000
2400,4,3,450000
"""
    house_dataset = create_dataset(
        "House Prices", house_data, "houses.csv",
        "Simple house pricing data", admin_user
    )
    
    # Student Scores Dataset
    student_data = """hours_studied,previous_score,extra_activities,final_score
5,75,1,85
3,60,0,65
7,85,1,90
2,50,0,55
6,80,1,88
"""
    student_dataset = create_dataset(
        "Student Performance", student_data, "students.csv",
        "Student study habits and exam scores", admin_user
    )
    
    # Wine Quality Dataset (Simplified)
    wine_data = """alcohol,volatile_acidity,sulphates,quality
9.4,0.7,0.56,5
10.1,0.3,0.64,7
9.8,0.5,0.68,6
11.2,0.4,0.72,8
10.6,0.6,0.58,6
"""
    wine_dataset = create_dataset(
        "Wine Quality", wine_data, "wine.csv",
        "Chemical properties affecting wine quality", admin_user
    )
    
    # Basic ML Problems
    problems = [
        # Basic Data Manipulation (1-5)
        {
            "title": "Load and Display Specific Columns",
            "description": "Load the house prices dataset and display only 'size_sqft' and 'price' columns.",
            "starter_code": '''import pandas as pd\ndf = pd.read_csv('/datasets/houses.csv')\n# Your code here''',
            "expected_output": "   size_sqft    price\n0       1500   300000\n1       2000   400000\n2       1200   250000\n3       1800   350000\n4       2400   450000",
            "solution": '''import pandas as pd\ndf = pd.read_csv('/datasets/houses.csv')\nprint(df[['size_sqft', 'price']])''',
            "difficulty": "beginner",
            "points": 50,
            "dataset": house_dataset
        },
        {
            "title": "Calculate Price per Sqft",
            "description": "Add a new column 'price_per_sqft' to the house prices dataset and display the result.",
            "starter_code": '''import pandas as pd\ndf = pd.read_csv('/datasets/houses.csv')\n# Your code here''',
            "expected_output": "   size_sqft  bedrooms  bathrooms    price  price_per_sqft\n0       1500         3          2   300000      200.000000\n1       2000         4          3   400000      200.000000\n2       1200         2          1   250000      208.333333\n3       1800         3          2   350000      194.444444\n4       2400         4          3   450000      187.500000",
            "solution": '''import pandas as pd\ndf = pd.read_csv('/datasets/houses.csv')\ndf['price_per_sqft'] = df['price'] / df['size_sqft']\nprint(df)''',
            "difficulty": "beginner",
            "points": 75,
            "dataset": house_dataset
        },
        {
            "title": "Filter Records by Condition",
            "description": "Display houses with more than 3 bedrooms from the dataset.",
            "starter_code": '''import pandas as pd\ndf = pd.read_csv('/datasets/houses.csv')\n# Your code here''',
            "expected_output": "   size_sqft  bedrooms  bathrooms    price\n1       2000         4          3   400000\n4       2400         4          3   450000",
            "solution": '''import pandas as pd\ndf = pd.read_csv('/datasets/houses.csv')\nprint(df[df['bedrooms'] > 3])''',
            "difficulty": "beginner",
            "points": 75,
            "dataset": house_dataset
        },
        {
            "title": "Calculate Correlation Matrix",
            "description": "Calculate and display the correlation matrix for the student performance dataset.",
            "starter_code": '''import pandas as pd\ndf = pd.read_csv('/datasets/students.csv')\n# Your code here''',
            "expected_output": "                hours_studied  previous_score  extra_activities  final_score\nhours_studied        1.000000        0.806796          0.500000     0.986689\nprevious_score       0.806796        1.000000          0.327327     0.843274\nextra_activities     0.500000        0.327327          1.000000     0.469041\nfinal_score          0.986689        0.843274          0.469041     1.000000",
            "solution": '''import pandas as pd\ndf = pd.read_csv('/datasets/students.csv')\nprint(df.corr())''',
            "difficulty": "beginner",
            "points": 75,
            "dataset": student_dataset
        },
        {
            "title": "Group and Aggregate Data",
            "description": "Calculate the average final score by extra_activities status from the student dataset.",
            "starter_code": '''import pandas as pd\ndf = pd.read_csv('/datasets/students.csv')\n# Your code here''',
            "expected_output": "extra_activities\n0    60.0\n1    87.666667\nName: final_score, dtype: float64",
            "solution": '''import pandas as pd\ndf = pd.read_csv('/datasets/students.csv')\nprint(df.groupby('extra_activities')['final_score'].mean())''',
            "difficulty": "beginner",
            "points": 100,
            "dataset": student_dataset
        },
        
        # Basic Visualization (6-10)
        {
            "title": "Create a Simple Scatter Plot",
            "description": "Create a scatter plot of size_sqft vs price from the house prices dataset.",
            "starter_code": '''import pandas as pd\nimport matplotlib.pyplot as plt\n\ndf = pd.read_csv('/datasets/houses.csv')\n# Your code here''',
            "expected_output": "Displayed scatter plot of house size vs price",
            "solution": '''import pandas as pd\nimport matplotlib.pyplot as plt\n\ndf = pd.read_csv('/datasets/houses.csv')\ndf.plot.scatter(x='size_sqft', y='price')\nplt.show()''',
            "difficulty": "beginner",
            "points": 100,
            "dataset": house_dataset
        },
        {
            "title": "Plot a Histogram",
            "description": "Plot a histogram of final scores from the student dataset with 3 bins.",
            "starter_code": '''import pandas as pd\nimport matplotlib.pyplot as plt\n\ndf = pd.read_csv('/datasets/students.csv')\n# Your code here''',
            "expected_output": "Displayed histogram of final scores with 3 bins",
            "solution": '''import pandas as pd\nimport matplotlib.pyplot as plt\n\ndf = pd.read_csv('/datasets/students.csv')\ndf['final_score'].plot.hist(bins=3)\nplt.show()''',
            "difficulty": "beginner",
            "points": 75,
            "dataset": student_dataset
        },
        {
            "title": "Create a Bar Chart",
            "description": "Create a bar chart showing average price by number of bedrooms.",
            "starter_code": '''import pandas as pd\nimport matplotlib.pyplot as plt\n\ndf = pd.read_csv('/datasets/houses.csv')\n# Your code here''',
            "expected_output": "Displayed bar chart of average price by bedrooms",
            "solution": '''import pandas as pd\nimport matplotlib.pyplot as plt\n\ndf = pd.read_csv('/datasets/houses.csv')\ndf.groupby('bedrooms')['price'].mean().plot.bar()\nplt.show()''',
            "difficulty": "beginner",
            "points": 100,
            "dataset": house_dataset
        },
        {
            "title": "Box Plot of Wine Quality",
            "description": "Create a box plot showing alcohol distribution by wine quality.",
            "starter_code": '''import pandas as pd\nimport matplotlib.pyplot as plt\n\ndf = pd.read_csv('/datasets/wine.csv')\n# Your code here''',
            "expected_output": "Displayed box plot of alcohol by wine quality",
            "solution": '''import pandas as pd\nimport matplotlib.pyplot as plt\n\ndf = pd.read_csv('/datasets/wine.csv')\ndf.boxplot(column='alcohol', by='quality')\nplt.show()''',
            "difficulty": "beginner",
            "points": 100,
            "dataset": wine_dataset
        },
        {
            "title": "Plot Multiple Features",
            "description": "Create scatter plots of hours_studied vs final_score and previous_score vs final_score side by side.",
            "starter_code": '''import pandas as pd\nimport matplotlib.pyplot as plt\n\ndf = pd.read_csv('/datasets/students.csv')\n# Your code here''',
            "expected_output": "Displayed two scatter plots side by side",
            "solution": '''import pandas as pd\nimport matplotlib.pyplot as plt\n\ndf = pd.read_csv('/datasets/students.csv')\n\nplt.figure(figsize=(10,4))\nplt.subplot(1,2,1)\ndf.plot.scatter(x='hours_studied', y='final_score')\n\nplt.subplot(1,2,2)\ndf.plot.scatter(x='previous_score', y='final_score')\n\nplt.show()''',
            "difficulty": "beginner",
            "points": 125,
            "dataset": student_dataset
        },
        
        # Basic Modeling (11-15)
        {
            "title": "Simple Linear Regression",
            "description": "Train a linear regression model to predict house price based on size.",
            "starter_code": '''from sklearn.linear_model import LinearRegression\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/houses.csv')\nX = df[['size_sqft']]\ny = df['price']\n\n# Your code here''',
            "expected_output": "Linear regression model trained with coefficient: [183.33]",
            "solution": '''from sklearn.linear_model import LinearRegression\nimport pandas as pd\nimport numpy as np\n\ndf = pd.read_csv('/datasets/houses.csv')\nX = df[['size_sqft']]\ny = df['price']\n\nmodel = LinearRegression()\nmodel.fit(X, y)\nprint(f"Linear regression model trained with coefficient: {np.round(model.coef_, 2)}")''',
            "difficulty": "beginner",
            "points": 150,
            "dataset": house_dataset
        },
        {
            "title": "Predict Student Scores",
            "description": "Use linear regression to predict final_score based on hours_studied.",
            "starter_code": '''from sklearn.linear_model import LinearRegression\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/students.csv')\nX = df[['hours_studied']]\ny = df['final_score']\n\n# Your code here''',
            "expected_output": "Predicted score for 4 hours: [73.33]",
            "solution": '''from sklearn.linear_model import LinearRegression\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/students.csv')\nX = df[['hours_studied']]\ny = df['final_score']\n\nmodel = LinearRegression()\nmodel.fit(X, y)\npred = model.predict([[4]])\nprint(f"Predicted score for 4 hours: {np.round(pred, 2)}")''',
            "difficulty": "beginner",
            "points": 150,
            "dataset": student_dataset
        },
        {
            "title": "Train-Test Split Practice",
            "description": "Split the wine dataset into 80% train and 20% test sets and print their shapes.",
            "starter_code": '''from sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/wine.csv')\n# Your code here''',
            "expected_output": "Train set: (4, 4)\nTest set: (1, 4)",
            "solution": '''from sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/wine.csv')\ntrain, test = train_test_split(df, test_size=0.2)\nprint(f"Train set: {train.shape}")\nprint(f"Test set: {test.shape}")''',
            "difficulty": "beginner",
            "points": 100,
            "dataset": wine_dataset
        },
        {
            "title": "KNN Classifier Basics",
            "description": "Train a KNN classifier to predict wine quality (threshold: >=7 is good) using alcohol and sulphates.",
            "starter_code": '''from sklearn.neighbors import KNeighborsClassifier\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/wine.csv')\ndf['quality_label'] = df['quality'].apply(lambda x: 1 if x >=7 else 0)\nX = df[['alcohol', 'sulphates']]\ny = df['quality_label']\n\n# Your code here''',
            "expected_output": "KNN classifier trained with accuracy: 1.00",
            "solution": '''from sklearn.neighbors import KNeighborsClassifier\nfrom sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/wine.csv')\ndf['quality_label'] = df['quality'].apply(lambda x: 1 if x >=7 else 0)\nX = df[['alcohol', 'sulphates']]\ny = df['quality_label']\n\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)\nmodel = KNeighborsClassifier(n_neighbors=3)\nmodel.fit(X_train, y_train)\nscore = model.score(X_test, y_test)\nprint(f"KNN classifier trained with accuracy: {score:.2f}")''',
            "difficulty": "beginner",
            "points": 150,
            "dataset": wine_dataset
        },
        {
            "title": "Decision Tree Basics",
            "description": "Train a decision tree to predict if students did extra activities based on their scores.",
            "starter_code": '''from sklearn.tree import DecisionTreeClassifier\nfrom sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/students.csv')\nX = df[['hours_studied', 'previous_score', 'final_score']]\ny = df['extra_activities']\n\n# Your code here''',
            "expected_output": "Decision tree trained with accuracy: [value]",
            "solution": '''from sklearn.tree import DecisionTreeClassifier\nfrom sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/students.csv')\nX = df[['hours_studied', 'previous_score', 'final_score']]\ny = df['extra_activities']\n\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)\nmodel = DecisionTreeClassifier()\nmodel.fit(X_train, y_train)\nscore = model.score(X_test, y_test)\nprint(f"Decision tree trained with accuracy: {score:.2f}")''',
            "difficulty": "beginner",
            "points": 150,
            "dataset": student_dataset
        },
        
        # Evaluation Metrics (16-20)
        {
            "title": "Calculate Mean Absolute Error",
            "description": "Calculate MAE for a linear regression model predicting house prices.",
            "starter_code": '''from sklearn.linear_model import LinearRegression\nfrom sklearn.metrics import mean_absolute_error\nfrom sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/houses.csv')\nX = df[['size_sqft']]\ny = df['price']\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)\n\nmodel = LinearRegression()\nmodel.fit(X_train, y_train)\ny_pred = model.predict(X_test)\n\n# Your code here''',
            "expected_output": "MAE: [value]",
            "solution": '''from sklearn.linear_model import LinearRegression\nfrom sklearn.metrics import mean_absolute_error\nfrom sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/houses.csv')\nX = df[['size_sqft']]\ny = df['price']\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)\n\nmodel = LinearRegression()\nmodel.fit(X_train, y_train)\ny_pred = model.predict(X_test)\n\nmae = mean_absolute_error(y_test, y_pred)\nprint(f"MAE: {mae:.2f}")''',
            "difficulty": "beginner",
            "points": 125,
            "dataset": house_dataset
        },
        {
            "title": "Calculate Accuracy Score",
            "description": "Calculate accuracy for a wine quality classifier (good/bad).",
            "starter_code": '''from sklearn.neighbors import KNeighborsClassifier\nfrom sklearn.metrics import accuracy_score\nfrom sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/wine.csv')\ndf['quality_label'] = df['quality'].apply(lambda x: 1 if x >=7 else 0)\nX = df[['alcohol', 'sulphates']]\ny = df['quality_label']\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)\n\nmodel = KNeighborsClassifier(n_neighbors=3)\nmodel.fit(X_train, y_train)\ny_pred = model.predict(X_test)\n\n# Your code here''',
            "expected_output": "Accuracy: [value]",
            "solution": '''from sklearn.neighbors import KNeighborsClassifier\nfrom sklearn.metrics import accuracy_score\nfrom sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/wine.csv')\ndf['quality_label'] = df['quality'].apply(lambda x: 1 if x >=7 else 0)\nX = df[['alcohol', 'sulphates']]\ny = df['quality_label']\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)\n\nmodel = KNeighborsClassifier(n_neighbors=3)\nmodel.fit(X_train, y_train)\ny_pred = model.predict(X_test)\n\nacc = accuracy_score(y_test, y_pred)\nprint(f"Accuracy: {acc:.2f}")''',
            "difficulty": "beginner",
            "points": 125,
            "dataset": wine_dataset
        },
        {
            "title": "Confusion Matrix Basics",
            "description": "Create a confusion matrix for the student extra activities classifier.",
            "starter_code": '''from sklearn.tree import DecisionTreeClassifier\nfrom sklearn.metrics import confusion_matrix\nfrom sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/students.csv')\nX = df[['hours_studied', 'final_score']]\ny = df['extra_activities']\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)\n\nmodel = DecisionTreeClassifier()\nmodel.fit(X_train, y_train)\ny_pred = model.predict(X_test)\n\n# Your code here''',
            "expected_output": "[[1 0]\n [0 0]]",
            "solution": '''from sklearn.tree import DecisionTreeClassifier\nfrom sklearn.metrics import confusion_matrix\nfrom sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/students.csv')\nX = df[['hours_studied', 'final_score']]\ny = df['extra_activities']\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)\n\nmodel = DecisionTreeClassifier()\nmodel.fit(X_train, y_train)\ny_pred = model.predict(X_test)\n\nprint(confusion_matrix(y_test, y_pred))''',
            "difficulty": "beginner",
            "points": 125,
            "dataset": student_dataset
        },
        {
            "title": "Precision and Recall",
            "description": "Calculate precision and recall for the wine quality classifier.",
            "starter_code": '''from sklearn.neighbors import KNeighborsClassifier\nfrom sklearn.metrics import precision_score, recall_score\nfrom sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/wine.csv')\ndf['quality_label'] = df['quality'].apply(lambda x: 1 if x >=7 else 0)\nX = df[['alcohol', 'volatile_acidity']]\ny = df['quality_label']\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)\n\nmodel = KNeighborsClassifier(n_neighbors=3)\nmodel.fit(X_train, y_train)\ny_pred = model.predict(X_test)\n\n# Your code here''',
            "expected_output": "Precision: [value]\nRecall: [value]",
            "solution": '''from sklearn.neighbors import KNeighborsClassifier\nfrom sklearn.metrics import precision_score, recall_score\nfrom sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/wine.csv')\ndf['quality_label'] = df['quality'].apply(lambda x: 1 if x >=7 else 0)\nX = df[['alcohol', 'volatile_acidity']]\ny = df['quality_label']\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)\n\nmodel = KNeighborsClassifier(n_neighbors=3)\nmodel.fit(X_train, y_train)\ny_pred = model.predict(X_test)\n\nprecision = precision_score(y_test, y_pred)\nrecall = recall_score(y_test, y_pred)\nprint(f"Precision: {precision:.2f}")\nprint(f"Recall: {recall:.2f}")''',
            "difficulty": "beginner",
            "points": 150,
            "dataset": wine_dataset
        },
        {
            "title": "Classification Report",
            "description": "Generate a classification report for the student activities classifier.",
            "starter_code": '''from sklearn.tree import DecisionTreeClassifier\nfrom sklearn.metrics import classification_report\nfrom sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/students.csv')\nX = df[['hours_studied', 'final_score']]\ny = df['extra_activities']\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)\n\nmodel = DecisionTreeClassifier()\nmodel.fit(X_train, y_train)\ny_pred = model.predict(X_test)\n\n# Your code here''',
            "expected_output": "              precision    recall  f1-score   support\n\n           0       1.00      1.00      1.00         1\n           1       0.00      0.00      0.00         0\n\n    accuracy                           1.00         1\n   macro avg       0.50      0.50      0.50         1\nweighted avg       1.00      1.00      1.00         1",
            "solution": '''from sklearn.tree import DecisionTreeClassifier\nfrom sklearn.metrics import classification_report\nfrom sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/students.csv')\nX = df[['hours_studied', 'final_score']]\ny = df['extra_activities']\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)\n\nmodel = DecisionTreeClassifier()\nmodel.fit(X_train, y_train)\ny_pred = model.predict(X_test)\n\nprint(classification_report(y_test, y_pred))''',
            "difficulty": "beginner",
            "points": 150,
            "dataset": student_dataset
        }
    ]
    
    for p in problems:
        Problem.objects.get_or_create(
            title=p["title"],
            topic=ml_topic,
            dataset=p.get("dataset"),
            difficulty=p["difficulty"],
            description=p["description"],
            starter_code=p["starter_code"],
            expected_output=p["expected_output"],
            solution=p["solution"],
            points=p["points"],
            created_by=admin_user
        )
    
    print("20 additional basic ML problems populated successfully!")

if __name__ == '__main__':
    populate()