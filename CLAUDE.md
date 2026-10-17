# CLAUDE.md

Port Rust de DeepVariant 1.10.0. L'oracle est l'image `google/deepvariant:1.10.0` et les sources
clonees par `scripts/fetch_oracle.sh` (ou `../deepvariant`).

- Gate locale : `./scripts/check.sh` (fmt, clippy `-D warnings`, tests).
- Un etage n'est porte que lorsque `dv-diff` le compare a l'oracle : make_examples et
  postprocess octet-identiques, modele sous la tolerance de ROADMAP.md.
- Le chemin scalaire/CPU est la reference ; SIMD et GPU (Metal, CUDA, ROCm) s'y comparent par
  un test nomme, jamais l'inverse.
- Chaque divergence voulue va dans `DIVERGENCES.md` avec sa raison.
- Pas de tiret cadratin dans les textes.
