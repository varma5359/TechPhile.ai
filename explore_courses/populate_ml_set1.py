from techphile_exams.explore_courses.populate_base import *
import pandas as pd
import numpy as np

def populate():
    admin_user = get_admin_user()
    ml_topic = Topic.objects.get_or_create(name="ML")[0]
    
    # Titanic Dataset
    titanic_data = """PassengerId,Survived,Pclass,Name,Sex,Age,SibSp,Parch,Fare
1,0,3,Braund,male,22,1,0,7.25
2,1,1,Cumings,female,38,1,0,71.28
3,1,3,Heikkinen,female,26,0,0,7.92
4,1,1,Futrelle,female,35,1,0,53.1
5,0,3,Allen,male,35,0,0,8.05
"""
    titanic_dataset = create_dataset(
        "Titanic Dataset", titanic_data, "titanic.csv",
        "Survival data from Titanic shipwreck", admin_user
    )
    
    # Iris Dataset
    iris_data = """sepal_length,sepal_width,petal_length,petal_width,species
5.1,3.5,1.4,0.2,setosa
4.9,3.0,1.4,0.2,setosa
4.7,3.2,1.3,0.2,setosa
7.0,3.2,4.7,1.4,versicolor
6.4,3.2,4.5,1.5,versicolor
6.9,3.1,4.9,1.5,versicolor
6.3,3.3,6.0,2.5,virginica
5.8,2.7,5.1,1.9,virginica
7.1,3.0,5.9,2.1,virginica
"""
    iris_dataset = create_dataset(
        "Iris Dataset", iris_data, "iris.csv",
        "Classic iris flowers dataset", admin_user
    )
    
    # Diabetes Dataset
    diabetes_data = """age,sex,bmi,bp,s6,y
29,1,29.6,94,75,151
48,0,23.7,84,92,75
77,1,35.2,168,156,141
73,1,25.9,123,116,206
55,0,30.6,100,103,135
"""
    diabetes_dataset = create_dataset(
        "Diabetes Dataset", diabetes_data, "diabetes.csv",
        "Diabetes progression dataset", admin_user
    )
    
    # Machine Learning Problems
    problems = [
        # Basic Data Exploration Problems (1-5)
        {
            "title": "Display Dataset Shape",
            "description": "Load the Titanic dataset and print its shape (rows, columns).",
            "starter_code": '''import pandas as pd\ndf = pd.read_csv('/datasets/titanic.csv')\n# Your code here''',
            "expected_output": "(5, 9)",
            "solution": '''import pandas as pd\ndf = pd.read_csv('/datasets/titanic.csv')\nprint(df.shape)''',
            "difficulty": "beginner",
            "points": 50,
            "dataset": titanic_dataset
        },
        {
            "title": "Count Missing Values",
            "description": "Count and print the number of missing values in each column of the Titanic dataset.",
            "starter_code": '''import pandas as pd\ndf = pd.read_csv('/datasets/titanic.csv')\n# Your code here''',
            "expected_output": "PassengerId    0\nSurvived       0\nPclass         0\nName           0\nSex            0\nAge            0\nSibSp          0\nParch          0\nFare           0\ndtype: int64",
            "solution": '''import pandas as pd\ndf = pd.read_csv('/datasets/titanic.csv')\nprint(df.isnull().sum())''',
            "difficulty": "beginner",
            "points": 75,
            "dataset": titanic_dataset
        },
        {
            "title": "Calculate Basic Statistics",
            "description": "Calculate and print basic statistics (mean, std, min, max) for numerical columns in the Iris dataset.",
            "starter_code": '''import pandas as pd\ndf = pd.read_csv('/datasets/iris.csv')\n# Your code here''',
            "expected_output": "sepal_length  sepal_width  petal_length  petal_width\ncount     9.000000     9.000000      9.000000     9.000000\nmean      5.911111     3.133333      3.900000     1.366667\nstd       0.996648     0.219257      2.024846     0.961509\nmin       4.700000     2.700000      1.300000     0.200000\nmax       7.100000     3.500000      6.000000     2.500000",
            "solution": '''import pandas as pd\ndf = pd.read_csv('/datasets/iris.csv')\nprint(df.describe())''',
            "difficulty": "beginner",
            "points": 75,
            "dataset": iris_dataset
        },
        {
            "title": "Count Unique Values",
            "description": "Count and print the number of unique values in each column of the Iris dataset.",
            "starter_code": '''import pandas as pd\ndf = pd.read_csv('/datasets/iris.csv')\n# Your code here''',
            "expected_output": "sepal_length    9\nsepal_width     8\npetal_length    9\npetal_width     8\nspecies         3\ndtype: int64",
            "solution": '''import pandas as pd\ndf = pd.read_csv('/datasets/iris.csv')\nprint(df.nunique())''',
            "difficulty": "beginner",
            "points": 50,
            "dataset": iris_dataset
        },
        {
            "title": "Filter Data by Condition",
            "description": "Filter the Titanic dataset to show only female passengers and print the result.",
            "starter_code": '''import pandas as pd\ndf = pd.read_csv('/datasets/titanic.csv')\n# Your code here''',
            "expected_output": "   PassengerId  Survived  Pclass      Name     Sex  Age  SibSp  Parch   Fare\n1            2         1       1   Cumings  female   38      1      0  71.28\n2            3         1       3  Heikkinen  female   26      0      0   7.92\n3            4         1       1  Futrelle  female   35      1      0  53.10",
            "solution": '''import pandas as pd\ndf = pd.read_csv('/datasets/titanic.csv')\nprint(df[df['Sex'] == 'female'])''',
            "difficulty": "beginner",
            "points": 75,
            "dataset": titanic_dataset
        },
        
        # Data Preprocessing Problems (6-10)
        {
            "title": "Handle Missing Values",
            "description": "Fill missing age values in Titanic dataset with the mean age and print the updated Age column.",
            "starter_code": '''import pandas as pd\ndf = pd.read_csv('/datasets/titanic.csv')\n# Your code here''',
            "expected_output": "0    22.0\n1    38.0\n2    26.0\n3    35.0\n4    35.0\nName: Age, dtype: float64",
            "solution": '''import pandas as pd\ndf = pd.read_csv('/datasets/titanic.csv')\ndf['Age'].fillna(df['Age'].mean(), inplace=True)\nprint(df['Age'])''',
            "difficulty": "beginner",
            "points": 100,
            "dataset": titanic_dataset
        },
        {
            "title": "Encode Categorical Variable",
            "description": "Convert the 'Sex' column in Titanic dataset to numerical values (male=0, female=1) and print the result.",
            "starter_code": '''import pandas as pd\ndf = pd.read_csv('/datasets/titanic.csv')\n# Your code here''',
            "expected_output": "0    0\n1    1\n2    1\n3    1\n4    0\nName: Sex, dtype: int64",
            "solution": '''import pandas as pd\ndf = pd.read_csv('/datasets/titanic.csv')\ndf['Sex'] = df['Sex'].map({'male': 0, 'female': 1})\nprint(df['Sex'])''',
            "difficulty": "beginner",
            "points": 100,
            "dataset": titanic_dataset
        },
        {
            "title": "Normalize Numerical Data",
            "description": "Normalize the 'Age' column in Titanic dataset using min-max scaling and print the result.",
            "starter_code": '''import pandas as pd\ndf = pd.read_csv('/datasets/titanic.csv')\n# Your code here''',
            "expected_output": "0    0.000000\n1    1.000000\n2    0.250000\n3    0.812500\n4    0.812500\nName: Age, dtype: float64",
            "solution": '''import pandas as pd\ndf = pd.read_csv('/datasets/titanic.csv')\nage = df['Age']\ndf['Age_normalized'] = (age - age.min()) / (age.max() - age.min())\nprint(df['Age_normalized'])''',
            "difficulty": "beginner",
            "points": 100,
            "dataset": titanic_dataset
        },
        {
            "title": "Create Dummy Variables",
            "description": "Convert the 'Pclass' column in Titanic dataset to dummy variables and print the result.",
            "starter_code": '''import pandas as pd\ndf = pd.read_csv('/datasets/titanic.csv')\n# Your code here''',
            "expected_output": "   Pclass_1  Pclass_3\n0         0         1\n1         1         0\n2         0         1\n3         1         0\n4         0         1",
            "solution": '''import pandas as pd\ndf = pd.read_csv('/datasets/titanic.csv')\ndummies = pd.get_dummies(df['Pclass'], prefix='Pclass')\nprint(dummies[['Pclass_1', 'Pclass_3']])''',
            "difficulty": "beginner",
            "points": 100,
            "dataset": titanic_dataset
        },
        {
            "title": "Train-Test Split",
            "description": "Split the Iris dataset into 70% training and 30% test sets and print their shapes.",
            "starter_code": '''from sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/iris.csv')\n# Your code here''',
            "expected_output": "Training set: (6, 5)\nTest set: (3, 5)",
            "solution": '''from sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/iris.csv')\ntrain, test = train_test_split(df, test_size=0.3)\nprint(f"Training set: {train.shape}")\nprint(f"Test set: {test.shape}")''',
            "difficulty": "beginner",
            "points": 100,
            "dataset": iris_dataset
        },
        
        # Basic Modeling Problems (11-15)
        {
            "title": "Train a Logistic Regression Model",
            "description": "Train a logistic regression model to predict survival on the Titanic dataset.",
            "starter_code": '''from sklearn.linear_model import LogisticRegression\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/titanic.csv')\nX = df[['Pclass', 'Age']]\ny = df['Survived']\n\n# Your code here''',
            "expected_output": "Model trained with accuracy: 0.60",
            "solution": '''from sklearn.linear_model import LogisticRegression\nfrom sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/titanic.csv')\nX = df[['Pclass', 'Age']]\ny = df['Survived']\n\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)\nmodel = LogisticRegression()\nmodel.fit(X_train, y_train)\nscore = model.score(X_test, y_test)\nprint(f"Model trained with accuracy: {score:.2f}")''',
            "difficulty": "intermediate",
            "points": 150,
            "dataset": titanic_dataset
        },
        {
            "title": "Predict Iris Species",
            "description": "Train a KNN classifier to predict iris species and print the accuracy.",
            "starter_code": '''from sklearn.neighbors import KNeighborsClassifier\nfrom sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/iris.csv')\nX = df[['sepal_length', 'sepal_width', 'petal_length', 'petal_width']]\ny = df['species']\n\n# Your code here''',
            "expected_output": "KNN accuracy: 1.00",
            "solution": '''from sklearn.neighbors import KNeighborsClassifier\nfrom sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/iris.csv')\nX = df[['sepal_length', 'sepal_width', 'petal_length', 'petal_width']]\ny = df['species']\n\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)\nmodel = KNeighborsClassifier(n_neighbors=3)\nmodel.fit(X_train, y_train)\nscore = model.score(X_test, y_test)\nprint(f"KNN accuracy: {score:.2f}")''',
            "difficulty": "intermediate",
            "points": 150,
            "dataset": iris_dataset
        },
        {
            "title": "Decision Tree Classifier",
            "description": "Train a decision tree classifier on the Iris dataset and print its depth.",
            "starter_code": '''from sklearn.tree import DecisionTreeClassifier\nfrom sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/iris.csv')\nX = df[['sepal_length', 'sepal_width', 'petal_length', 'petal_width']]\ny = df['species']\n\n# Your code here''',
            "expected_output": "Decision tree depth: [depth]",
            "solution": '''from sklearn.tree import DecisionTreeClassifier\nfrom sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/iris.csv')\nX = df[['sepal_length', 'sepal_width', 'petal_length', 'petal_width']]\ny = df['species']\n\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)\nmodel = DecisionTreeClassifier()\nmodel.fit(X_train, y_train)\nprint(f"Decision tree depth: {model.get_depth()}")''',
            "difficulty": "intermediate",
            "points": 150,
            "dataset": iris_dataset
        },
        {
            "title": "Linear Regression",
            "description": "Train a linear regression model to predict diabetes progression and print the R2 score.",
            "starter_code": '''from sklearn.linear_model import LinearRegression\nfrom sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/diabetes.csv')\nX = df[['age', 'bmi', 'bp']]\ny = df['y']\n\n# Your code here''',
            "expected_output": "R2 score: [value]",
            "solution": '''from sklearn.linear_model import LinearRegression\nfrom sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/diabetes.csv')\nX = df[['age', 'bmi', 'bp']]\ny = df['y']\n\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)\nmodel = LinearRegression()\nmodel.fit(X_train, y_train)\nscore = model.score(X_test, y_test)\nprint(f"R2 score: {score:.2f}")''',
            "difficulty": "intermediate",
            "points": 150,
            "dataset": diabetes_dataset
        },
        {
            "title": "Random Forest Classifier",
            "description": "Train a random forest classifier on the Titanic dataset to predict survival.",
            "starter_code": '''from sklearn.ensemble import RandomForestClassifier\nfrom sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/titanic.csv')\nX = df[['Pclass', 'Age', 'Fare']]\ny = df['Survived']\n\n# Your code here''',
            "expected_output": "Random Forest accuracy: [value]",
            "solution": '''from sklearn.ensemble import RandomForestClassifier\nfrom sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/titanic.csv')\nX = df[['Pclass', 'Age', 'Fare']]\ny = df['Survived']\n\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)\nmodel = RandomForestClassifier()\nmodel.fit(X_train, y_train)\nscore = model.score(X_test, y_test)\nprint(f"Random Forest accuracy: {score:.2f}")''',
            "difficulty": "intermediate",
            "points": 150,
            "dataset": titanic_dataset
        },
        
        # Evaluation and Visualization Problems (16-20)
        {
            "title": "Confusion Matrix",
            "description": "Create a confusion matrix for the Iris species prediction model.",
            "starter_code": '''from sklearn.metrics import confusion_matrix\nfrom sklearn.neighbors import KNeighborsClassifier\nfrom sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/iris.csv')\nX = df[['sepal_length', 'sepal_width', 'petal_length', 'petal_width']]\ny = df['species']\n\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)\nmodel = KNeighborsClassifier(n_neighbors=3)\nmodel.fit(X_train, y_train)\ny_pred = model.predict(X_test)\n\n# Your code here''',
            "expected_output": "[[1 0 0]\n [0 1 0]\n [0 0 1]]",
            "solution": '''from sklearn.metrics import confusion_matrix\nfrom sklearn.neighbors import KNeighborsClassifier\nfrom sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/iris.csv')\nX = df[['sepal_length', 'sepal_width', 'petal_length', 'petal_width']]\ny = df['species']\n\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)\nmodel = KNeighborsClassifier(n_neighbors=3)\nmodel.fit(X_train, y_train)\ny_pred = model.predict(X_test)\n\nprint(confusion_matrix(y_test, y_pred))''',
            "difficulty": "intermediate",
            "points": 150,
            "dataset": iris_dataset
        },
        {
            "title": "Feature Importance",
            "description": "Display feature importances from a random forest model trained on the Iris dataset.",
            "starter_code": '''from sklearn.ensemble import RandomForestClassifier\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/iris.csv')\nX = df[['sepal_length', 'sepal_width', 'petal_length', 'petal_width']]\ny = df['species']\n\n# Your code here''',
            "expected_output": "sepal_length    0.11\nsepal_width     0.02\npetal_length    0.44\npetal_width     0.43",
            "solution": '''from sklearn.ensemble import RandomForestClassifier\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/iris.csv')\nX = df[['sepal_length', 'sepal_width', 'petal_length', 'petal_width']]\ny = df['species']\n\nmodel = RandomForestClassifier()\nmodel.fit(X, y)\nimportance = pd.Series(model.feature_importances_, index=X.columns)\nprint(importance.round(2))''',
            "difficulty": "intermediate",
            "points": 150,
            "dataset": iris_dataset
        },
        {
            "title": "Cross-Validation Score",
            "description": "Calculate and print the cross-validation score for a logistic regression model on the Titanic dataset.",
            "starter_code": '''from sklearn.linear_model import LogisticRegression\nfrom sklearn.model_selection import cross_val_score\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/titanic.csv')\nX = df[['Pclass', 'Age', 'Fare']]\ny = df['Survived']\n\n# Your code here''',
            "expected_output": "Cross-validation scores: [0.6 0.6 0.6 0.6 0.6]",
            "solution": '''from sklearn.linear_model import LogisticRegression\nfrom sklearn.model_selection import cross_val_score\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/titanic.csv')\nX = df[['Pclass', 'Age', 'Fare']]\ny = df['Survived']\n\nmodel = LogisticRegression()\nscores = cross_val_score(model, X, y, cv=5)\nprint(f"Cross-validation scores: {scores}")''',
            "difficulty": "intermediate",
            "points": 150,
            "dataset": titanic_dataset
        },
        {
            "title": "Classification Report",
            "description": "Generate a classification report for the Iris species prediction model.",
            "starter_code": '''from sklearn.metrics import classification_report\nfrom sklearn.neighbors import KNeighborsClassifier\nfrom sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/iris.csv')\nX = df[['sepal_length', 'sepal_width', 'petal_length', 'petal_width']]\ny = df['species']\n\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)\nmodel = KNeighborsClassifier(n_neighbors=3)\nmodel.fit(X_train, y_train)\ny_pred = model.predict(X_test)\n\n# Your code here''',
            "expected_output": "              precision    recall  f1-score   support\n\n      setosa       1.00      1.00      1.00         1\n  versicolor       1.00      1.00      1.00         1\n   virginica       1.00      1.00      1.00         1\n\n    accuracy                           1.00         3\n   macro avg       1.00      1.00      1.00         3\nweighted avg       1.00      1.00      1.00         3",
            "solution": '''from sklearn.metrics import classification_report\nfrom sklearn.neighbors import KNeighborsClassifier\nfrom sklearn.model_selection import train_test_split\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/iris.csv')\nX = df[['sepal_length', 'sepal_width', 'petal_length', 'petal_width']]\ny = df['species']\n\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)\nmodel = KNeighborsClassifier(n_neighbors=3)\nmodel.fit(X_train, y_train)\ny_pred = model.predict(X_test)\n\nprint(classification_report(y_test, y_pred))''',
            "difficulty": "intermediate",
            "points": 150,
            "dataset": iris_dataset
        },
        {
            "title": "Grid Search for Hyperparameter Tuning",
            "description": "Perform grid search to find the best K for KNN classifier on the Iris dataset.",
            "starter_code": '''from sklearn.neighbors import KNeighborsClassifier\nfrom sklearn.model_selection import GridSearchCV\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/iris.csv')\nX = df[['sepal_length', 'sepal_width', 'petal_length', 'petal_width']]\ny = df['species']\n\n# Your code here''',
            "expected_output": "Best K: 3\nBest score: 1.00",
            "solution": '''from sklearn.neighbors import KNeighborsClassifier\nfrom sklearn.model_selection import GridSearchCV\nimport pandas as pd\n\ndf = pd.read_csv('/datasets/iris.csv')\nX = df[['sepal_length', 'sepal_width', 'petal_length', 'petal_width']]\ny = df['species']\n\nparam_grid = {'n_neighbors': range(1, 10)}\ngrid = GridSearchCV(KNeighborsClassifier(), param_grid, cv=5)\ngrid.fit(X, y)\nprint(f"Best K: {grid.best_params_['n_neighbors']}")\nprint(f"Best score: {grid.best_score_:.2f}")''',
            "difficulty": "advanced",
            "points": 200,
            "dataset": iris_dataset
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
    
    print("20 Machine Learning problems populated successfully!")

if __name__ == '__main__':
    populate()