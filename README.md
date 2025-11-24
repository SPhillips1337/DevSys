# DevSys — Developer-in-a-Box PoC

This repository contains a small Proof-of-Concept for a "developer-in-a-box" workflow where containerized agents collaborate to implement, test, deploy and monitor small projects.

Key components
- `manager` — HTTP API to accept user stories and create task specs.
- `coding-agent` — runs opencode-like scaffolding to produce code/artifacts for tasks.
- `deployment-agent` — deploys task artifacts into the local PHP container and verifies acceptance criteria.
- `php` — a PHP/Apache container repurposed as a local deployment target (serves files from `/var/www/www`).
- `workspace` — shared folder mounted into agents where tasks, artifacts, and deploys live.

Quick start
1. Copy `.env.example` to `.env` and set secure values (do NOT commit `.env`).
   - `cp .env.example .env` and edit values.
2. Build and start the stack:
   - `docker compose up -d --build`
3. Create a task via the manager API (example):
   - `curl -X POST http://localhost:8080/api/tasks -H 'Content-Type: application/json' -d '{"id":"task-001","title":"Create blog","owner":"manager","kind":"deployment","deploy":true}'`
4. Optionally trigger deploy explicitly:
   - `curl -X POST http://localhost:8080/api/tasks/task-001/deploy`
5. The deployed site will be served at `http://localhost:8081`.

Developer notes
- The manager exposes endpoints to create tasks, update status, trigger deploys, list deploy history, and rollback.
- Task specs live under `./workspace/tasks/<task-id>/spec.yaml`. Artifacts are placed in `./workspace/tasks/<task-id>/src` by the coding-agent.
- Deployments are stored under `./workspace/deploy/<task-id>/current` and copied into `./workspace/www/` for serving by the PHP container.
- The PHP container’s SSH user password is configured at runtime via `.env` (see `.env.example`) or by adding a public key.

Security
- Do not commit `.env` — it is ignored by git. For production use replace `.env` with a secret manager or Docker secrets.
- The stack is intended for local development / PoC only — do not expose services publicly without hardening.

License
This project is licensed under the MIT License — see `LICENSE` for details.

Next steps
- Integrate `spec-kit` for richer validation of task specs.
- Add `testing-agent` and `monitoring-agent` to complete the pipeline.
- Harden manager API with authentication and RBAC before exposing beyond localhost.

If you want me to continue, tell me which next step to implement (e.g., add testing-agent skeleton, integrate spec-kit, or add manager auth).