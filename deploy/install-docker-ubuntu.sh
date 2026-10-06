#!/usr/bin/env bash
# Execute na EC2 Ubuntu: sudo bash install-docker-ubuntu.sh
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
  echo "Execute com sudo." >&2
  exit 1
fi

# shellcheck disable=SC1091
source /etc/os-release
if [ "$ID" != "ubuntu" ]; then
  echo "Este script é para Ubuntu. Use a instalação oficial para sua distribuição." >&2
  exit 1
fi

apt-get update
apt-get install -y ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

DOCKER_ARCH=$(dpkg --print-architecture)
DOCKER_SUITE=${UBUNTU_CODENAME:-$VERSION_CODENAME}
cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $DOCKER_SUITE
Components: stable
Architectures: $DOCKER_ARCH
Signed-By: /etc/apt/keyrings/docker.asc
EOF

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
docker compose version
