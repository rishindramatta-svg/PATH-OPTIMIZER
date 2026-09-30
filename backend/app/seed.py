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
                    db.add(
                        Question(
                            concept_slug=slug,
                            prompt=prompt,
                            options=options,
                            correct_index=correct,
                            explanation=f"{title} is a fundamental part of Python. Review the example and try another question.",
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
