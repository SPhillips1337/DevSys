# DevSys scripts — usage

This folder contains helper scripts for provisioning and preparing remote hosts and local secrets used by the DevSys PoC.

Files

- `setup-remote.sh` — (run on the remote host as root or via sudo) installs Docker, rsync, and SSH, creates `/tmp/devsys` directories, and optionally creates a `devsys` user in the `docker` group. Use this to prepare a remote test/deploy host such as `192.168.5.69`.

- `generate-known-hosts.sh` — (run locally) generates a `known_hosts` file for the remote host using `ssh-keyscan`. Example:

  ```bash
  mkdir -p ./secrets && chmod 700 ./secrets
  ./scripts/generate-known-hosts.sh 192.168.5.69 22 ./secrets/remote_known_hosts
  ```

Usage notes

- Do NOT commit private keys or the `./secrets` folder into source control. The repository `.gitignore` is configured to ignore `./secrets/`.

- Typical workflow:
  1. Generate a `known_hosts` file locally (see example above).
  2. Copy or place your SSH private key into `./secrets` (e.g. `./secrets/remote_test_key`) and ensure permissions are `600`.
  3. Use `docker-compose.override.yml` (provided) to mount the secrets into the agent containers for local development.
  4. Update `.env` to point at the secret paths inside containers (e.g. `REMOTE_TEST_SSH_KEY=/run/secrets/remote_test_key`).

Security

- Prefer Docker secrets or a secrets manager for production deployments. These scripts are intended for initial provisioning and local convenience.
- The `setup-remote.sh` script must be run as `root` or via `sudo` on the remote host.

Support

If you want, I can:
- Add a wrapper script that uploads `setup-remote.sh` and runs it on the remote host from your workstation, prompting for your password (one-liner SSH execution),
- Add checks to `generate-known-hosts.sh` to validate the resulting `known_hosts` file contains a key, or
- Add a script to create Docker secrets from local files and demonstrate `docker secret` usage.

