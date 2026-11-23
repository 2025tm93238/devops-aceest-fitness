"""AI-style weekly workout plan generator (ported from Aceestver-3.1.2).

The desktop version filled a Tkinter tree view; here the same rules produce a
JSON-serialisable plan. A ``seed`` makes generation reproducible, which keeps
the function deterministic under test.
"""

import random

EXERCISE_POOL = {
    "Strength": ["Squat", "Deadlift", "Bench Press", "Overhead Press", "Pull-Up", "Barbell Row"],
    "Hypertrophy": ["Leg Press", "Incline Dumbbell Press", "Lat Pulldown", "Lateral Raise",
                    "Bicep Curl", "Tricep Extension"],
    "Conditioning": ["Running", "Cycling", "Rowing", "Burpees", "Jump Rope",
                     "Kettlebell Swings"],
    "Full Body": ["Push-Up", "Pull-Up", "Lunge", "Plank", "Dumbbell Row", "Dumbbell Press"],
}

# experience level -> (sets range, reps range, training days per week)
EXPERIENCE_LEVELS = {
    "beginner": ((2, 3), (8, 12), 3),
    "intermediate": ((3, 4), (8, 15), 4),
    "advanced": ((4, 5), (6, 15), 5),
}

WEEK_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


def focus_for_program(program_name):
    """Pick the training focus from the client's enrolled program."""
    program_name = program_name or ""
    if "Fat Loss" in program_name:
        return "Conditioning"
    if "Muscle Gain" in program_name:
        return "Hypertrophy"
    return "Full Body"


def generate_plan(program_name, experience, seed=None):
    """Return a weekly plan as a list of {day, exercise, sets, reps} dicts.

    Raises ValueError for an unknown experience level.
    """
    level = (experience or "").lower()
    if level not in EXPERIENCE_LEVELS:
        raise ValueError(f"experience must be one of {sorted(EXPERIENCE_LEVELS)}")
    sets_range, reps_range, days = EXPERIENCE_LEVELS[level]
    focus = focus_for_program(program_name)
    # Not security sensitive: randomness only varies exercise selection.
    rng = random.Random(seed)  # NOSONAR
    per_day = 3 if days < 4 else 4

    plan = []
    for day in WEEK_DAYS[:days]:
        for exercise in rng.sample(EXERCISE_POOL[focus], k=per_day):
            plan.append({
                "day": day,
                "exercise": exercise,
                "sets": rng.randint(*sets_range),
                "reps": rng.randint(*reps_range),
            })
    return {"focus": focus, "experience": level, "days_per_week": days, "plan": plan}
