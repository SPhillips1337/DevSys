#!/usr/bin/env bash
set -euo pipefail

# setup-remote.sh
# Minimal remote host provisioning script for DevSys remote-ssh runner (Debian/Ubuntu)
# Run as root (sudo) on the remote host: sudo bash setup-remote.sh

if [ "$(id -u)" -ne 0 ]; then
  echo "Please run this script as root or via sudo: sudo bash setup-remote.sh"
  exit 1
fi

echo "=== DevSys remote host setup: starting ==="

# Install common prerequisites and Docker (Debian/Ubuntu flow)
apt-get update
apt-get install -y ca-certificates curl gnupg lsb-release software-properties-common || true

mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg || true
DIST_ID="$(. /etc/os-release && echo "$ID")"
CODENAME="$(lsb_release -cs 2>/dev/null || echo focal)"
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${DIST_ID} ${CODENAME} stable" \
  | tee /etc/apt/sources.list.d/docker.list > /dev/null || true

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin rsync openssh-server openssh-client || true

echo "Enabling and starting Docker service..."
systemctl enable --now docker || true

# Create runtime dirs
mkdir -p /tmp/devsys/deploy
mkdir -p /tmp/devsys/tests
chmod 755 /tmp/devsys
chown root:root /tmp/devsys || true

# Create optional `devsys` user and add to docker group
if ! id -u devsys >/dev/null 2>&1; then
  echo "Creating 'devsys' user and adding to docker group..."
  useradd -m -s /bin/bash devsys || true
  usermod -aG docker devsys || true
  echo "Created user 'devsys'. Set password (if desired) with: sudo passwd devsys"
else
  echo "User 'devsys' already exists; ensuring it is in the docker group..."
  usermod -aG docker devsys || true
fi

# Ensure SSH is running
systemctl enable --now ssh || systemctl enable --now sshd || true

cat <<'EOF'

Setup complete.

Next steps (on your workstation):
 - Add public key to remote host: ssh-copy-id -i ~/.ssh/id_rsa.pub stephen@<REMOTE_HOST>
 - Generate known_hosts file locally: ssh-keyscan -p <PORT> <REMOTE_HOST> > ./secrets/remote_known_hosts
 - Copy or mount private keys into your repo's ./secrets and point .env entries to /run/secrets/* inside containers.

To run this script remotely from your workstation (you will be prompted for your password):
 - scp setup-remote.sh stephen@<REMOTE_HOST>:~
 - ssh stephen@<REMOTE_HOST> 'sudo bash ~/setup-remote.sh'

EOF

exit 0
