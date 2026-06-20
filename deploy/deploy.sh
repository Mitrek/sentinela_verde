#!/bin/bash
set -e

echo "→ Creating system user 'sentinela'"
if ! id "sentinela" &>/dev/null; then
    useradd -r -s /usr/sbin/nologin sentinela
fi

echo "→ Installing system dependencies (python3, nginx, rsync)"
apt-get update
apt-get install -y python3 python3-venv nginx rsync

echo "→ Stopping legacy fire_catcher service (if present)"
if systemctl is-active --quiet fire_catcher 2>/dev/null; then
    systemctl stop fire_catcher
    systemctl disable fire_catcher
fi

echo "→ Setting up /opt/sentinela_verde directory"
mkdir -p /opt/sentinela_verde
chown sentinela:sentinela /opt/sentinela_verde

echo "→ Copying project files to /opt/sentinela_verde"
rsync -av --exclude '.venv' --exclude 'venv' --exclude '.git' ./ /opt/sentinela_verde/
chown -R sentinela:sentinela /opt/sentinela_verde

echo "→ Creating virtualenv and installing requirements"
sudo -u sentinela python3 -m venv /opt/sentinela_verde/venv
sudo -u sentinela /opt/sentinela_verde/venv/bin/pip install --upgrade pip
sudo -u sentinela /opt/sentinela_verde/venv/bin/pip install -r /opt/sentinela_verde/requirements.txt

echo "→ Creating static asset directory"
sudo -u sentinela mkdir -p /opt/sentinela_verde/sentinela_verde/web/static

echo "→ Copying .env file"
if [ -f ".env" ]; then
    cp .env /opt/sentinela_verde/.env
    chown sentinela:sentinela /opt/sentinela_verde/.env
else
    echo "Warning: .env file not found in current directory. Please create /opt/sentinela_verde/.env manually."
fi

echo "→ Installing systemd service"
cp deploy/sentinela_verde.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now sentinela_verde

echo "→ Configuring Nginx"
cp deploy/nginx.conf /etc/nginx/sites-available/sentinela_verde
ln -sf /etc/nginx/sites-available/sentinela_verde /etc/nginx/sites-enabled/sentinela_verde
rm -f /etc/nginx/sites-enabled/default
rm -f /etc/nginx/sites-enabled/fire_catcher

echo "→ Starting services"
systemctl reload nginx

echo "✓ Deployed. Visit http://<server-ip>"
echo "Reminder: Ensure FIRMS_API_KEY is set in /opt/sentinela_verde/.env and restart the service if needed."
