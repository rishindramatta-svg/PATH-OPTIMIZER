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


QUESTION_BANK.update({
    "Variables": [
        ("Which line correctly creates a variable named age with the value 25?", ["int age = 25", "var age := 25", "25 = age", "age = 25"], 3, "Python needs no type keyword. You write the name, an equals sign, then the value."),
        ("After x = 5 and then x = x + 1, what is stored in x?", ["6", "5", "x + 1", "An error"], 0, "Python works out x + 1 using the old value (6) and stores the result back in x."),
        ("Which is a valid variable name in Python?", ["2count", "my-count", "my_count", "my count"], 2, "Names can use letters, digits and underscores, but cannot start with a digit or contain hyphens or spaces."),
        ("What happens after x = 3 and then x = 'hi'?", ["Python raises a TypeError", "x stays 3", "x now refers to the string 'hi'", "'hi' is converted to a number"], 2, "Python variables have no fixed type. Assigning again just makes the name point to the new value."),
    ],
    "Data types": [
        ("What does type(3.14) report?", ["<class 'int'>", "<class 'str'>", "<class 'float'>", "<class 'decimal'>"], 2, "A number with a decimal point is a float."),
        ("Which of these values is a string?", ["42", "3.0", "True", "'42'"], 3, "Anything inside quotes is a string, even if it looks like a number."),
        ("What does int('7') return?", ["7", "'7'", "7.0", "An error"], 0, "int() converts the text '7' into the whole number 7."),
        ("What type is the value True?", ["str", "int only", "bool", "None"], 2, "True and False are the two bool (Boolean) values."),
    ],
    "Operators": [
        ("What is 7 // 2?", ["3.5", "4", "3", "1"], 2, "// is floor division. It divides and drops the decimal part, so 7 // 2 is 3."),
        ("What is 7 % 2?", ["1", "3", "0", "3.5"], 0, "% gives the remainder. 7 divided by 2 leaves a remainder of 1."),
        ("What is 2 ** 3?", ["6", "5", "9", "8"], 3, "** is the power operator, so 2 ** 3 means 2 x 2 x 2 = 8."),
        ("Which operator checks whether two values are equal?", ["=", "!=", "==", "=>"], 2, "== compares values. A single = assigns a value to a variable."),
    ],
    "Strings": [
        ("What is 'hello'[1]?", ["'h'", "'l'", "'o'", "'e'"], 3, "Indexing starts at 0, so index 1 is the second character, 'e'."),
        ("What does len('python') return?", ["5", "7", "6", "'python'"], 2, "len() counts the characters. 'python' has 6."),
        ("What is 'ab' * 3?", ["'ababab'", "'ab3'", "6", "An error"], 0, "Multiplying a string repeats it, so 'ab' * 3 is 'ababab'."),
        ("What does 'Hello'.upper() return?", ["'HELLO'", "'hello'", "None, and it changes the original", "'Hello'"], 0, "upper() returns a new uppercase string. Strings cannot be changed in place."),
    ],
    "Input and output": [
        ("What type does input() always return?", ["int", "float", "bool", "str"], 3, "input() returns whatever the user typed as text, even if they typed digits."),
        ("Which line prints Hello on the screen?", ["print('Hello')", "echo('Hello')", "output('Hello')", "console.log('Hello')"], 0, "print() is the built-in function that shows output."),
        ("age = input('Age: ') and the user types 5. What does age + 1 do?", ["It gives 6", "It gives 51", "It raises a TypeError", "It gives '5+1'"], 2, "age is the text '5'. Python will not add a number to text, so you get a TypeError."),
        ("How do you read a whole number from the user?", ["input(int)", "number(input())", "input().int", "int(input())"], 3, "input() gives text, and int() converts that text to a whole number."),
    ],
    "Conditionals": [
        ("Which keyword adds a second condition after an if?", ["else if", "elseif", "elif", "otherwise"], 2, "Python spells it elif."),
        ("What prints? x = 5, then: if x > 3: print('big') else: print('small')", ["small", "bigsmall", "Nothing", "big"], 3, "5 > 3 is True, so only the if branch runs and prints big."),
        ("What must come at the end of an if line?", ["A colon", "Curly braces", "A semicolon", "The word then"], 0, "Python needs a colon after the condition, then an indented block."),
        ("How does Python know which lines belong to an if block?", ["Curly braces", "An end if line", "Indentation", "Parentheses"], 2, "Indentation defines the block in Python."),
    ],
    "Boolean logic": [
        ("What is True and False?", ["True", "None", "False", "An error"], 2, "and is True only when both sides are True."),
        ("What is not (5 > 3)?", ["True", "5", "An error", "False"], 3, "5 > 3 is True, and not flips it to False."),
        ("What is True or False?", ["True", "False", "None", "An error"], 0, "or is True when at least one side is True."),
        ("With x = 4, which expression is True?", ["x > 2 and x < 6", "x < 2 or x > 6", "x > 2 and x > 6", "not x == 4"], 0, "4 is greater than 2 and less than 6, so both parts are True."),
    ],
    "Lists": [
        ("What does nums.append(4) do?", ["Adds 4 at the end of the list", "Adds 4 at the start", "Replaces the last item", "Removes the last item"], 0, "append() adds one item to the end of the list."),
        ("What does len([10, 20, 30]) return?", ["2", "30", "3", "60"], 2, "len() counts the items. The list has 3."),
        ("Which line creates an empty list?", ["{}", "()", "[]", "list{}"], 2, "Square brackets make a list. {} makes an empty dictionary."),
        ("After nums = [1, 2, 3] and nums[0] = 9, what is nums?", ["A TypeError, lists cannot change", "[1, 2, 9]", "[9]", "[9, 2, 3]"], 3, "Lists can be changed in place, so index 0 now holds 9."),
    ],
    "Indexing": [
        ("With nums = [10, 20, 30, 40], what is nums[1]?", ["10", "30", "20", "40"], 2, "Indexes start at 0, so nums[1] is the second item, 20."),
        ("With the same list, what is nums[-1]?", ["40", "10", "30", "An error"], 0, "Negative indexes count from the end, so -1 is the last item."),
        ("What is nums[1:3]?", ["[20, 30, 40]", "[10, 20, 30]", "[20, 30]", "[10, 20]"], 2, "A slice starts at index 1 and stops before index 3."),
        ("What happens with nums[4] on a list of 4 items?", ["IndexError", "None", "40", "0"], 0, "Valid indexes are 0 to 3. Index 4 is out of range and raises IndexError."),
    ],
    "Loops": [
        ("How many times does the body of for i in range(3): run?", ["2", "4", "3", "Forever"], 2, "range(3) gives 0, 1, 2, which is 3 repeats."),
        ("What does range(2, 5) produce?", ["2, 3, 4, 5", "3, 4", "2, 3, 4", "2, 5"], 2, "range starts at the first number and stops before the second."),
        ("Which loop repeats while a condition stays True?", ["for", "repeat", "loop", "while"], 3, "A while loop keeps going as long as its condition is True."),
        ("What does for ch in 'abc': print(ch) do?", ["Prints each letter on its own line", "Prints abc on one line", "Prints the number 3", "Prints nothing"], 0, "Looping over a string gives one character at a time."),
    ],
    "Loop control": [
        ("What does break do inside a loop?", ["Skips to the next iteration", "Pauses the loop", "Exits the loop immediately", "Restarts the loop"], 2, "break ends the whole loop right away."),
        ("What does continue do inside a loop?", ["Skips the rest of this iteration and moves to the next", "Exits the loop", "Ends the program", "Repeats the same iteration"], 0, "continue jumps to the next pass of the loop."),
        ("What prints? for i in range(5): if i == 3: break, then print(i)", ["0 1 2 3", "0 1 2 3 4", "0 1 2 4", "0 1 2"], 3, "The loop stops when i reaches 3, before 3 is printed."),
        ("What prints? for i in range(4): if i == 2: continue, then print(i)", ["0 1", "0 1 2 3", "0 1 3", "1 3"], 2, "When i is 2, continue skips the print. Every other value prints."),
    ],
    "Functions": [
        ("Which keyword defines a function?", ["function", "fun", "define", "def"], 3, "Python functions start with def."),
        ("What does a function return if it has no return statement?", ["0", "An empty string", "None", "An error"], 2, "Without return, Python gives back None."),
        ("How do you run a function named greet that takes no arguments?", ["greet()", "greet", "run greet", "call greet"], 0, "Writing the name followed by parentheses calls the function."),
        ("Why do we write functions?", ["To reuse code under one name", "To make every program faster", "Python forces it", "To hide errors"], 0, "A function packages steps so you can reuse them without copying code."),
    ],
    "Parameters": [
        ("In def add(a, b) called as add(2, 3), what are a and b?", ["Parameters that receive 2 and 3", "Return values", "Global variables", "Modules"], 0, "Parameters are the names in the definition. They receive the values you pass in."),
        ("With def hi(name='friend'), what is name when you call hi()?", ["An error", "None", "'friend'", "An empty string"], 2, "A default value is used when no argument is given."),
        ("What is the difference between a parameter and an argument?", ["An argument is in the definition; a parameter is passed in the call", "They are exactly the same thing", "Parameters exist only in built-in functions", "A parameter is the name in the definition; an argument is the value passed in"], 3, "The definition lists parameters. The call supplies arguments."),
        ("What happens if you call def f(a, b) as f(1)?", ["TypeError: missing argument", "b becomes 0", "b becomes None", "It returns 1"], 0, "Python needs a value for every parameter that has no default."),
    ],
    "Return values": [
        ("With def sq(x): return x * x, what is sq(4)?", ["8", "None", "x * x", "16"], 3, "The function returns 4 * 4, which is 16."),
        ("What is the difference between print and return?", ["return shows a value on screen; print gives it back", "They are identical", "print stops the function", "print shows a value on screen; return hands a value back to the caller"], 3, "print only displays something. return sends a value back so the code can use it."),
        ("What happens to code after a return statement in the same function?", ["It runs normally", "It runs twice", "It is skipped", "It runs before the return"], 2, "return ends the function immediately."),
        ("Can a function return more than one value?", ["Yes, as a tuple such as return a, b", "No, only one value is allowed", "Only if you use global", "Only if they are lists"], 0, "Returning a, b packs both values into a tuple."),
    ],
    "Scope": [
        ("A variable is created inside a function. What happens if you print it outside?", ["It prints the value", "It prints None", "It prints 0", "A NameError is raised"], 3, "Variables made inside a function are not visible outside it."),
        ("x = 10 outside, then def f(): x = 5. After f(), what does print(x) show?", ["5", "None", "An error", "10"], 3, "The x inside f is a separate local variable. The global x stays 10."),
        ("What is a local variable?", ["Available everywhere in the file", "Stored in a separate file", "Created inside a function and available only there", "Always a number"], 2, "Local variables live only while their function runs."),
        ("Which keyword lets a function change a global variable?", ["static", "local", "outer", "global"], 3, "Writing global x inside the function makes assignments change the outer x."),
    ],
    "Dictionaries": [
        ("With d = {'a': 1}, what is d['a']?", ["'a'", "{'a': 1}", "KeyError", "1"], 3, "Looking up a key returns the value stored with it."),
        ("What happens with d['b'] if 'b' is not a key?", ["KeyError", "None", "0", "An empty string"], 0, "Reading a missing key with square brackets raises KeyError."),
        ("Which line adds key 'c' with value 3?", ["d.add('c', 3)", "d.append('c', 3)", "d{'c'} = 3", "d['c'] = 3"], 3, "Assigning to a new key adds it to the dictionary."),
        ("What does d.get('z', 0) return when 'z' is missing?", ["0", "KeyError", "None", "'z'"], 0, "get() returns the default you give instead of raising an error."),
    ],
    "Tuples and sets": [
        ("Which of these is a tuple?", ["[1, 2]", "{1, 2}", "(1, 2)", "{'a': 1}"], 2, "Round brackets make a tuple."),
        ("What happens with t = (1, 2, 3) and then t[0] = 9?", ["t becomes (9, 2, 3)", "9 is added to t", "t[0] is deleted", "A TypeError, because tuples cannot be changed"], 3, "Tuples are immutable, so you cannot assign to an index."),
        ("What does set([1, 2, 2, 3]) give?", ["{1, 2, 2, 3}", "[1, 2, 3]", "{1, 3}", "{1, 2, 3}"], 3, "A set keeps each value only once."),
        ("Which statement about sets is true?", ["They hold unique items; duplicates are dropped", "They keep duplicates in order", "You read items by index like s[0]", "You can only create them with []"], 0, "Sets store unique values and have no index positions."),
    ],
})


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
        for title, bank_items in QUESTION_BANK.items():
            if title not in CONCEPT_NAMES:
                continue
            q_slug = title.lower().replace(" ", "-")
            current = db.scalars(
                select(Question).where(Question.concept_slug == q_slug).order_by(Question.id)
            ).all()
            for idx, (q_prompt, q_options, q_correct, q_expl) in enumerate(bank_items):
                if idx < len(current):
                    row = current[idx]
                    row.prompt = q_prompt
                    row.options = q_options
                    row.correct_index = q_correct
                    row.explanation = q_expl
                    row.misconception_ids = ["", f"misunderstands_{q_slug}", "", ""]
                else:
                    db.add(
                        Question(
                            concept_slug=q_slug,
                            prompt=q_prompt,
                            options=q_options,
                            correct_index=q_correct,
                            explanation=q_expl,
                            misconception_ids=["", f"misunderstands_{q_slug}", "", ""],
                        )
                    )
        db.flush()
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
