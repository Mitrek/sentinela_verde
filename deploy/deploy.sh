#!/bin/bash
set -e

echo "→ Creating system user 'firecatcher'"
if ! id "firecatcher" &>/dev/null; then
    useradd -r -s /usr/sbin/nologin firecatcher
fi

echo "→ Installing system dependencies (python3.11, nginx, rsync)"
apt-get update
apt-get install -y python3.11 python3.11-venv nginx rsync

echo "→ Setting up /opt/fire_catcher directory"
mkdir -p /opt/fire_catcher
chown firecatcher:firecatcher /opt/fire_catcher

echo "→ Copying project files to /opt/fire_catcher"
rsync -av --exclude 'venv' --exclude '.git' ./ /opt/fire_catcher/
chown -R firecatcher:firecatcher /opt/fire_catcher

echo "→ Creating virtualenv and installing requirements"
sudo -u firecatcher python3.11 -m venv /opt/fire_catcher/venv
sudo -u firecatcher /opt/fire_catcher/venv/bin/pip install --upgrade pip
sudo -u firecatcher /opt/fire_catcher/venv/bin/pip install -r /opt/fire_catcher/requirements.txt

echo "→ Creating static output directory"
sudo -u firecatcher mkdir -p /opt/fire_catcher/static

echo "→ Copying .env file"
if [ -f ".env" ]; then
    cp .env /opt/fire_catcher/.env
    chown firecatcher:firecatcher /opt/fire_catcher/.env
else
    echo "Warning: .env file not found in current directory. Please create /opt/fire_catcher/.env manually."
fi

echo "→ Installing systemd service"
cp deploy/fire_catcher.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now fire_catcher

echo "→ Configuring Nginx"
cp deploy/nginx.conf /etc/nginx/sites-available/fire_catcher
ln -sf /etc/nginx/sites-available/fire_catcher /etc/nginx/sites-enabled/fire_catcher
rm -f /etc/nginx/sites-enabled/default

echo "→ Starting services"
systemctl reload nginx

echo "✓ Deployed. Visit http://<server-ip>"
echo "Reminder: Ensure FIRMS_API_KEY is set in /opt/fire_catcher/.env and restart the service if needed."
