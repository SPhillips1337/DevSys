# Changelog

All notable changes to this project are documented in this file.

Dates are in UTC. This file summarizes the work performed during the DevSys PoC development.

## 2025-11-24 — Initial PoC and scaffolding
- Created repository scaffold for the DevSys PoC: `docker-compose.yml`, `Dockerfile.php`, `README.md`, `PLAN.md`, `TODO.md`.
- Added `project.json` manifest describing goals, features, and how to run locally.

## 2025-11-24 — Manager and coding agent
- Added `manager` service (Flask HTTP API) to accept user stories and create task specs.
- Added `coding-agent` service to pick up `created` tasks and scaffold a simple static site into `workspace/tasks/<id>/src`.

## 2025-11-24 — Deployment flow and PHP deployment target
- Repurposed PHP container to act as a local deployment target and added `deployment-agent` to deploy artifacts, archive revisions, and run acceptance checks.
- Added manager endpoints for deploy and rollback.

## 2025-11-24 — Workspace layout and security improvements
- Introduced `workspace` (shared artifacts), `.env.example` for runtime secrets, and removed hardcoded SSH password from Dockerfile.
- Initialized git repository and committed project scaffolding.

## 2025-11-24 — Manager token-based authentication
- Implemented optional token-based auth for the manager API (`MANAGER_API_TOKEN`).
- Agents updated to send `Authorization: Bearer <token>` when present.

## 2025-11-24 — Testing agent and pipeline
- Added `testing-agent` to run tests, produce text reports and JUnit/XML reports, and record test history.
- Added manager endpoint to fetch latest test report: `GET /api/tasks/<id>/tests/latest`.

## 2025-11-24 — Monitoring agent
- Added `monitoring-agent` scaffold that reads `monitoring/checks.yaml`, performs HTTP checks, tracks failures, and creates follow-up coding tasks when thresholds are exceeded.
- Monitoring is configured via `monitoring/checks.yaml` and persists state to `workspace/monitoring_state.json`.
- Demonstrated monitor-created follow-up tasks during testing; follow-ups were cleaned up on request.

---

Notes and next steps
- Current PoC status: core agents implemented (manager, coding, testing, deployment, monitoring). Remaining work: spec-kit integration, notification hooks (Slack/webhook/email), RBAC and per-agent tokens, persistent DB + queues, CI integration.
- See `TODO.md` for a prioritized list of tasks.

