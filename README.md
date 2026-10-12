# ACEest Fitness & Gym — CI/CD Pipeline

A Flask-based REST API for managing gym clients, workouts, body metrics and
training progress, wrapped in a complete DevOps workflow: **Git/GitHub →
Pytest → Docker → GitHub Actions → Jenkins**.

This project was built for the *Introduction to DevOps* assignment. The core
business logic (programs, calorie estimation, BMI, workout/metric tracking) is
ported from a desktop prototype into a web service so it can be tested,
containerized and deployed through an automated pipeline.

---

## Features / API Endpoints

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
├── app.py                     # Flask application (REST API + SQLite)
├── fitness.py                 # Pure domain logic (BMI, calories) — easy to unit test
├── requirements.txt           # Runtime dependencies (Flask, gunicorn)
├── requirements-dev.txt       # Dev/CI dependencies (pytest, flake8)
├── tests/
│   └── test_app.py            # Pytest suite (logic + endpoints)
├── Dockerfile                 # Multi-stage: base → test → production
├── .dockerignore
├── .github/workflows/main.yml # GitHub Actions CI pipeline
├── Jenkinsfile                # Jenkins BUILD pipeline
├── pytest.ini
├── .flake8
└── README.md
```

---

## 1. Local setup & execution

Requires Python 3.12+.

```bash
# Clone and enter the project
git clone <your-repo-url>
cd aceest-fitness

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt

# Run the application (development server)
python app.py
# App is now live at http://localhost:5000
```

Try it:

```bash
curl http://localhost:5000/health
curl -X POST http://localhost:5000/clients \
     -H "Content-Type: application/json" \
     -d '{"name":"Asha","age":30,"height":170,"weight":70,"program":"Muscle Gain (MG) - PPL"}'
curl http://localhost:5000/clients/Asha/bmi
```

---

## 2. Running the tests manually

```bash
# Lint for syntax / style issues
flake8 .

# Run the full test suite
pytest -q
```

Expected: `15 passed`.

---

## 3. Running with Docker

The `Dockerfile` is **multi-stage**:
- **`base`** — installs runtime deps and copies the source.
- **`test`** — adds pytest/flake8 and runs the suite *inside a container*.
- **`production`** — lean image, runs as a **non-root** user via **gunicorn**.

```bash
# Build the production image
docker build --target production -t aceest-fitness .

# Run the container
docker run -p 5000:5000 aceest-fitness
curl http://localhost:5000/health

# Run the test suite inside a container
docker build --target test -t aceest-fitness:test .
docker run --rm aceest-fitness:test
```

---

## 4. CI/CD integration overview

### GitHub Actions (`.github/workflows/main.yml`)

Triggered on **every push and pull request**. Two jobs:

1. **`build-and-test`**
   - Build & Lint: `flake8` + `python -m compileall` (catches syntax errors).
   - Automated Testing: `pytest`.
2. **`docker`** (runs after the first job passes)
   - **Docker Image Assembly**: builds the production image.
   - **Automated Testing in-container**: builds the `test` stage and runs `pytest` *inside the container*.
   - **Smoke test**: starts the container and asserts `/health` responds.

This directly implements the pipeline stages required by the assignment:
*Build & Lint → Docker Image Assembly → Automated Testing.*

### Jenkins (`Jenkinsfile`)

Jenkins handles the primary **BUILD** stage as a secondary validation layer. A
Pipeline job is pointed at the GitHub repository; on trigger it:

1. **Checkout** — pulls the latest code from GitHub.
2. **Build Docker image** — a clean build of the environment.
3. **Test in container** — runs the pytest suite inside the freshly built image.
4. **Smoke test** — boots the container and checks `/health`.

Together, **GitHub Actions** provides continuous integration on every push,
while **Jenkins** provides an independent, controlled BUILD environment that
confirms the code compiles, containerizes and passes its tests.

---

## Tech stack

Python 3.12 · Flask · gunicorn · SQLite · Pytest · flake8 · Docker · GitHub
Actions · Jenkins.
