# opencode in PHP Docker Container (devsys copy)

This directory contains a minimal copy of the files required to run the PHP + SSH container and the opencode setup extracted from your `n8n` project. The goal is to move this out of the `n8n` project so it can be managed separately.

Included files
- `docker-compose.yml` — the Compose configuration for the PHP container (and n8n entry for reference).
- `Dockerfile.php` — Dockerfile used to build the PHP + ssh image.
- `README.md` — this file (copied from the project).

Note: the original `README.md` contains opencode setup and instructions. This copy is intended to be the starting point to run the PHP+SSH container separately.

How to use
1. Move into this directory on the host where your Docker environment runs:
   - `cd /home/stephen/devsys`
2. Adjust configuration as needed (ports, volumes). The current `docker-compose.yml` references `./n8n_data` for volumes — you may want to change that to a location under `devsys` or adjust mounts.
3. Build and start the services:
   - `docker compose up -d --build`
4. The PHP container exposes SSH on host port `2222` and HTTP on the host IP `192.168.5.215:80` as configured in the Compose file.

Security and migration notes
- The `Dockerfile.php` in this directory contains a hardcoded user `n8nuser` with password `n8npass`. Update credentials or switch to key-based SSH before exposing to broader networks.
- The opencode artifacts and configuration are not included here; the intent is to let you separate the container setup. If you want the opencode install and Supervisor config incorporated into this Docker image (so it starts opencode on container start), I can create a new Dockerfile and Compose service for `opencode` and include Supervisor configuration.

Next steps I can perform (optional)
- Update `docker-compose.yml` to run opencode as a separate service.
- Create a dedicated `Dockerfile` that installs `opencode` and Supervisor so the container starts `opencode` automatically.
- Move any required application data from `/home/stephen/n8n/n8n_data/php` into `devsys` with sanitized content.

If you want me to proceed with any of the next steps, tell me which and I will implement it here in `/home/stephen/devsys`.
