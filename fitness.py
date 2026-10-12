"""Core fitness domain logic for ACEest Fitness & Gym.

These are pure functions with no database or web framework dependencies, which
keeps them trivial to unit test. The numbers and categories here are carried
over directly from the original desktop prototype so behaviour stays identical.
"""

# Training programs offered by the gym. ``factor`` is the kcal-per-kg multiplier
# used to estimate a client's daily calorie target.
PROGRAMS = {
    "Fat Loss (FL) - 3 day": {"factor": 22, "desc": "3-day full-body fat loss"},
    "Fat Loss (FL) - 5 day": {"factor": 24, "desc": "5-day split, higher volume fat loss"},
    "Muscle Gain (MG) - PPL": {"factor": 35, "desc": "Push/Pull/Legs hypertrophy"},
    "Beginner (BG)": {"factor": 26, "desc": "3-day simple beginner full-body"},
}


def calculate_calories(weight, program):
    """Estimate daily calories as bodyweight (kg) * the program's factor."""
    if program not in PROGRAMS:
        raise ValueError(f"Unknown program: {program}")
    if weight is None or weight <= 0:
        raise ValueError("Weight must be a positive number")
    return int(weight * PROGRAMS[program]["factor"])


def calculate_bmi(weight, height_cm):
    """Return BMI = weight(kg) / height(m)^2, rounded to one decimal place."""
    if weight is None or weight <= 0:
        raise ValueError("Weight must be a positive number")
    if height_cm is None or height_cm <= 0:
        raise ValueError("Height must be a positive number")
    height_m = height_cm / 100.0
    return round(weight / (height_m * height_m), 1)


def bmi_category(bmi):
    """Map a BMI value to a (category, risk note) pair."""
    if bmi < 18.5:
        return "Underweight", "Potential nutrient deficiency, low energy."
    if bmi < 25:
        return "Normal", "Low risk if active and strong."
    if bmi < 30:
        return "Overweight", "Moderate risk; focus on adherence and progressive activity."
    return "Obese", "Higher risk; prioritize fat loss, consistency, and supervision."
