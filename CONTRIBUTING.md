# Contributing to DevSys PoC

Thank you for your interest in contributing to this project. This file describes the basic workflow and expectations for contributions.

Getting started
- Fork the repository (if pushing to a remote) or work on a feature branch locally.
- Run the stack locally to reproduce behavior:
  - Copy `.env.example` to `.env` and update secrets (do NOT commit `.env`).
  - `docker compose up -d --build`

Branching & commits
- Create a feature branch for your work: `git checkout -b feat/your-feature`.
- Keep commits small and focused; write clear commit messages.
- Follow conventional commits where practical (e.g., `feat:`, `fix:`, `chore:`).

Code style & tests
- Use Python 3.11 for agent scripts. Keep code readable and add comments where helpful.
- If you add functionality, include tests where it makes sense and add a simple test runner under `workspace/tasks/<id>/run-tests.sh` for the testing-agent to pick up.

Developer workflow
- Update `TODO.md`, `PLAN.md`, or `CHANGELOG.md` as appropriate when adding features.
- Run `docker compose up -d --build` to test services after changes.
- When ready, create a PR with a clear description; include relevant changes to the plan or TODOs.

Security & secrets
- Never commit secrets or private keys to the repository. Use `.env` locally or Docker secrets for deployments.
- Validate any third-party installers or downloads before adding them to the Dockerfiles.

Communication
- Use issue tracker or PR descriptions to explain rationale, design choices, and migration steps.

Thanks — maintainers
- stephen
