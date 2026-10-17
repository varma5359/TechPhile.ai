from explore_courses.populate_ml_set1 import populate as populate_ml_set1
from explore_courses.populate_ml_set2 import populate as populate_ml_set2
from explore_courses.populate_dl_set1 import populate as populate_dl_set1
from explore_courses.populate_dl_set2 import populate as populate_dl_set2
from explore_courses.populate_cv_set1 import populate as populate_cv_set1
from explore_courses.populate_cv_set2 import populate as populate_cv_set2
from explore_courses.populate_ai_set1 import populate as populate_ai_set1
from explore_courses.populate_ai_set2 import populate as populate_ai_set2
from explore_courses.populate_nlp_set1 import populate as populate_nlp_set1
from explore_courses.populate_nlp_set2 import populate as populate_nlp_set2
from explore_courses.populate_genai_set1 import populate as populate_genai_set1
from explore_courses.populate_genai_set2 import populate as populate_genai_set2
from explore_courses.populate_pandas_set1 import populate as populate_pandas_set1
from explore_courses.populate_pandas_set2 import populate as populate_pandas_set2
from explore_courses.populate_numpy_set1 import populate as populate_numpy_set1
from explore_courses.populate_numpy_set2 import populate as populate_numpy_set2
from core.models import Topic

def run_all():
    print("🚀 Populating all data...\n")

    sections = [
        ("Machine Learning", [populate_ml_set1, populate_ml_set2]),
        ("Deep Learning", [populate_dl_set1, populate_dl_set2]),
        ("Computer Vision", [populate_cv_set1, populate_cv_set2]),
        ("AI (General)", [populate_ai_set1, populate_ai_set2]),
        ("Natural Language Processing", [populate_nlp_set1, populate_nlp_set2]),
        ("Generative AI", [populate_genai_set1, populate_genai_set2]),
        ("Pandas", [populate_pandas_set1, populate_pandas_set2]),
        ("NumPy", [populate_numpy_set1, populate_numpy_set2]),
    ]

    for name, funcs in sections:
        print(f"📂 {name}")
        for func in funcs:
            try:
                func()
                print(f"   ✅ {func.__name__} done.")
            except Exception as e:
                print(f"   ❌ Failed: {func.__name__} - {e}")
        print()

    print("✅ All data populated successfully!")

if __name__ == '__main__':
    run_all()
