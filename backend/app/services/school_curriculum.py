"""Delta for School — fixed curriculum (CBSE / NCERT), as data.

Adding a subject, grade or board is a data change here, not a code change.

⚠ Verify before launch: chapter lists must match the current NCERT textbooks
(https://ncert.nic.in/textbook.php). Classes 9–10 follow the rationalised
2023-24 books. Classes 6–8 moved to the new NCERT books (Ganita Prakash /
Curiosity) from 2024-25. Those lists are marked `verify=True` and must be
checked against the printed books, since chapter titles and order may differ.
Lessons are only shown after human review, so a reviewer should catch a wrong
title before any child sees it.
"""
from __future__ import annotations

BOARD = "CBSE"
GRADES = [6, 7, 8, 9, 10]
SUBJECTS = {"maths": "Mathematics", "science": "Science"}
NCERT_TEXTBOOK_PORTAL = "https://ncert.nic.in/textbook.php"

CURRICULUM: dict[int, dict[str, dict]] = {
    6: {
        "maths": {"textbook": "Ganita Prakash (Class 6)", "verify": True, "chapters": [
            "Patterns in Mathematics", "Lines and Angles", "Number Play", "Data Handling and Presentation",
            "Prime Time", "Perimeter and Area", "Fractions", "Playing with Constructions", "Symmetry",
            "The Other Side of Zero",
        ]},
        "science": {"textbook": "Curiosity (Class 6)", "verify": True, "chapters": [
            "The Wonderful World of Science", "Diversity in the Living World", "Mindful Eating: A Path to a Healthy Body",
            "Exploring Magnets", "Measurement of Length and Motion", "Materials Around Us",
            "Temperature and its Measurement", "A Journey through States of Water",
            "Methods of Separation in Everyday Life", "Living Creatures: Exploring their Characteristics",
            "Nature's Treasures", "Beyond Earth",
        ]},
    },
    7: {
        "maths": {"textbook": "Ganita Prakash (Class 7, Part 1)", "verify": True, "chapters": [
            "Large Numbers Around Us", "Arithmetic Expressions", "A Peek Beyond the Point",
            "Expressions using Letter-Numbers", "Parallel and Intersecting Lines", "Number Play",
            "A Tale of Three Intersecting Lines", "Working with Fractions",
        ]},
        "science": {"textbook": "Curiosity (Class 7)", "verify": True, "chapters": [
            "The Ever-Evolving World of Science", "Exploring Substances: Acidic, Basic, and Neutral",
            "Electricity: Circuits and their Components", "The World of Metals and Non-metals",
            "Changes Around Us: Physical and Chemical", "Adolescence: A Stage of Growth and Change",
            "Heat Transfer in Nature", "Measurement of Time and Motion", "Life Processes in Animals",
            "Life Processes in Plants", "Light: Shadows and Reflections", "Earth, Moon, and the Sun",
        ]},
    },
    8: {
        "maths": {"textbook": "Ganita Prakash (Class 8, Part 1)", "verify": True, "chapters": [
            "A Square and a Cube", "Power Play", "A Story of Numbers", "Quadrilaterals", "Number Play",
            "We Distribute, Yet Things Multiply", "Proportional Reasoning",
        ]},
        "science": {"textbook": "Curiosity (Class 8)", "verify": True, "chapters": [
            "Exploring the Investigative World of Science", "The Invisible Living World: Beyond Our Naked Eye",
            "Health: The Ultimate Treasure", "Electricity: Magnetic and Heating Effects", "Exploring Forces",
            "Pressure, Winds, Storms, and Cyclones", "Particulate Nature of Matter",
            "Nature of Matter: Elements, Compounds, and Mixtures",
            "The Amazing World of Solutes, Solvents, and Solutions", "Light: Mirrors and Lenses",
            "Keeping Time with the Skies", "How Nature Works in Harmony",
            "Our Home: Earth, a Unique Life Sustaining Planet",
        ]},
    },
    9: {
        "maths": {"textbook": "Mathematics (Class 9)", "verify": False, "chapters": [
            "Number Systems", "Polynomials", "Coordinate Geometry", "Linear Equations in Two Variables",
            "Introduction to Euclid's Geometry", "Lines and Angles", "Triangles", "Quadrilaterals", "Circles",
            "Heron's Formula", "Surface Areas and Volumes", "Statistics",
        ]},
        "science": {"textbook": "Science (Class 9)", "verify": False, "chapters": [
            "Matter in Our Surroundings", "Is Matter Around Us Pure?", "Atoms and Molecules",
            "Structure of the Atom", "The Fundamental Unit of Life", "Tissues", "Motion",
            "Force and Laws of Motion", "Gravitation", "Work and Energy", "Sound",
            "Improvement in Food Resources",
        ]},
    },
    10: {
        "maths": {"textbook": "Mathematics (Class 10)", "verify": False, "chapters": [
            "Real Numbers", "Polynomials", "Pair of Linear Equations in Two Variables", "Quadratic Equations",
            "Arithmetic Progressions", "Triangles", "Coordinate Geometry", "Introduction to Trigonometry",
            "Some Applications of Trigonometry", "Circles", "Areas Related to Circles",
            "Surface Areas and Volumes", "Statistics", "Probability",
        ]},
        "science": {"textbook": "Science (Class 10)", "verify": False, "chapters": [
            "Chemical Reactions and Equations", "Acids, Bases and Salts", "Metals and Non-metals",
            "Carbon and its Compounds", "Life Processes", "Control and Coordination",
            "How do Organisms Reproduce?", "Heredity", "Light – Reflection and Refraction",
            "The Human Eye and the Colourful World", "Electricity", "Magnetic Effects of Electric Current",
            "Our Environment",
        ]},
    },
}


def book(grade: int, subject: str) -> dict | None:
    return CURRICULUM.get(grade, {}).get(subject)


def chapter_title(grade: int, subject: str, chapter_no: int) -> str | None:
    b = book(grade, subject)
    if not b or not (1 <= chapter_no <= len(b["chapters"])):
        return None
    return b["chapters"][chapter_no - 1]
