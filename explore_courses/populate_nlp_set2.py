from techphile_exams.explore_courses.populate_base import *

def populate():
    admin_user = get_admin_user()
    nlp_topic = Topic.objects.get_or_create(name="NLP")[0]
    
    # Create text datasets
    sample_texts = """id,text,label
1,"The quick brown fox jumps over the lazy dog.",example
2,"Natural language processing enables computers to understand human language.",nlp
3,"Python is a popular programming language for data science.",python
4,"Machine learning algorithms improve through experience.",ml
5,"Deep learning uses neural networks with many layers.",dl
"""
    text_dataset = create_dataset(
        "Sample Texts", sample_texts, "sample_texts.csv",
        "Collection of sample sentences for NLP exercises", admin_user
    )
    
    sentiment_data = """id,text,sentiment
1,"I love this product!",positive
2,"This is terrible.",negative
3,"The service was okay.",neutral
4,"Amazing experience! Will buy again.",positive
5,"Worst customer service ever.",negative
"""
    sentiment_dataset = create_dataset(
        "Sentiment Examples", sentiment_data, "sentiment.csv",
        "Text samples with sentiment labels", admin_user
    )
    
    # Basic NLP Problems
    problems = [
        {
            "title": "Tokenize Sentence",
            "description": "Split a sentence into words using NLTK's word_tokenize.",
            "starter_code": '''import nltk
nltk.download('punkt')
sentence = "NLP makes computers understand language."

# Your code here''',
            "solution": '''from nltk.tokenize import word_tokenize
tokens = word_tokenize("NLP makes computers understand language.")
print(tokens)''',
            "expected_output": "['NLP', 'makes', 'computers', 'understand', 'language', '.']",
            "difficulty": "beginner",
            "points": 50
        },
        {
            "title": "Remove Punctuation",
            "description": "Remove punctuation from a list of tokens.",
            "starter_code": '''import string
tokens = ['Hello', ',', 'world', '!']

# Your code here''',
            "solution": '''clean_tokens = [token for token in tokens if token not in string.punctuation]
print(clean_tokens)''',
            "expected_output": "['Hello', 'world']",
            "difficulty": "beginner",
            "points": 50
        },
        {
            "title": "Convert to Lowercase",
            "description": "Convert all tokens to lowercase.",
            "starter_code": '''tokens = ['The', 'Quick', 'BROWN', 'Fox']

# Your code here''',
            "solution": '''lower_tokens = [token.lower() for token in tokens]
print(lower_tokens)''',
            "expected_output": "['the', 'quick', 'brown', 'fox']",
            "difficulty": "beginner",
            "points": 50
        },
        {
            "title": "Count Word Frequencies",
            "description": "Count how many times each word appears in a text.",
            "starter_code": '''from collections import defaultdict
text = "apple orange apple banana orange apple"

# Your code here''',
            "solution": '''words = text.split()
freq = defaultdict(int)
for word in words:
    freq[word] += 1
print(dict(freq))''',
            "expected_output": "{'apple': 3, 'orange': 2, 'banana': 1}",
            "difficulty": "beginner",
            "points": 75
        },
        {
            "title": "Remove Stopwords",
            "description": "Remove common stopwords from text using NLTK.",
            "starter_code": '''from nltk.corpus import stopwords
nltk.download('stopwords')
tokens = ['this', 'is', 'a', 'sample', 'sentence']

# Your code here''',
            "solution": '''stop_words = set(stopwords.words('english'))
filtered = [word for word in tokens if word.lower() not in stop_words]
print(filtered)''',
            "expected_output": "['sample', 'sentence']",
            "difficulty": "beginner",
            "points": 75
        },
        {
            "title": "Stem Words",
            "description": "Reduce words to their stems using Porter Stemmer.",
            "starter_code": '''from nltk.stem import PorterStemmer
words = ['running', 'jumps', 'easily']

# Your code here''',
            "solution": '''stemmer = PorterStemmer()
stems = [stemmer.stem(word) for word in words]
print(stems)''',
            "expected_output": "['run', 'jump', 'easili']",
            "difficulty": "beginner",
            "points": 75
        },
        {
            "title": "Lemmatize Words",
            "description": "Reduce words to their dictionary form using WordNetLemmatizer.",
            "starter_code": '''from nltk.stem import WordNetLemmatizer
nltk.download('wordnet')
words = ['running', 'better', 'geese']

# Your code here''',
            "solution": '''lemmatizer = WordNetLemmatizer()
lemmas = [lemmatizer.lemmatize(word) for word in words]
print(lemmas)''',
            "expected_output": "['running', 'better', 'goose']",
            "difficulty": "beginner",
            "points": 75
        },
        {
            "title": "Part-of-Speech Tagging",
            "description": "Tag words with their part-of-speech using NLTK.",
            "starter_code": '''import nltk
nltk.download('averaged_perceptron_tagger')
sentence = "Python is a great language"

# Your code here''',
            "solution": '''tokens = nltk.word_tokenize(sentence)
tags = nltk.pos_tag(tokens)
print(tags)''',
            "expected_output": "[('Python', 'NNP'), ('is', 'VBZ'), ('a', 'DT'), ('great', 'JJ'), ('language', 'NN')]",
            "difficulty": "intermediate",
            "points": 100
        },
        {
            "title": "Named Entity Recognition",
            "description": "Identify named entities in text using NLTK.",
            "starter_code": '''import nltk
nltk.download('maxent_ne_chunker')
nltk.download('words')
text = "Apple is looking at buying U.K. startup for $1 billion"

# Your code here''',
            "solution": '''tokens = nltk.word_tokenize(text)
tags = nltk.pos_tag(tokens)
entities = nltk.chunk.ne_chunk(tags)
print(entities)''',
            "expected_output": "Tree showing named entities",
            "difficulty": "intermediate",
            "points": 100
        },
        {
            "title": "Sentiment Analysis with TextBlob",
            "description": "Analyze sentiment polarity of a sentence.",
            "starter_code": '''from textblob import TextBlob
text = "I love natural language processing!"

# Your code here''',
            "solution": '''blob = TextBlob(text)
print(blob.sentiment.polarity)''',
            "expected_output": "0.5 (or similar positive value)",
            "difficulty": "beginner",
            "points": 75
        },
        {
            "title": "Bag-of-Words Representation",
            "description": "Create a bag-of-words model using CountVectorizer.",
            "starter_code": '''from sklearn.feature_extraction.text import CountVectorizer
docs = ["NLP is awesome", "I love NLP"]

# Your code here''',
            "solution": '''vectorizer = CountVectorizer()
X = vectorizer.fit_transform(docs)
print(vectorizer.get_feature_names_out())
print(X.toarray())''',
            "expected_output": "Feature names and document-term matrix",
            "difficulty": "intermediate",
            "points": 100
        },
        {
            "title": "TF-IDF Vectorization",
            "description": "Convert text to TF-IDF vectors.",
            "starter_code": '''from sklearn.feature_extraction.text import TfidfVectorizer
docs = ["machine learning", "deep learning"]

# Your code here''',
            "solution": '''tfidf = TfidfVectorizer()
X = tfidf.fit_transform(docs)
print(tfidf.get_feature_names_out())
print(X.toarray())''',
            "expected_output": "Feature names and TF-IDF matrix",
            "difficulty": "intermediate",
            "points": 100
        },
        {
            "title": "Word Cloud Generation",
            "description": "Create a word cloud from text.",
            "starter_code": '''from wordcloud import WordCloud
text = "Python Python data science machine learning Python"

# Your code here''',
            "solution": '''wc = WordCloud().generate(text)
wc.to_file("wordcloud.png")
print("wordcloud.png created")''',
            "expected_output": "wordcloud.png created",
            "difficulty": "beginner",
            "points": 75,
        },
        {
            "title": "Text Similarity (Cosine)",
            "description": "Calculate cosine similarity between two sentences.",
            "starter_code": '''from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
doc1 = "I love machine learning"
doc2 = "I enjoy deep learning"

# Your code here''',
            "solution": '''tfidf = TfidfVectorizer()
vectors = tfidf.fit_transform([doc1, doc2])
similarity = cosine_similarity(vectors[0], vectors[1])
print(similarity[0][0])''',
            "expected_output": "Similarity score between 0 and 1",
            "difficulty": "intermediate",
            "points": 100
        },
        {
            "title": "Spell Checker",
            "description": "Correct spelling in a sentence using TextBlob.",
            "starter_code": '''from textblob import TextBlob
text = "I havv good speling"

# Your code here''',
            "solution": '''blob = TextBlob(text)
corrected = blob.correct()
print(corrected)''',
            "expected_output": "I have good spelling",
            "difficulty": "beginner",
            "points": 75
        },
        {
            "title": "Language Detection",
            "description": "Detect language of text using langdetect.",
            "starter_code": '''from langdetect import detect
text = "Bonjour le monde"

# Your code here''',
            "solution": '''language = detect(text)
print(language)''',
            "expected_output": "fr",
            "difficulty": "beginner",
            "points": 75
        },
        {
            "title": "Text Summarization",
            "description": "Extract key sentences from text using NLTK.",
            "starter_code": '''from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
text = "Natural language processing is a field of AI. It helps computers understand human language. NLP has many applications."

# Your code here''',
            "solution": '''sentences = sent_tokenize(text)
words = word_tokenize(text.lower())
stop_words = set(stopwords.words('english'))
word_freq = {}
for word in words:
    if word not in stop_words and word.isalpha():
        word_freq[word] = word_freq.get(word, 0) + 1
max_freq = max(word_freq.values())
for word in word_freq:
    word_freq[word] /= max_freq
sentence_scores = {}
for sentence in sentences:
    for word in word_tokenize(sentence.lower()):
        if word in word_freq:
            sentence_scores[sentence] = sentence_scores.get(sentence, 0) + word_freq[word]
summary = sorted(sentence_scores, key=sentence_scores.get, reverse=True)[:1]
print(summary)''',
            "expected_output": "Most important sentence from text",
            "difficulty": "intermediate",
            "points": 150
        },
        {
            "title": "Word Embeddings (GloVe)",
            "description": "Load and use pre-trained GloVe word vectors.",
            "starter_code": '''# Assuming glove.6B.50d.txt is in /datasets
import numpy as np

# Your code here''',
            "solution": '''embeddings = {}
with open('/datasets/glove.6B.50d.txt', encoding='utf-8') as f:
    for line in f:
        values = line.split()
        word = values[0]
        vector = np.asarray(values[1:], dtype='float32')
        embeddings[word] = vector
print(embeddings.get('king', None).shape)''',
            "expected_output": "(50,)",
            "difficulty": "advanced",
            "points": 200
        },
        {
            "title": "Simple Chatbot",
            "description": "Create a rule-based response system.",
            "starter_code": '''def chatbot_response(user_input):
    # Your code here
    return response

print(chatbot_response("Hello"))''',
            "solution": '''def chatbot_response(user_input):
    user_input = user_input.lower()
    if "hello" in user_input:
        return "Hello there!"
    elif "how are you" in user_input:
        return "I'm a bot, so I'm always good!"
    elif "bye" in user_input:
        return "Goodbye!"
    else:
        return "I didn't understand that."

print(chatbot_response("Hello"))''',
            "expected_output": "Hello there!",
            "difficulty": "intermediate",
            "points": 150
        },
        {
            "title": "Text Generation (Markov)",
            "description": "Generate text using a simple Markov chain.",
            "starter_code": '''from collections import defaultdict
import random

text = "I love NLP. I love machine learning. I love Python."

# Your code here''',
            "solution": '''words = text.split()
markov = defaultdict(list)
for i in range(len(words)-1):
    markov[words[i]].append(words[i+1])
current = random.choice(list(markov.keys()))
generated = [current]
for _ in range(5):
    next_word = random.choice(markov[current])
    generated.append(next_word)
    current = next_word
print(' '.join(generated))''',
            "expected_output": "Generated sequence of words",
            "difficulty": "intermediate",
            "points": 150
        }
    ]

    # Create Problem entries
    for p in problems:
        Problem.objects.get_or_create(
            title=p["title"],
            topic=nlp_topic,
            dataset=text_dataset if p.get("dataset") else None,
            difficulty=p["difficulty"],
            description=p["description"],
            starter_code=p["starter_code"],
            expected_output=p["expected_output"],
            solution=p["solution"],
            points=p["points"],
            created_by=admin_user,
        )
    
    print("✅ 20 Basic NLP problems populated.")

if __name__ == '__main__':
    populate()