#!/usr/bin/env bash
# Gate locale : format, lint, tests. Miroir de .github/workflows/ci.yml.
# Parite a l'oracle : tests golden si DV_ORACLE_DIR (ou reference/), scripts/oracle_stability.sh.
set -euo pipefail
cargo fmt --all --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
