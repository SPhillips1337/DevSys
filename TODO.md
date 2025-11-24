# DevSys Next Steps / TODO

These are recommended actions for the DevSys PoC and future hardening. Items marked with (POC) indicate work already implemented in this repository.

1. Rebuild & validate
   - `docker compose up -d --build` and run end-to-end tests regularly. (POC)
   - Add CI job to run the PoC stack and run integration tests.
   - Add an integration test that exercises the full flow: manager → coding-agent → testing-agent → deployment-agent → monitoring-agent.

2. Security & access
   - Add authentication/authorization to the manager API (deploy/rollback endpoints) and protect agent endpoints (token-based or mutual TLS). (POC implemented: token-based auth)
   - Remove hardcoded SSH passwords from `Dockerfile.php` and migrate to key-only auth or Docker secrets. (TODO)
   - Store secrets in Docker secrets / environment management and avoid committing keys to the repo.
   - Add audit logging for manager actions (who triggered deploy/rollback).

3. Spec & validation
   - Integrate `spec-kit` fully to validate task specs and acceptance criteria (schema & acceptance tests).
   - Expand task schema to include: `kind`, `resource_requirements`, `tags`, `related_tasks`, `expected_artifacts`, and `retry_policy`.
   - Provide CLI/manager tooling to generate validated task specs from user stories.

4. Persistence, queueing & reliability
   - Replace file-based task store with Postgres (or SQLite for smaller installs) and add Redis for durable queues and pub/sub.
   - Add retries, backoff, and dead-letter handling for failed jobs.
   - Ensure agents checkpoint progress and support idempotent re-runs.

5. Agents & workflows
    - testing-agent: implement a runner that executes provided tests, writes reports to `/workspace/tasks/<id>/reports`, and updates task status. (POC implemented: basic testing-agent)
    - monitoring-agent: collect logs/metrics, run periodic health checks, and create follow-up tasks for regressions (POC scaffold implemented). Enhance with concurrent checks, richer check types, and notification hooks.
    - notification service: integrate Slack/email/webhooks for important events (failed deploys, rollbacks, critical alerts). (Add retry and rate-limiting to avoid spam.)
    - Implement role-based assignment and agent selection (e.g., label agents by capabilities).

    Monitoring enhancements (short-term)
    - Support additional check types: TCP, script, log pattern, and synthetic transactions.
    - Add webhook/Slack notifier and basic retry/backoff for notifications.
    - Add per-check concurrency and scheduling (avoid serial blocking checks).
    - Add a monitoring `README` describing `monitoring/checks.yaml` format and examples.



6. Deployment improvements
   - Multi-app hosting: keep `deploy/<task-id>/current` and support `deploy/<task-id>/revisions/*` (POC implemented).
   - Manager endpoints for deploy/rollback exist (POC) — add RBAC and safe-guards (approval workflows).
   - Improve zero-downtime/atomic deploys and add optional in-container watcher or manager-triggered sync to update served content without container restart.
   - Add fixture support for staging URLs and container-accessible acceptance checks (use service hostnames, not `localhost`).

7. Acceptance, verification & auto-repair
   - Acceptance checks: extend beyond simple HTTP GET to run scripted acceptance suites and smoke tests.
   - Auto-repair policies: allow monitoring agent to either create follow-up tasks or (carefully) attempt automated fixes with human approval gating.
   - Record per-deployment verification metadata (HTTP response, logs snippet, screenshots if applicable).

8. Observability & metrics
   - Export metrics for agent performance, deployment success rate, and task throughput (Prometheus + Grafana suggested).
   - Centralize logs and add searchable logs (ELK/Vector/Loki) for easier root-cause analysis.

9. Testing & automation
   - Add unit and integration tests for manager APIs and agent behaviors.
   - Add end-to-end smoke tests to the CI pipeline that deploy a sample app and verify acceptance.
   - Add chaos tests for agent failures and network partitions.
   - Add JUnit/XML test report output for the testing-agent so CI systems can parse results.
   - Add a manager API endpoint to fetch the latest test report or a test summary for a task.
   - Implement a basic test queue and parallel test runners for the testing-agent to allow concurrent execution and throttling.

10. Documentation & runbook
   - Document agent APIs, task spec format (`specs/`), and operational runbook for running and troubleshooting the PoC. (TODO)
   - Create onboarding docs and example workflows for product managers (how to write a user story → task spec).

11. Production readiness
   - Review security posture (network exposure, secrets, image hardening) before any non-local deployment.
   - Add backup/restore for task store and deploy artifacts.
   - Plan scaling: container orchestration (Kubernetes), multi-host work queues, and agent autoscaling.

12. Short-term immediate tasks (next sprint)
   - Integrate `spec-kit` schema validation into the manager (partial work done; finish integration).
   - Implement `testing-agent` skeleton and wire it into the pipeline. (POC done; extend with JUnit/XML and parallelism)
   - Add manager API authentication and RBAC for deploy/rollback. (POC: token auth implemented)
   - Add notifications for failed deploys and created follow-up tasks.
   - Add CI job to build images and run the PoC integration test.
   - Implement JUnit/XML reporting in testing-agent and expose manager API to fetch latest test report.
   - Implement basic test queue and parallel test runners for the testing-agent.
   - Monitoring: finalize monitoring-agent features (POC scaffold added) — add webhook notifier, richer check types, non-blocking scheduling, and monitoring README.
   - Start monitoring-agent and perform an initial run to validate checks and follow-up task creation behavior. (next immediate action)

(End of TODO list)
▼
Todo
[✓] Define architecture & roles
[✓] Design task-handoff format
[✓] Create agent docker-compose
[ ] Implement shared storage & queue
[ ] Integrate spec-kit for specs
[ ] Build coding agent image (opencode)
[ ] Build testing agent & CI scripts
[✓] Build deployment agent & pipeline
[ ] Build monitoring & auto-repair agent
[✓] Create sample blog project
[ ] Run integration tests & validate
[ ] Document workflows & handoffs