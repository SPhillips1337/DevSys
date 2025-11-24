FROM php:8.2-apache

# Install OpenSSH server
RUN apt-get update && \
    apt-get install -y openssh-server && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Configure SSH
RUN mkdir -p /var/run/sshd && \
    sed -i 's/^#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    sed -i 's/^PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config

# Create SSH user (password will be set at runtime from environment variables)
RUN useradd -m -s /bin/bash n8nuser || true

# Expose SSH port
EXPOSE 22

# Copy start script, entrypoint and apache site configuration
COPY start-services.sh /start-services.sh
COPY entrypoint.sh /entrypoint.sh
COPY apache-site.conf /etc/apache2/sites-available/000-default.conf
RUN chmod +x /start-services.sh /entrypoint.sh

# Use entrypoint to prepare deployed content then start services
CMD ["/entrypoint.sh"]
