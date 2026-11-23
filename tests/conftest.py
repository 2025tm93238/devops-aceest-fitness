"""Shared pytest fixtures for the ACEest Fitness & Gym test suite."""

import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    """A Flask app backed by a fresh, throwaway SQLite database per test."""
    application = create_app(database=str(tmp_path / "test.db"))
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(app):
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def make_client(client):
    """Factory that creates a gym client through the public API."""

    def _make(name="Asha", **overrides):
        payload = {
            "name": name,
            "age": 30,
            "height": 170,
            "weight": 70,
            "program": "Muscle Gain (MG) - PPL",
        }
        payload.update(overrides)
        return client.post("/clients", json=payload)

    return _make
