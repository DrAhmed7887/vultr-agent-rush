#!/usr/bin/env bash
# Push the code to the Vultr VM and restart. Usage: deploy/deploy.sh   (needs the `ahmes` SSH alias)
set -euo pipefail
cd "$(dirname "$0")/.."
rsync -az --delete --exclude .venv --exclude .git --exclude __pycache__ --exclude 'runs.db' --exclude video ./ ahmes:/opt/ahmes/
ssh ahmes 'set -e
  id ahmes >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin ahmes
  usermod -aG docker ahmes
  mkdir -p /var/lib/ahmes/audio && chown -R ahmes:ahmes /var/lib/ahmes
  chown root:ahmes /etc/ahmes.env && chmod 640 /etc/ahmes.env
  docker build -q -t ahmes-sandbox:1 /opt/ahmes/sandbox >/dev/null
  cp /opt/ahmes/deploy/ahmes.service /etc/systemd/system/ahmes.service
  cp /opt/ahmes/deploy/Caddyfile /etc/caddy/Caddyfile
  systemctl daemon-reload && systemctl enable -q ahmes && systemctl restart ahmes && systemctl reload caddy || systemctl restart caddy
  ufw allow 80/tcp >/dev/null && ufw allow 443/tcp >/dev/null
  sleep 3; curl -fsS localhost:8000/health'
