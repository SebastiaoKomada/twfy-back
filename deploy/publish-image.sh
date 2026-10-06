#!/usr/bin/env bash
# Uso: bash deploy/publish-image.sh SEU_USUARIO/tw4y-api 1.0.0
set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "Uso: $0 USUARIO/REPOSITORIO TAG" >&2
  exit 1
fi

IMAGE_REPOSITORY=$1
IMAGE_TAG=$2
cd "$(dirname "$0")/.."
BUILD_CONTEXT="$PWD"
# Aceita o backend na raiz de twfy-back ou na pasta backend deste workspace.
if [ ! -f "$BUILD_CONTEXT/Dockerfile" ]; then
  BUILD_CONTEXT="$BUILD_CONTEXT/backend"
fi
if [ ! -f "$BUILD_CONTEXT/Dockerfile" ]; then
  echo "Dockerfile do backend não encontrado." >&2
  exit 1
fi

# Faça docker login antes de executar. amd64 atende t3; arm64 atende t4g.
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  --tag "$IMAGE_REPOSITORY:$IMAGE_TAG" \
  --push \
  "$BUILD_CONTEXT"
