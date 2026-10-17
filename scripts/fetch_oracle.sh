#!/usr/bin/env bash
# Recupere l'oracle : sources DeepVariant 1.10.0 et image Docker officielle (binaires de reference).
set -euo pipefail
DV_VERSION="${DV_VERSION:-1.10.0}"
mkdir -p reference
[ -d reference/deepvariant ] || git clone --depth 1 --branch "v${DV_VERSION}" \
  https://github.com/google/deepvariant.git reference/deepvariant
docker pull "google/deepvariant:${DV_VERSION}"
