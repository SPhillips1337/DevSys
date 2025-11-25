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
- Add notification integrations (Slack/webhook/email) and RBAC for manager endpoints.
- Migrate to a persistent task store (Postgres) with Redis for queues as we scale up.

Notes on current status (PoC)
- Implemented services: `manager`, `coding-agent`, `testing-agent` (JUnit/XML reports), `deployment-agent`, `monitoring-agent`.
- Manager supports optional token-based auth via `MANAGER_API_TOKEN` and exposes a test report endpoint: `GET /api/tasks/<id>/tests/latest`.

If you want me to continue, tell me which next step to implement (e.g., integrate spec-kit, add notification hooks, or migrate the task store).

## Project manifest support & tests

- The manager now accepts project manifests conforming to `specs/project.schema.json`. A sample manifest is provided at `specs/create-blog.json`.
- To run the included test that posts the sample manifest and asserts a task is created:
  - Install manager dependencies: `python -m pip install -r manager/requirements.txt`
  - Install the test runner: `python -m pip install pytest`
  - Run the test: `pytest tests/test_create_blog.py -q`
- The test uses Flask's test client and creates a temporary `WORKSPACE`, so you do not need the manager server running to run the test.
- When a project manifest is accepted the manager will convert it into a task spec and persist it under `./workspace/tasks/<task-id>/` with `spec.yaml` (which embeds the original manifest) and `meta.json`.
- To manually POST a manifest to a running manager (if the server is up):
  - `curl -X POST http://localhost:8080/api/tasks -H 'Content-Type: application/json' -d @specs/create-blog.json`
  - If `MANAGER_API_TOKEN` is enabled, include it via `-H 'Authorization: Bearer <token>'` or `-H 'X-Api-Token: <token>'`.

If you'd like, I can add a CI workflow to run this test automatically on push/PR.

## Remote runner & SSH secrets

The agents support a `remote-ssh` runner mode so you can run tests and deploy to an external host (for example `192.168.5.69`). This is configured via environment variables in your `.env` (see `.env.example`). Key points:

- Runner selection: `DEPLOY_RUNNER` and `TEST_RUNNER` control behavior. `auto` will prefer a configured remote host, fallback to host-docker if the Docker socket exists, otherwise `local`.
- SSH keys: For secure usage mount private keys into the container via Docker secrets or bind-mount a file and point the env var to the path (e.g., `REMOTE_TEST_SSH_KEY=/run/secrets/remote_test_key`).
  - Example (local bind mount): create `secrets/remote_test_key` with your private key, `chmod 600 secrets/remote_test_key`, and add a service volume like `- ./secrets/remote_test_key:/run/secrets/remote_test_key:ro` in your `docker-compose.yml` for the agent service.
- Known hosts enforcement: the remote SSH runner requires a `REMOTE_*_KNOWN_HOSTS` or `EXTERNAL_DEPLOY_KNOWN_HOSTS` path to a `known_hosts` file by default. This avoids using `StrictHostKeyChecking=no` and protects against MITM attacks. If you need to bypass this for PoC only, set `REMOTE_ALLOW_INSECURE_SSH=true` in `.env` (not recommended).
- The testing and deployment agent images now include `openssh-client` and `rsync` so they can transfer files and execute remote commands.
- Security: do not commit private keys. Use Docker secrets or a secrets manager in production and restrict access to the secret files.

Example usage (manual):

- Add the private key to a local file and point at it in `.env`:
  - `REMOTE_TEST_SSH_KEY=/run/secrets/remote_test_key`
  - `REMOTE_TEST_KNOWN_HOSTS=/run/secrets/remote_known_hosts`
- Ensure the remote host has the corresponding public key in `~/.ssh/authorized_keys` for the SSH user and that `ssh-keyscan` output has been stored into your `known_hosts` file.
- To run `docker compose` on the remote deploy host after copying artifacts, set `EXTERNAL_DEPLOY_RUN_COMPOSE=true` in `.env`. The deployment agent will run `docker compose up -d --build` in the remote deploy path after transferring files.
- Start the stack and the testing/deployment agents will prefer `remote-ssh` when `REMOTE_TEST_HOST`/`EXTERNAL_DEPLOY_HOST` and corresponding user/known_hosts values are present.

