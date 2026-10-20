<!--
Title: one sentence stating the outcome, e.g. "Read and write TFRecord byte-identically to the oracle".
Body: English. Delete any section that does not apply.
-->

One or two sentences: what this changes and why.

## Changes

- `path/or/crate`: what changed there.

## Parity against DeepVariant 1.10.0

What was compared to the oracle, how (`dv-diff`, golden test, `scripts/oracle_stability.sh`), and the result in numbers. Any intended divergence is listed in `DIVERGENCES.md`.

## Verification

- [ ] `./scripts/check.sh` passes locally
- [ ] Golden tests ran with the oracle present (not skipped)

## Not covered

What was not checked, and any risk the reviewer should know.

Closes #
