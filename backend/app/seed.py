import os

import bcrypt
from sqlalchemy import select

from .models import (
    Base,
    Concept,
    CourseEnrollment,
    Question,
    SessionLocal,
    User,
    engine,
)


def validate_dag(concepts):
    known = {c.slug for c in concepts}
    marks = {}

    def visit(slug):
        if marks.get(slug) == 1:
            raise ValueError(f"Prerequisite cycle at {slug}")
        if marks.get(slug) == 2:
            return
        marks[slug] = 1
        concept = next(c for c in concepts if c.slug == slug)
        for dependency in concept.prerequisites:
            if dependency not in known:
                raise ValueError(f"Unknown prerequisite {dependency}")
            visit(dependency)
        marks[slug] = 2

    for slug in known:
        visit(slug)


CONCEPT_NAMES = [
    "Variables",
    "Data types",
    "Operators",
    "Strings",
    "Input and output",
    "Conditionals",
    "Boolean logic",
    "Lists",
    "Indexing",
    "Loops",
    "Loop control",
    "Functions",
    "Parameters",
    "Return values",
    "Scope",
    "Dictionaries",
    "Tuples and sets",
    "Comprehensions",
    "Modules",
    "Exceptions",
    "Files",
    "Recursion",
    "Classes",
    "Methods",
    "Inheritance",
]


QUESTION_BANK = {
    "Comprehensions": [
        ("What does [n * 2 for n in range(4)] produce?", ["[2, 4, 6, 8]", "[0, 1, 2, 3]", "[0, 2, 4, 6]", "[0, 2, 4, 6, 8]"], 2, "range(4) gives 0, 1, 2, 3, and each value is doubled, so the result is [0, 2, 4, 6]."),
        ("Which comprehension keeps only the even numbers from nums?", ["[n for n in nums if n % 2 == 1]", "[n % 2 == 0 for n in nums]", "[n for n in nums where n % 2 == 0]", "[n for n in nums if n % 2 == 0]"], 3, "The condition goes after the loop and filters items. Putting the test first gives True/False values instead of the numbers."),
        ("What does {k: v for k, v in pairs} create?", ["A dictionary", "A set", "A list of tuples", "A generator"], 0, "Curly braces with key: value pairs build a dictionary. A set comprehension has no colon."),
    ],
    "Modules": [
        ("Which statement imports only the sqrt function from the math module?", ["import math.sqrt", "import sqrt from math", "from math import sqrt", "include math.sqrt"], 2, "Python uses from module import name. The form 'import sqrt from math' belongs to other languages."),
        ("After 'import math', how do you call sqrt on 16?", ["math(16)", "sqrt(16)", "from math sqrt(16)", "math.sqrt(16)"], 3, "A plain import keeps names inside the module, so you write the module name, a dot, then the function."),
        ("What does if __name__ == '__main__': do?", ["Runs the block only when the file is run directly", "Makes the file importable by other files", "Declares the name of the module", "Stops the file from running"], 0, "When a file is imported, __name__ is the module name. It equals '__main__' only when the file is run directly."),
    ],
    "Exceptions": [
        ("Which block runs only if an exception occurs?", ["try", "finally", "except", "else"], 2, "except handles the error. finally runs every time, and else runs only when no error happens."),
        ("What is printed? try: print(1 / 0) except ZeroDivisionError: print('error')", ["error", "1", "ZeroDivisionError", "Nothing is printed"], 0, "Dividing by zero raises ZeroDivisionError, the except block catches it, and 'error' is printed."),
        ("Which statement raises an exception on purpose?", ["catch ValueError('bad')", "throw ValueError('bad')", "error ValueError('bad')", "raise ValueError('bad')"], 3, "Python uses raise. The words throw and catch belong to other languages."),
    ],
    "Files": [
        ("Which mode opens a file for writing and erases its old content?", ["'r'", "'a'", "'w'", "'rb'"], 2, "'w' truncates the file. 'a' adds to the end, and 'r' only reads."),
        ("Why is 'with open(path) as f:' preferred?", ["It closes the file automatically, even if an error occurs", "It makes the file read faster", "It lets several programs write the file at once", "It converts the file to text automatically"], 0, "The with statement closes the file for you when the block ends, even after an error."),
        ("What does f.read() return for a text file?", ["A list of lines", "The first line only", "The number of characters", "The whole content as one string"], 3, "read() returns everything as one string. readline() gives one line and readlines() gives a list."),
    ],
    "Recursion": [
        ("What must every recursive function have?", ["A loop", "A global variable", "A base case that stops the recursion", "An integer return type"], 2, "Without a base case the function keeps calling itself and never finishes."),
        ("What does factorial(3) return? def factorial(n): return 1 if n <= 1 else n * factorial(n - 1)", ["3", "9", "1", "6"], 3, "factorial(3) = 3 * 2 * 1 = 6."),
        ("What happens if a recursive function never reaches its base case?", ["Python raises a RecursionError", "It runs forever without any error", "It returns None quietly", "Python turns it into a loop"], 0, "Python limits recursion depth and raises RecursionError when the limit is passed."),
    ],
    "Classes": [
        ("What is __init__ used for?", ["Deleting an object", "Declaring a class", "Importing a module", "Setting up a new object's attributes"], 3, "__init__ runs when an object is created and usually sets its starting attributes."),
        ("What does self refer to inside a method?", ["The parent class", "The class itself", "The current object", "The module"], 2, "self is the specific object the method was called on, so each object keeps its own data."),
        ("What does d = Dog() do, if Dog is a class?", ["Creates an instance of Dog", "Copies the Dog class", "Defines a new class called d", "Calls a function and discards it"], 0, "Calling the class creates a new object (an instance) and stores it in d."),
    ],
    "Methods": [
        ("How do you call the method speak on an object d?", ["speak(d)", "d->speak()", "d:speak()", "d.speak()"], 3, "Methods are called with dot notation: object.method()."),
        ("Why does a method usually start with the parameter self?", ["To make it private", "Because every Python function needs it", "So the method can use the object it is called on", "To make it run faster"], 2, "Python passes the object in as the first argument, and self lets the method read and change that object's data."),
        ("What is a @staticmethod?", ["A method that does not receive self or cls", "A method that cannot be overridden", "A method that runs once at import", "A method that changes the class"], 0, "A static method belongs to the class but receives no automatic first argument."),
    ],
    "Inheritance": [
        ("In class Dog(Animal), what is Animal?", ["An instance of Dog", "The child class", "The parent (base) class", "A module"], 2, "The class in the brackets is the parent. Dog is the child that inherits from it."),
        ("What does super().__init__() do in a child class?", ["Creates a second object", "Skips the parent's setup", "Deletes the parent class", "Runs the parent class's __init__"], 3, "super() reaches the parent, so the parent's setup code runs for the child too."),
        ("Parent and child both define speak(). Which runs on a child object?", ["The child's speak()", "The parent's speak()", "Both, parent first", "Python raises an error"], 0, "The child's version overrides the parent's. Python looks in the child class first."),
    ],
}


