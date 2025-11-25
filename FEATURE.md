FEATURE: Self-Improving DevSys Agents
Date: 2025-11-25

Summary
- Capture ideas for allowing DevSys agents to pull their own source code from GitHub, iterate on the codebase (branch-per-task + PRs), and integrate spec-kit for validated task specs.
- Record deployment/test execution options (host Docker socket, remote runners, DinD) and security trade-offs.
- Provide a short implementation roadmap and actionable next tasks to revisit.

Goals
- Enable agents to fetch repositories and produce changes as task artifacts.
- Prefer safe, auditable flows: branch-per-task + automated PR creation + human review before merging.
- Integrate `spec-kit` (schema + validators) into the manager validation and agent verification steps.
- Provide a secure, reproducible way for agents to run integration tests and deploy artifacts without exposing the host unnecessarily.

Key Concepts
1. Repo Pull & Workflows
   - Agents (primarily `coding-agent`) should be able to `git clone` or `git fetch` a repo specified in a task spec.
   - Use a `branch-per-task` pattern: agents create and work on a dedicated branch `task/<task-id>` to capture changes.
   - Agents commit changes and push to remote; instead of directly pushing to `main`, agents open a Pull Request (PR) for review.
   - Manager can optionally add metadata to the PR (task-id, acceptance tests link, checklist).

2. PR-Based Self-Improvement
   - Self-modification should be gated: any change to agent code, manager logic, or infra files must create a PR for human review.
   - Tests (unit + integration) must pass on the PR branch before a merge; CI should enforce required checks.
   - For low-risk changes (docs, non-runtime config), manager could auto-merge if configured and checks pass.

3. Spec-Kit Integration
   - Integrate `spec-kit` validators in the manager to validate task specs at creation-time and in post-delivery verification.
   - Store canonical task schema under `./specs/` and add sample specs (e.g., `specs/create-blog.yaml`).
   - Agents should annotate artifacts with spec verification results.

4. Deployment + Test Execution Options
   - Host Docker access: mount `/var/run/docker.sock` into `deployment-agent` (fast, insecure). Enables running `docker build` and `docker compose` from inside container.
   - Remote executor: `deployment-agent` SSHs into a dedicated test host (recommended for security). Host runs compose/build/test commands (remote-ssh runner implemented).
   - Docker-in-Docker (DinD): run a DinD service/container where agents can build/run sibling containers without host socket; more complex and often unnecessary for PoC.
   - Lightweight in-container test runner: if full container orchestration isn’t needed, testing-agent can run language-level tests inside the agent container.

5. Security & Secrets
   - Never store long-lived high-privilege tokens in repo. Use scoped GitHub tokens, short-lived credentials, or a secrets manager.
   - If mounting Docker socket: restrict networking and treat that container as privileged — isolate it and audit access.
   - Use key-only SSH access for remote executors and rotate keys regularly.
   - Agents should default to creating PRs rather than pushing to protected branches.

6. Observability & Auditability
   - Record per-task artifacts: git commit SHA, branch, PR URL, test reports (JUnit/XML), and acceptance check outputs in `/workspace/tasks/<id>/reports`.
   - Manager API should expose latest test report: `GET /api/tasks/<id>/tests/latest` (already present in PoC).

Implementation Roadmap (short-term)
- [x] Add `repo` fields to task spec schema to reference GitHub repo/branch/PR (schema expanded in `specs/` where applicable).
- [x] Update `coding-agent/worker.py` to support basic clone/checkout flows (skeleton work present; full PR flow remains to implement).
- [x] Add `spec-kit` schema under `./specs/` and wire manager validation in `manager/app.py` (JSON Schema validation integrated; full spec-kit toolchain remains a next step).
- [x] Implement PR creation flow that adds task metadata and links to test reports (partial — coding-agent skeleton added; full GitHub API flow pending).
- [x] Add `deployment-agent` mode: `host-docker` (socket) and `remote-ssh`; make remote-ssh the default in prod configs (remote-ssh implemented; remote compose support added).
- [x] Add CI job to run integration pipeline on PRs and enforce passing checks before merge (basic CI for tests added in `.github/workflows/ci.yml`).
- [x] Update `README.md`, `PLAN.md`, and `TODO.md` with new workflows and security notes (done).

Acceptance Criteria (PoC)
- Manager accepts a task with `repo` field and validates with `spec-kit` (basic JSON schema validation integrated; full spec-kit usage TBD).
- `coding-agent` clones the repo, creates `task/<id>` branch, runs `opencode`, and opens a PR containing artifact changes (PR flow skeleton exists; GitHub token support via `GITHUB_TOKEN` env).
- Testing-agent runs unit tests and uploads JUnit/XML results to `/workspace/tasks/<id>/reports` (implemented; supports remote-ssh execution and report collection).
- Deployment-agent can perform a deploy on a remote test host and record an acceptance report (implemented with `EXTERNAL_DEPLOY_RUN_COMPOSE` option to run `docker compose` remotely).

Risks & Mitigations
- Risk: Agent compromise leading to host takeover if Docker socket is mounted.
  Mitigation: prefer `remote-ssh` runner or isolate the deployment agent tightly and audit access.
- Risk: Unreviewed self-modifying code gets merged.
  Mitigation: enforce branch protections and CI checks; require human approval for critical paths.

Short actionable tasks (next sprint)
1. Wire `spec-kit` toolchain into manager validation (high priority).
2. Implement `coding-agent` Git+PR flow (branch-per-task) with push+PR only, not direct merges — use `GITHUB_TOKEN` for API calls.
3. Add CI integration to run tests on PR branches and block merges until passing (extend `.github/workflows`).
4. Harden secrets management: migrate to Docker secrets or external secret manager and add audit logging.

References
- `README.md`, `PLAN.md`, `TODO.md`, `project.json`
- Spec-kit: https://github.com/github/spec-kit

Notes
- This document is a living doc: revisit it after the first iteration and update the roadmap and acceptance criteria.
- Consider moving these items into `project.json.todo` and `TODO.md` once prioritized.

---
Created-by: DevSys Assistant