If you want, I will now:
- Add the runner helper code (done).
- Implement `remote-ssh` behavior in agents (done for basic copy+remote-run in testing and copy for deployment).
- Update `docker-compose.yml` examples to show how to mount secrets into the agent services (I can add this next).

## Provisioning a remote test/deploy host — example shell commands

Below are example commands you can run locally to provision files used by the agents (private key + known_hosts), mount them into the agent containers, and configure `.env`. Adapt paths, user and host as needed.

1) Create a local secrets folder (not checked into git) and set permissions:

   - `mkdir -p ./secrets`
   - `chmod 700 ./secrets`

2) Copy or place your SSH private key into the secrets folder (do NOT commit this file):

   - `cp ~/.ssh/id_rsa ./secrets/remote_test_key`
   - `chmod 600 ./secrets/remote_test_key`

   If you keep a separate key for the agent, use that instead of `~/.ssh/id_rsa`.

3) Create a `known_hosts` file for the remote host (recommended):

   - `ssh-keyscan -p 22 192.168.5.69 > ./secrets/remote_known_hosts`
   - `chmod 644 ./secrets/remote_known_hosts`

   If the remote SSH server uses a non-default port, pass `-p <PORT>` to `ssh-keyscan`.

4) (Optional) Install the public key on the remote host for the agent user (if you have network access):

   - `ssh-copy-id -i ~/.ssh/id_rsa.pub devsys@192.168.5.69`

   Alternatively manually append the public key to `~/.ssh/authorized_keys` on the remote host.

5) Mount the secrets into your agent services in `docker-compose.yml` (example snippet):

```yaml
services:
  testing-agent:
    volumes:
      - ./workspace:/workspace
      - ./secrets/remote_test_key:/run/secrets/remote_test_key:ro
      - ./secrets/remote_known_hosts:/run/secrets/remote_known_hosts:ro
    env_file:
      - .env

  deployment-agent:
    volumes:
      - ./workspace:/workspace
      - ./secrets/external_deploy_key:/run/secrets/external_deploy_key:ro
      - ./secrets/external_deploy_known_hosts:/run/secrets/external_deploy_known_hosts:ro
    env_file:
      - .env
```

6) Set the relevant variables in your `.env` (copy from `.env.example`):

   - `REMOTE_TEST_HOST=192.168.5.69`
   - `REMOTE_TEST_USER=devsys`
   - `REMOTE_TEST_SSH_KEY=/run/secrets/remote_test_key`
   - `REMOTE_TEST_KNOWN_HOSTS=/run/secrets/remote_known_hosts`
   - `TEST_RUNNER=auto`

   For remote deploy + compose runs:

   - `EXTERNAL_DEPLOY_HOST=192.168.5.69`
   - `EXTERNAL_DEPLOY_USER=devsys`
   - `EXTERNAL_DEPLOY_SSH_KEY=/run/secrets/external_deploy_key`
   - `EXTERNAL_DEPLOY_KNOWN_HOSTS=/run/secrets/external_deploy_known_hosts`
   - `EXTERNAL_DEPLOY_RUN_COMPOSE=true`

7) Start the stack and run a sample task:

   - `docker compose up -d --build`
   - Create a task (example): `curl -X POST http://localhost:8080/api/tasks -H 'Content-Type: application/json' -d @specs/create-blog.json`

Notes

- The agents require the key files and known_hosts paths supplied via the `.env` entries shown above. For production use replace bind mounts with Docker secrets or a secrets manager.
- By default the remote runner enforces known_hosts. Only set `REMOTE_ALLOW_INSECURE_SSH=true` to bypass that behavior for short-lived PoC testing (not recommended).

