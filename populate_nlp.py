from techphile_exams.explore_courses.populate_base import *

def populate():
    admin_user = get_admin_user()
    nlp_topic = Topic.objects.get(name="NLP")
    
    # Sample text data
    text_data = """id,text,label
    1,"I love this product!",positive
    2,"This is terrible.",negative
    3,"It's okay, not great.",neutral
    4,"Amazing experience!",positive
    5,"Worst service ever.",negative
    """
    sentiment_dataset = create_dataset(
        "Sentiment Analysis Sample", text_data, "sentiment.csv",
        "Small sample of text with sentiment labels", admin_user
    )
    
    # NLP Problems
    problems = [
        {
            "title": "Tokenize Text with NLTK",
            "description": "Tokenize a sample sentence using NLTK.",
            "starter_code": '''import nltk
nltk.download('punkt')
sentence = "This is a sample sentence."

# Your code here''',
            "expected_output": "['This', 'is', 'a', 'sample', 'sentence', '.']",
            "solution": '''import nltk
nltk.download('punkt')
from nltk.tokenize import word_tokenize

sentence = "This is a sample sentence."
tokens = word_tokenize(sentence)
print(tokens)''',
            "difficulty": "beginner",
            "points": 100,
            "dataset": None
        },
        {
            "title": "Sentiment Analysis with TextBlob",
            "description": "Analyze sentiment of text using TextBlob.",
            "starter_code": '''from textblob import TextBlob
text = "I love this product!"

# Your code here''',
            "expected_output": "Sentiment(polarity=0.5, subjectivity=0.6)",
            "solution": '''from textblob import TextBlob
text = "I love this product!"
blob = TextBlob(text)
print(blob.sentiment)''',
            "difficulty": "beginner",
            "points": 100,
            "dataset": None
        },
        {
            "title": "Train a Simple Text Classifier",
            "description": "Train a classifier to predict sentiment from text.",
            "starter_code": '''import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB

df = pd.read_csv('/datasets/sentiment.csv')

# Your code here''',
            "expected_output": "Model trained with accuracy > 0.8",
            "solution": '''import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

df = pd.read_csv('/datasets/sentiment.csv')

# Prepare data
X = df['text']
y = df['label']

# Vectorize text
vectorizer = TfidfVectorizer()
X_vec = vectorizer.fit_transform(X)

# Split data
X_train, X_test, y_train, y_test = train_test_split(X_vec, y, test_size=0.2)

# Train model
model = MultinomialNB()
model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
acc = accuracy_score(y_test, y_pred)
print(f"Model accuracy: {acc:.2f}")''',
            "difficulty": "intermediate",
            "points": 200,
            "dataset": sentiment_dataset
        }
    ]
    
    for p in problems:
        Problem.objects.get_or_create(
            title=p["title"],
            topic=nlp_topic,
            dataset=p.get("dataset"),
            difficulty=p["difficulty"],
            description=p["description"],
            starter_code=p["starter_code"],
            expected_output=p["expected_output"],
            solution=p["solution"],
            points=p["points"],
            created_by=admin_user
        )
    
    print("NLP problems populated.")

if __name__ == '__main__':
    populate()