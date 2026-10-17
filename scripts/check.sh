#!/usr/bin/env bash
# Gate locale : format, lint, tests. Miroir de .github/workflows/ci.yml.
# Ne couvre PAS la parite a l'oracle (scripts/oracle_diff.sh, a ecrire, issue M0).
set -euo pipefail
cargo fmt --all --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
