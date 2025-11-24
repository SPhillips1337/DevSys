#!/usr/bin/env bash
set -e

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

# Start both Apache and SSH
if [ -x "/start-services.sh" ]; then
  exec /start-services.sh
else
  # Fallback: start sshd and apache
  /usr/sbin/sshd
  apache2-foreground
fi
