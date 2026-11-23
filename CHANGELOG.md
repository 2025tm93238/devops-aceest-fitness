# Changelog

All notable changes to the ACEest Fitness & Gym API. Versions follow
[Semantic Versioning](https://semver.org/); each release is a git tag
(`vX.Y.Z`) and a Docker Hub image tag of the same name.

## [2.1.0]
### Added
- AI-style weekly workout plan generator (`planner.py`, ported from
  `Aceestver-3.1.2`): `POST /clients/<name>/program/generate` with
  `experience` = beginner / intermediate / advanced and optional `seed`.

## [2.0.0]
### Added
- Role-based authentication (`auth.py`, ported from `Aceestver-3.2.4` login):
  `POST /auth/login` issues a signed, time-limited bearer token; `GET /auth/me`;
  `POST /auth/users` (Admin) creates Admin/Trainer accounts. Passwords are hashed.
- Default `admin` account seeded on first start; password from `ADMIN_PASSWORD`.
- Membership management (`membership.py`): new clients get a 30-day Active trial,
  `GET /clients/<name>/membership`, `POST /clients/<name>/membership/renew` (token).
- `DELETE /clients/<name>` (Admin only).
- In-place schema migration so v1.x databases upgrade without data loss.
### Changed
- **Breaking:** `SECRET_KEY` must be set (identically on all replicas) in production.
### Fixed
- Updating an existing client no longer deletes and re-creates its row
  (`INSERT OR REPLACE` replaced by an upsert), preserving id and membership.
- Container crashed on start-up when gunicorn workers booted together against a
  fresh database (race on the admin seed and the migration); both are now
  idempotent and covered by a multi-process regression test.

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
