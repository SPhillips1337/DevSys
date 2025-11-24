# Software Developer-in-a-Box — PLAN

Executive summary
- Build a Docker Compose-based "developer in a box" platform where multiple containerized agents collaborate to deliver, test, deploy, and monitor software projects autonomously.
- Agents: Manager (orchestrator / task planner), Coding Agent (runs opencode), Testing Agent (runs tests/CI), Deployment Agent (builds/releases to the local dev stack), Monitoring Agent (logs/health + auto-repair).
- Use a shared persistent store (task database and file volume) and a standardized task-spec format (integrate GitHub spec-kit) for handoffs between agents.

Goals
- Create a reproducible dev environment that can accept a user story (e.g., "Develop and run a blog site"), break it into tasks, and run the full pipeline from coding → test → deploy → monitor.
- Provide traceability for tasks and automated handoffs between agents.
- Make the system extensible: swap or scale agents as needed.

High-level architecture
- `docker-compose.yml` (top-level) to define services:
  - `manager` — receives user stories, creates task specs, assigns tasks to agents.
  - `coding-agent` — runs `opencode` to generate or modify code per spec.
  - `testing-agent` — pulls code, runs unit/integration tests, reports results.
  - `deployment-agent` — builds and deploys the app into the `dev` environment (other compose services) or container registry.
  - `monitoring-agent` — collects logs/metrics, performs health checks, can create new tasks to request fixes.
  - `task-store` — a persistent store (Postgres or SQLite) + optional Redis for queues.
  - `file-share` — a named Docker volume or host-mounted directory shared by agents for source artifacts and artifacts (e.g., `./workspace`).

Task & handoff model
- Use a structured YAML/JSON task spec derived from `spec-kit` principles (task id, owner, priority, inputs, expected outputs, tests, constraints, artifacts path).
- Store the authoritative copy of the task spec in `task-store` and place any file artifacts in `file-share` under `tasks/<task-id>/`.
- Agents poll a queue or subscribe to events; manager marks status transitions: `created` → `assigned` → `in_progress` → `complete` → `verified` → `deployed`.

Spec-kit integration
- Use `spec-kit` (https://github.com/github/spec-kit) to formalize and validate task specs and acceptance criteria.
- Strategy:
  - Define a minimal task schema (YAML) compatible with spec-kit.
  - Store schema and example specs under `./specs` in the repo.
  - Manager uses spec-kit validators before creating tasks and when verifying deliverables.

Shared storage and persistence
- `file-share` (host directory `./workspace` mapped into agents at `/workspace`): holds code, artifacts, logs.
- `task-store` (Postgres preferred) with a simple `tasks` table, `events` table, and `artifacts` metadata.
- Optional Redis for message queueing (task assignment, notifications).

Agent responsibilities (concise)
- Manager: Accepts user stories, decomposes into tasks, validates using spec-kit, inserts tasks into `task-store` and queue.
- Coding Agent: Runs `opencode` (inside its container), writes output to `/workspace/tasks/<id>/src`, updates task status and attaches artifacts.
- Testing Agent: Runs configured tests (shell script or language-specific), writes test reports to artifacts and updates `task-store`.
- Deployment Agent: Builds application images or runs `docker compose` stacks to deploy to a `dev` namespace; updates task status to `deployed`.
- Monitoring Agent: Monitors endpoints / logs, can create new tasks for regressions or failures and escalate to the manager.

Security and access
- Agents communicate internally via the private Docker network.
- `file-share` should have permissions least-privilege for containers; sensitive secrets stored via Docker secrets or environment variables — never commit keys into the repository.
- Default SSH/passwords in the existing PHP image must be removed; use key-based auth only if needed for any remote access.

Phases & Milestones
- Phase 1 (Scaffold): Define schemas, `docker-compose.yml` scaffold, `workspace` layout, minimal manager + coding-agent skeletons, integrate spec-kit validators.
- Phase 2 (PoC): Implement coding agent running opencode to scaffold a blog project, testing agent runs simple tests, deployment agent deploys to local compose webserver, monitoring agent does basic health checks.
- Phase 3 (Hardening): Add persistent DB, job queue, retries, RBAC, secret management, and better monitoring (metrics + alerting).
- Phase 4 (Automation): Create CI/CD flows, automatic rollback strategies, and auto-repair policies implemented by monitoring agent.

Deliverables for initial PoC
- `docker-compose.yml` with the services above and a `workspace` volume.
- `specs/` directory with a minimal task schema and one sample task: "Create blog site".
- `manager` service: HTTP API or CLI to accept user story and create tasks.
- `coding-agent` image: based on existing `Dockerfile.php` style but with `opencode` installed and able to run job specs.
- `testing-agent` minimal runner: executes provided test script and reports results.
- `deployment-agent` minimal deployer: runs container build and launches app into Compose under `dev` network.
- `monitoring-agent` basic health checker and log scanner that can create tasks on failure.
- `PLAN.md` (this file) and a short `ARCHITECTURE.md` autogenerated from these notes.

Example minimal task spec (YAML)
- `specs/create-blog.yaml` (example):

```
id: task-001
title: Create blog website
owner: manager
priority: high
inputs:
  - type: template
    name: simple-static
outputs:
  - path: /workspace/tasks/task-001/src
acceptance:
  - url: http://devsite:8080
  - should_respond: 200
tests:
  - run: ./run-tests.sh
```

Implementation details & tech choices
- Task store: start with SQLite for PoC (`/workspace/task.db`) then migrate to Postgres for multi-host scaling.
- Queue: Redis streams or simple DB-based queue for PoC; prefer Redis later.
- File sharing: host-mounted `./workspace` for easy inspection by users.
- Agent code: lightweight Python or Node services wrapping `opencode` CLI and exposing a small REST control plane.
- Logging: write to `/workspace/logs/<service>.log` and expose a simple dashboard or `docker compose logs` for debugging.

Acceptance criteria for PoC
- Manager can accept a user story and create a validated task spec.
- Coding Agent can pick up the task, run opencode, and produce source in `/workspace/tasks/<id>/src`.
- Testing Agent can run tests and report pass/fail back to the task-store.
- Deployment Agent can launch the site into the compose environment and the Monitoring Agent can detect health OK.

Risks & open questions
- Running opencode autonomously may produce insecure or unreviewed code; require review or gated approvals for production.
- How much autonomy should the Monitoring Agent have for auto-repair? (auto-deploy vs create tasks)
- Spec-kit integration level: use only schema validation or full spec-kit toolchain?

Next steps I can take now (pick one)
- Scaffold `docker-compose.yml` and `workspace` layout and small manager + coding-agent skeleton services.
- Create the `specs` schema and `specs/create-blog.yaml` example and wire spec-kit validation.
- Implement the minimal `coding-agent` container that runs `opencode` and writes artifacts to `/workspace`.

If you approve, I'll begin by scaffolding the PoC (`docker-compose.yml`, `workspace` volume, `specs/` files, manager and coding-agent skeleton). The first step is already marked in the todo list as `in_progress`.

References
- spec-kit: https://github.com/github/spec-kit

File: `PLAN.md` — saved at repository root.
