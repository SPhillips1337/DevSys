#!/usr/bin/env bash
set -e

# Ensure shared workspace exists and is writable by web user
if [ ! -d "/workspace" ]; then
  mkdir -p /workspace || true
fi
# Attempt to chown workspace to www-data so PHP can write; ignore failures
chown -R www-data:www-data /workspace || true

# If a deployed current app exists, copy it into /var/www/html
if [ -d "/var/www/deploy/current" ]; then
  echo "Found deployed app at /var/www/deploy/current. Copying into /var/www/html."
  rm -rf /var/www/html
  mkdir -p /var/www/html
  cp -r /var/www/deploy/current/. /var/www/html/
  chown -R www-data:www-data /var/www/html || true
elif [ -d "/var/www/www" ]; then
  echo "No deployed app found. Using fallback /var/www/www."
  rm -rf /var/www/html
  mkdir -p /var/www/html
  cp -r /var/www/www/. /var/www/html/
  chown -R www-data:www-data /var/www/html || true
else
  echo "No deployed app or fallback content found. Creating default index."
  mkdir -p /var/www/html
  echo "<html><body><h1>Devsys PHP Container</h1></body></html>" > /var/www/html/index.html
  chown -R www-data:www-data /var/www/html || true
fi

# Set runtime user password or SSH keys if provided via environment
if [ -n "${N8N_USER_PASSWORD:-}" ]; then
  echo "Setting password for n8nuser from N8N_USER_PASSWORD"
  echo "n8nuser:${N8N_USER_PASSWORD}" | chpasswd || true
fi

if [ -n "${N8N_USER_PUBKEY:-}" ]; then
  echo "Adding provided public key to /home/n8nuser/.ssh/authorized_keys"
  mkdir -p /home/n8nuser/.ssh
  echo "${N8N_USER_PUBKEY}" >> /home/n8nuser/.ssh/authorized_keys
  chown -R n8nuser:n8nuser /home/n8nuser/.ssh || true
  chmod 700 /home/n8nuser/.ssh || true
  chmod 600 /home/n8nuser/.ssh/authorized_keys || true
fi

# Optionally disable password auth if N8N_PASSWORD_AUTH is set to 'false'
if [ "${N8N_PASSWORD_AUTH:-true}" = "false" ]; then
  sed -i 's/^#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config || true
  sed -i 's/^PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config || true
fi

# Start both Apache and SSH
if [ -x "/start-services.sh" ]; then
  exec /start-services.sh
else
  # Fallback: start sshd and apache
  /usr/sbin/sshd
  apache2-foreground
fi
