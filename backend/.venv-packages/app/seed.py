from sqlalchemy import select
from .models import Concept, Question, Misconception, SessionLocal, Base, engine

CONCEPT_NAMES = ["Variables", "Data types", "Operators", "Strings", "Input and output", "Conditionals", "Boolean logic", "Lists", "Indexing", "Loops", "Loop control", "Functions", "Parameters", "Return values", "Scope", "Dictionaries", "Tuples and sets", "Comprehensions", "Modules", "Exceptions", "Files", "Recursion", "Classes", "Methods", "Inheritance"]

def seed():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    if db.scalar(select(Concept).limit(1)):
        db.close(); return
    slugs = []
    for i, title in enumerate(CONCEPT_NAMES):
        slug = title.lower().replace(" ", "-")
        slugs.append(slug)
        prereq = ([slugs[i-1]] if i else [])
        db.add(Concept(slug=slug, title=title, description=f"Build confidence with {title.lower()} in Python.", prerequisites=prereq, order=i))
    for i, title in enumerate(CONCEPT_NAMES):
        slug = slugs[i]
        for n in range(2):
            if i == 0:
                prompt, options, correct, misconception = "What does x = 5 do?", ["Stores 5 in x", "Compares x to 5", "Prints 5", "Creates a function"], 0, "assignment_is_comparison"
            else:
                prompt, options, correct, misconception = f"Which statement best describes {title.lower()} in Python?", [f"A core Python {title.lower()} feature", "Only comments", "A syntax error", "A file extension"], 0, f"misunderstands_{slug}"
            db.add(Question(concept_slug=slug, prompt=prompt, options=options, correct_index=correct, explanation=f"{title} is a fundamental part of Python. Review the example and try another question.", misconception_ids=["", misconception, "", ""]))
    db.commit(); db.close()

if __name__ == "__main__": seed()