def seed():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        if not db.scalar(select(Concept).limit(1)):
            slugs = []
            for i, title in enumerate(CONCEPT_NAMES):
                slug = title.lower().replace(" ", "-")
                slugs.append(slug)
                prereq = [slugs[i - 1]] if i else []
                db.add(
                    Concept(
                        slug=slug,
                        title=title,
                        description=f"Build confidence with {title.lower()} in Python.",
                        prerequisites=prereq,
                        order=i,
                    )
                )
            for i, title in enumerate(CONCEPT_NAMES):
                slug = slugs[i]
                for n in range(3 if i < 10 else 2):
                    if i == 0:
                        prompt, options, correct, misconception = (
                            "What does x = 5 do?",
                            [
                                "Stores 5 in x",
                                "Compares x to 5",
                                "Prints 5",
                                "Creates a function",
                            ],
                            0,
                            "assignment_is_comparison",
                        )
                    else:
                        prompt, options, correct, misconception = (
                            f"Which statement best describes {title.lower()} in Python?",
                            [
                                f"A core Python {title.lower()} feature",
                                "Only comments",
                                "A syntax error",
                                "A file extension",
                            ],
                            0,
                            f"misunderstands_{slug}",
                        )
                    bank = QUESTION_BANK.get(title, [])
                    explanation = f"{title} is a fundamental part of Python. Review the example and try another question."
                    if n < len(bank):
                        prompt, options, correct, explanation = bank[n]
                        misconception = f"misunderstands_{slug}"
                    db.add(
                        Question(
                            concept_slug=slug,
                            prompt=prompt,
                            options=options,
                            correct_index=correct,
                            explanation=explanation,
                            misconception_ids=["", misconception, "", ""],
                        )
                    )
            db.flush()
            validate_dag(db.scalars(select(Concept)).all())
        demo_password = os.getenv("DEMO_PASSWORD", "DemoPass123!")
        hashed = bcrypt.hashpw(demo_password.encode(), bcrypt.gensalt()).decode()
        for email, role in (
            ("student@png9.local", "student"),
            ("instructor@png9.local", "instructor"),
            ("admin@png9.local", "admin"),
        ):
            user = db.scalar(select(User).where(User.email == email))
            if not user:
                db.add(User(email=email, role=role, hashed_password=hashed))
            else:
                user.role = role
                if not user.hashed_password:
                    user.hashed_password = hashed
        db.flush()
        instructor = db.scalar(select(User).where(User.email == "instructor@png9.local"))
        demo_student = db.scalar(select(User).where(User.email == "student@png9.local"))
        if instructor:
            existing = {
                (row.user_id, row.role)
                for row in db.scalars(
                    select(CourseEnrollment).where(CourseEnrollment.course_id == "python-foundations")
                ).all()
            }
            if (instructor.id, "instructor") not in existing:
                db.add(
                    CourseEnrollment(
                        course_id="python-foundations",
                        user_id=instructor.id,
                        role="instructor",
                    )
                )
            for student in [demo_student] if demo_student else []:
                if (student.id, "student") not in existing:
                    db.add(
                        CourseEnrollment(
                            course_id="python-foundations",
                            user_id=student.id,
                            role="student",
                            instructor_id=instructor.id,
                        )
                    )
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
