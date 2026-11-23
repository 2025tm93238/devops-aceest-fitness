# Original ACEest application versions

These are the incremental Tkinter desktop versions provided with the assignment,
kept unchanged for traceability. The Flask web service in the repository root
re-implements their features as a REST API, released under semantic version tags.

| Provided file | Key features introduced | Ported in Flask release |
|---|---|---|
| `Aceestver-1.0.py` | Program catalogue (Fat Loss / Muscle Gain / Beginner) | v1.0.0 |
| `Aceestver-1.1.py` | Client profile, calorie estimate per program | v1.0.0 |
| `Aceestver1.1.2.py` | CSV export of clients, adherence chart | v1.1.0 (CSV export) |
| `Aceestver2.0.1.py` / `Aceestver-2.1.2.py` | SQLite persistence, weekly progress | v1.0.0 |
| `Aceestver-2.2.1.py` | Progress chart | v1.0.0 (data via `/summary`) |
| `Aceestver-2.2.4.py` / `Aceestver-3.0.1.py` | Workouts, body metrics, BMI info, summary | v1.0.0 |
| `Aceestver-3.2.4.py` | Role-based login, membership status / renewal | v2.0.0 |
| `Aceestver-3.1.2.py` | AI-style program generator by experience level | v2.1.0 |
| `Aceestver-3.1.2.py` / `Aceestver-3.2.4.py` | PDF client report | v3.0.0 |

Notes:
- `Aceestver-2.1.2.py` is byte-identical to `Aceestver2.0.1.py`, and
  `Aceestver-3.0.1.py` is identical to `Aceestver-2.2.4.py`, as provided.
- These files are excluded from linting, the Docker image and SonarQube analysis.
