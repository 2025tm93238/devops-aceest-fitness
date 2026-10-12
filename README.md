# ACEest Fitness & Gym — CI/CD Pipeline

![CI](https://github.com/2025tm93238/devops-aceest-fitness/actions/workflows/main.yml/badge.svg)

A **Flask-based REST API** for managing gym clients, training programs, workouts,
body metrics and weekly progress — wrapped in a complete, automated DevOps
workflow: **Git/GitHub → Pytest → Docker → GitHub Actions → Jenkins**.

The application auto-computes each client's daily calorie target from their
program and bodyweight, and classifies BMI with a risk note. The core business
logic is isolated from the web and database layers so it is easy to test, and
the whole service is containerized for "write once, run anywhere" consistency.

---

## Table of contents
1. [Features & API](#features--api-endpoints)
2. [Project structure](#project-structure)
3. [Local setup & execution](#1-local-setup--execution)
4. [Running the tests manually](#2-running-the-tests-manually)
5. [Running with Docker](#3-running-with-docker)
6. [CI/CD integration logic (GitHub Actions & Jenkins)](#4-cicd-integration-logic)
7. [Evaluation criteria mapping](#evaluation-criteria-mapping)
8. [Tech stack](#tech-stack)

---

## Features & API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET`  | `/health` | Liveness check (used by CI and container smoke tests) |
| `GET`  | `/` | API metadata and endpoint list |
| `GET`  | `/programs` | List available training programs |
| `POST` | `/clients` | Create/update a client (auto-computes daily calories) |
| `GET`  | `/clients` | List all clients |
| `GET`  | `/clients/<name>` | Fetch a single client |
| `GET`  | `/clients/<name>/bmi` | Compute BMI + category + risk note |
| `POST` | `/clients/<name>/workouts` | Log a workout session |
| `GET`  | `/clients/<name>/workouts` | Workout history |
| `POST` | `/clients/<name>/metrics` | Log body metrics (weight/waist/bodyfat) |
| `GET`  | `/clients/<name>/metrics` | Metrics history |
| `POST` | `/clients/<name>/progress` | Log weekly adherence |
| `GET`  | `/clients/<name>/summary` | Aggregated client summary |

**Domain rules** (in `fitness.py`, fully unit-tested):
- Daily calories = `bodyweight(kg) × program factor`
- BMI = `weight(kg) / height(m)²`, categorised Underweight / Normal / Overweight / Obese

---

## Project structure

```
aceest-fitness/
├── app.py                     # Flask application (REST API + SQLite, app-factory pattern)
├── fitness.py                 # Pure domain logic (BMI, calories) — isolated for unit testing
├── requirements.txt           # Runtime dependencies (Flask, gunicorn)
├── requirements-dev.txt       # Dev/CI dependencies (pytest, flake8)
├── tests/
│   └── test_app.py            # Pytest suite (16 tests: logic + endpoints)
├── Dockerfile                 # Multi-stage build: base → test → production
├── .dockerignore
├── .github/workflows/main.yml # GitHub Actions CI pipeline
├── Jenkinsfile                # Jenkins BUILD pipeline
├── pytest.ini                 # Pytest config (adds project root to path)
├── .flake8                    # Lint config
└── README.md
```

---

## 1. Local setup & execution

**Prerequisites:** Python 3.9+ (3.12 recommended).

```bash
# Clone the repository
git clone https://github.com/2025tm93238/devops-aceest-fitness.git
cd devops-aceest-fitness

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt

# Run the application (development server)
python app.py
# The API is now live at http://localhost:5000
```

**Try it:**

```bash
curl http://localhost:5000/health

curl -X POST http://localhost:5000/clients \
     -H "Content-Type: application/json" \
     -d '{"name":"Asha","age":30,"height":170,"weight":70,"program":"Muscle Gain (MG) - PPL"}'

curl http://localhost:5000/clients/Asha/bmi
```

Expected:
```json
{"status":"ok"}
{"name":"Asha","calories":2450, ...}
{"bmi":24.2,"category":"Normal","name":"Asha","risk":"Low risk if active and strong."}
```

---

## 2. Running the tests manually

```bash
# Lint — compile/syntax & style check (the "Build & Lint" gate)
flake8 .

# Run the full unit-test suite
pytest -q           # quiet; use `pytest -v` for a per-test breakdown
```

Expected result: **`16 passed`**.

The suite covers both the **pure domain logic** (BMI, calorie calculation,
category boundaries, input validation) and **every API endpoint** end-to-end
against a throwaway SQLite database, so no state leaks between tests.

---

## 3. Running with Docker

The `Dockerfile` is **multi-stage**:

| Stage | Purpose |
|-------|---------|
| `base` | Installs runtime deps and copies the source (shared layer) |
| `test` | Adds pytest/flake8 and runs the suite **inside a container** |
| `production` | Lean image, runs as a **non-root** user via **gunicorn** |

```bash
# Build the production image (~126 MB, slim base, non-root)
docker build --target production -t aceest-fitness .

# Run the container
docker run -p 5000:5000 aceest-fitness
curl http://localhost:5000/health

# Run the test suite inside a container (as the CI pipeline does)
docker build --target test -t aceest-fitness:test .
docker run --rm aceest-fitness:test          # -> 16 passed
```

**Docker efficiency notes:** a `python:3.12-slim` base, `--no-cache-dir` installs,
`requirements.txt` copied before the source for layer caching, a `.dockerignore`
to keep the context small, and a dedicated non-root `appuser` for the production
stage.

---

## 4. CI/CD integration logic

Two independent systems provide continuous integration and a controlled build
gate. Together they ensure every change compiles, containerizes and passes its
tests before it can be considered done.

### GitHub Actions — `.github/workflows/main.yml`

Triggered on **every `push` and `pull_request`**. It runs two jobs:

1. **`build-and-test`** (on the runner)
   - **Build & Lint** — `flake8` + `python -m compileall` to catch syntax errors.
   - **Automated Testing** — `pytest`.
2. **`docker`** (runs only after `build-and-test` passes)
   - **Docker Image Assembly** — builds the production image.
   - **Automated Testing (in container)** — builds the `test` stage and runs
     `pytest` **inside the container**, confirming stability in the packaged
     environment.
   - **Smoke test** — starts the container and asserts `/health` responds.

This maps one-to-one onto the assignment's required stages:
*Build & Lint → Docker Image Assembly → Automated Testing.*

### Jenkins — `Jenkinsfile`

Jenkins provides the primary **BUILD** stage as an independent, controlled
validation layer. A Pipeline job (*Pipeline script from SCM*) is pointed at this
GitHub repository on branch `main`; on trigger it:

1. **Checkout** — pulls the latest code from GitHub.
2. **Build Docker image** — a clean build of the environment.
3. **Test in container** — runs the pytest suite inside the freshly built image.
4. **Smoke test** — boots the container and checks `/health`.

**In short:** GitHub Actions gives fast feedback on every push/PR, while Jenkins
independently re-verifies that the code compiles, containerizes and passes its
tests in a separate controlled environment — a secondary quality gate.

---

## Evaluation criteria mapping

| Criterion | How this project satisfies it |
|-----------|-------------------------------|
| **Application Integrity** | Flask API functions as specified; verified live and via 15 tests |
| **VCS Maturity** | Logically structured, descriptive commits on a public repo |
| **Testing Coverage** | Pytest covers domain logic + every endpoint (16 cases) |
| **Docker Efficiency** | Multi-stage, slim base, non-root, cached layers (~126 MB) |
| **Pipeline Reliability** | Jenkins BUILD completes without errors; Actions passes build+test on every push |
| **Documentation Clarity** | This README (setup, manual tests, CI/CD overview) |

---

## Tech stack

Python 3.12 · Flask · gunicorn · SQLite · Pytest · flake8 · Docker (multi-stage)
· GitHub Actions · Jenkins.

---

*Author: Teja (BITS ID 2025TM93238) — Introduction to DevOps, Assignment 1.*
