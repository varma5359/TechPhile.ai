from populate_ml import populate as populate_ml
from populate_dl import populate as populate_dl
from populate_cv import populate as populate_cv
from populate_nlp import populate as populate_nlp
from populate_genai import populate as populate_genai

def run_all():
    print("Populating all data...")
    populate_ml()
    populate_dl()
    populate_cv()
    populate_nlp()
    populate_genai()
    print("All data populated successfully!")

if __name__ == '__main__':
    run_all()