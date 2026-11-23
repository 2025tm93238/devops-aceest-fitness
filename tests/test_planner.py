"""Tests for v2.1.0: AI-style workout plan generator."""

import pytest

from planner import EXERCISE_POOL, focus_for_program, generate_plan


@pytest.mark.parametrize("program, focus", [
    ("Fat Loss (FL) - 3 day", "Conditioning"),
    ("Muscle Gain (MG) - PPL", "Hypertrophy"),
    ("Beginner (BG)", "Full Body"),
    (None, "Full Body"),
])
def test_focus_for_program(program, focus):
    assert focus_for_program(program) == focus


@pytest.mark.parametrize("level, days, per_day, sets, reps", [
    ("beginner", 3, 3, (2, 3), (8, 12)),
    ("Intermediate", 4, 4, (3, 4), (8, 15)),
    ("ADVANCED", 5, 4, (4, 5), (6, 15)),
])
def test_plan_shape_follows_experience(level, days, per_day, sets, reps):
    result = generate_plan("Muscle Gain (MG) - PPL", level, seed=1)
    assert result["days_per_week"] == days
    assert len(result["plan"]) == days * per_day
    for item in result["plan"]:
        assert item["exercise"] in EXERCISE_POOL["Hypertrophy"]
        assert sets[0] <= item["sets"] <= sets[1]
        assert reps[0] <= item["reps"] <= reps[1]


def test_no_duplicate_exercise_within_a_day():
    plan = generate_plan("Beginner (BG)", "advanced", seed=7)["plan"]
    for day in {p["day"] for p in plan}:
        names = [p["exercise"] for p in plan if p["day"] == day]
        assert len(names) == len(set(names))


def test_seed_makes_plan_reproducible():
    assert generate_plan("Beginner (BG)", "beginner", seed=42) == \
        generate_plan("Beginner (BG)", "beginner", seed=42)


def test_invalid_experience_rejected():
    with pytest.raises(ValueError):
        generate_plan("Beginner (BG)", "expert")


def test_generate_program_endpoint(client, make_client):
    make_client(program="Fat Loss (FL) - 3 day")
    resp = client.post("/clients/Asha/program/generate",
                       json={"experience": "beginner", "seed": 3})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["focus"] == "Conditioning"
    assert body["days_per_week"] == 3 and len(body["plan"]) == 9


def test_generate_program_endpoint_errors(client, make_client):
    assert client.post("/clients/Ghost/program/generate",
                       json={"experience": "beginner"}).status_code == 404
    make_client()
    assert client.post("/clients/Asha/program/generate", json={}).status_code == 400
