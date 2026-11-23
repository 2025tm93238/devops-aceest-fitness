# Changelog

All notable changes to the ACEest Fitness & Gym API. Versions follow
[Semantic Versioning](https://semver.org/); each release is a git tag
(`vX.Y.Z`) and a Docker Hub image tag of the same name.

## [1.1.0]
### Added
- `version.py` as the single source of truth for the app version.
- `GET /version` returning version, deployment track and pod name (used to
  observe blue-green / canary / A/B / shadow deployments).
- `/health` now reports the running version.
- `GET /export/clients.csv` — CSV export of all clients (ported from `Aceestver1.1.2`).
- `versions/` folder with the original provided application versions.
### Changed
- Database helpers extracted into `db.py`; shared test fixtures in `tests/conftest.py`.

## [1.0.0]
### Added
- Assignment 1 baseline: Flask REST API (clients, programs, BMI, workouts,
  metrics, progress, summary) with SQLite, 15 pytest cases, multi-stage
  Dockerfile, Jenkins BUILD pipeline and GitHub Actions workflow.
