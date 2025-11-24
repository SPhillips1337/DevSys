# Changelog

All notable changes to this project are documented in this file.

Dates are in UTC. This file summarizes the work performed during the DevSys PoC development.

## 2025-11-24 — Initial PoC and scaffolding
- Created repository scaffold for the DevSys PoC: `docker-compose.yml`, `Dockerfile.php`, `README.md`, `PLAN.md`, `TODO.md`.
- Added `project.json` manifest describing goals, features, and how to run locally.
- Initial commit message: "chore: init repo and add DevSys PoC scaffolding (manager, agents, deploy flow, docs)".

## 2025-11-24 — Manager and coding agent
- Added `manager` service (Flask HTTP API) to accept user stories and create task specs.
  - Files: `manager/app.py`, `manager/Dockerfile`, `manager/requirements.txt`, `manager/task_schema.json`.
  - Functionality: create/list/get tasks, update task status, validate specs against a simple JSON schema.
- Added `coding-agent` service to pick up `created` tasks and scaffold a simple static site into `workspace/tasks/<id>/src`.
  - Files: `coding-agent/worker.py`, `coding-agent/Dockerfile`, `coding-agent/requirements.txt`.
- Committed under messages referencing the scaffold and agent additions.

## 2025-11-24 — Deployment flow and PHP deployment target
- Repurposed PHP container to act as a local deployment target.
  - Updated `docker-compose.yml` to mount `./workspace/deploy` and `./workspace/www`.
  - Added `entrypoint.sh` to copy deployed content into `/var/www/html` and to optionally set SSH user data at runtime.
  - Added `apache-site.conf` to allow serving from `/var/www/www`.
  - Updated `Dockerfile.php` to include the entrypoint and site config.
- Implemented `deployment-agent` to:
  - Watch completed tasks (with `deploy: true`), copy artifacts into `./workspace/deploy/<task-id>/current`, archive revisions, and copy to `./workspace/www` for the PHP container.
  - Perform acceptance checks against specified URLs and create follow-up fix tasks on failure.
  - Files: `deployment-agent/worker.py`, `deployment-agent/Dockerfile`, `deployment-agent/requirements.txt`.
- Added manager endpoints for deploy and rollback: `POST /api/tasks/<id>/deploy` and `POST /api/tasks/<id>/rollback`.

## 2025-11-24 — Workspace layout and security improvements
- Added `workspace` usage and `./workspace/deploy`, `./workspace/www` for sharing artifacts and serving deployed content.
- Removed hardcoded SSH password from `Dockerfile.php` and introduced runtime environment configuration to set password or public key via `entrypoint.sh`.
- Added `.env.example` and configured `docker-compose.yml` to read `.env` for runtime secrets (`N8N_USER_PASSWORD`, `N8N_USER_PUBKEY`, `N8N_PASSWORD_AUTH`).
- Added `.gitignore` and initialized a local git repository. Committed multiple changes.

## 2025-11-24 — Manager token-based authentication
- Implemented optional token-based auth for the manager API using `MANAGER_API_TOKEN`.
  - Decorator `@auth_required` enforces token when set.
  - Agents updated to send `Authorization: Bearer <token>` header if `MANAGER_API_TOKEN` present in their environment.
- Updated `.env.example` to document `MANAGER_API_TOKEN`.

## 2025-11-24 — Testing agent and pipeline
- Added `testing-agent` scaffold and service to `docker-compose.yml`.
  - `testing-agent/worker.py`: polls tasks, supports `related_task`, runs tests (script or spec-run), writes reports to `./workspace/tasks/<id>/reports`, updates task status and writes `test_records.json`.
  - `testing-agent/Dockerfile`, `testing-agent/requirements.txt`.
- Added an example test runner script and created a test task `task-002-test` demonstrating the flow.
- Ensured testing-agent reports and status updates are authenticated via `MANAGER_API_TOKEN` when present.

## 2025-11-24 — Test report improvements & manager test API
- Enhanced testing-agent to always write a summary header into reports (RESULT, EXIT_CODE, TIMESTAMP) so quiet tests are informative.
- Rebuilt and restarted testing-agent to pick up the update; re-ran tests and validated reports.
- Added JUnit XML output generation for each test run suitable for CI parsing.
- Implemented a manager API endpoint to fetch the latest test report: `GET /api/tasks/<id>/tests/latest` (protected by token auth when enabled).
- Implemented parallel test runner with configurable `TESTING_CONCURRENCY` and basic task claiming semantics (status set to `testing` while running).

## 2025-11-24 — Misc docs and TODO updates
- Updated `README.md`, `PLAN.md`, and `TODO.md` to reflect PoC progress, security notes, and next steps.
- Added `CHANGELOG.md` (this file) to track changes.

---

Notes and next steps
- Several immediate next items were recorded in `TODO.md`: spec-kit integration, testing-agent enhancements (JUnit/XML, report API, concurrency), manager auth and RBAC, monitoring agent, CI integration, and persistence/queueing improvements.
- Sensitive items: ensure `.env` is NOT committed; rotate any passwords and remove temporary keys from the host.

If you'd like, I can now:
- Push these commits to a remote repository you provide.
- Create a release tag (v0.2.0) and attach this changelog.
- Expand any changelog entries to include commit hashes or more precise timestamps per change.
