# Recherche de dependances (2026-10-17)

Etat de l'ecosysteme Rust pour chaque sous-module du port, verifie sur crates.io et dans les
depots amont le 2026-10-17. Versions et dates de cette date ; `Cargo.lock` reste le pin de record
une fois les choix faits. "dl" = telechargements sur 90 jours selon crates.io.

La regle de tri est celle de bwa-mem4 : une dependance n'est acceptable que si elle ne s'interpose
pas entre nous et l'octet-identite, ou si elle **est** la bibliotheque que l'oracle utilise.

## Resume des recommandations

| Sous-module | Choix propose | Alternative | Issue |
|---|---|---|---|
| BAM/CRAM/FASTA en lecture | `rust-htslib` 1.0.1 | `noodles` 0.118 | #6 |
| VCF/gVCF en ecriture | `rust-htslib`, sous reserve de la version htslib (voir plus bas) | `noodles-vcf` + formatage maison | #34, #35 |
| TFRecord | ecrit a la main (~100 lignes) + `crc32c` 0.6.8 | `tfrecord` 0.15 (abandonne, 2023) | #4 |
| tf.Example / protos | `prost` 0.14.4 pour les protos ; encodeur maison pour `tf.Example` | `protobuf` 3.7.2 | #4, #5 |
| gzip | `flate2` 1.1.10 (backend `zlib-rs`) ; on compare le flux decompresse | `libdeflater` 1.26.1 | #4 |
| Inference (CPU, Metal, CUDA, ROCm) | `burn` 0.22.0 | `ort` 2.0.0-rc.14, `candle` 0.11 | #20 |
| Poids | `safetensors` 0.8.0 + `burn-store` 0.22.0 | `burn-onnx` 0.22.0 | #21 |
| Smith-Waterman du realigner | port maison de libssw, `std::arch` + dispatch a l'execution | `parasail-rs`, `block-aligner` | #14 |
| RNG | `rand_mt` 6.1.0 (MT19937 et MT19937-64 de reference) + `randint` numpy et `absl::Uniform` portes a la main | `mt19937` 3.3.0 | #17 |
| Parallelisme et flux | `rayon` 1.12, `crossbeam-channel` 0.5.17 | | #18, #31 |
| CLI | `clap` 4.6.7 | | #37 |
| GBZ (pangenome) | `gbwt` 0.3.1 (Jouni Siren, auteur de GBWT) | binding C++ | #50 |

## I/O : htslib plutot que noodles, pour une raison precise

DeepVariant lit et ecrit tout par Nucleus, qui est une couche sur **htslib 1.18** (epingle dans le
`WORKSPACE` amont). Utiliser la meme bibliotheque supprime toute une classe de divergences : ordre
des reads renvoyes par une requete de region, decodage CRAM, et surtout le formatage des flottants
dans le VCF, que htslib fait avec ses propres routines.

- `rust-htslib` 1.0.1 (2026-06-29, 94 k dl) via `hts-sys` 2.2.1, deja utilise par bwa-mem4.
- **Piege :** `hts-sys` 2.2.1 embarque **htslib 1.23**, pas 1.18. Avant de s'appuyer sur lui pour
  ecrire le VCF, comparer les deux versions sur le formatage de `QUAL`, `GQ`, `PL`, `VAF` et sur
  l'en-tete. Si elles different, deux sorties : builder `hts-sys` contre un htslib 1.18 systeme, ou
  ecrire les lignes VCF nous-memes (ce que fait gatk-rs via htsjdk-rs) avec le formatage de 1.18.
- `noodles` 0.118 (2026-10-15, tres actif, utilise par gatk-rs cote test) : bon outil de validation
  et de diff, mais ce n'est pas la bibliotheque de l'oracle. A garder en dev-dependency dans
  `dv-diff`, comme bwa-mem4 le fait.

## TFRecord et tf.Example : l'octet-identite n'est peut-etre pas definie

Decouverte importante pour #4. `make_examples_native.cc` construit chaque exemple en remplissant la
`map<string, Feature>` de `tf.Example` puis appelle `SerializeToString` **sans** serialisation
deterministe. Protobuf C++ serialise alors une map dans l'ordre d'iteration de sa table de hachage,
ordre qui n'est pas garanti stable (protobuf peut le randomiser selon la version et le build : a verifier sur la version embarquee par TensorFlow dans l'image 1.10.0).

Consequence : il faut d'abord **mesurer** sur l'oracle (meme commande lancee deux fois, puis sur
deux machines) si les octets de l'exemple sont stables.

- s'ils sont stables, il faut reproduire l'ordre de la table de hachage de protobuf C++, ce qu'aucun
  crate ne fait : encodeur maison, ordre fige par des vecteurs de test ;
- s'ils ne le sont pas, le critere "octet-identique" doit devenir : **memes features, chacune
  octet-identique** (`image/encoded`, `variant/encoded`, `alt_allele_indices/encoded`, etc.), ordre
  des cles ignore. A trancher dans #8.

Dans les deux cas, `prost` reste le bon choix pour les protos internes (`Variant`, `CallVariantsOutput`),
dont les champs ne sont pas des maps et sont serialises dans l'ordre des numeros de champ. Les
`map` d'info de `Variant` ont le meme probleme et seront traitees pareil.

Le crate `tfrecord` 0.15 n'a pas bouge depuis 2023 et tire un generateur de protos TensorFlow : le
cadrage TFRecord (longueur u64 LE, CRC32C masque) tient en une centaine de lignes avec `crc32c`.

## Inference : Burn couvre seul les quatre cibles

| Crate | CPU | Metal | CUDA | ROCm | Etat |
|---|---|---|---|---|---|
| `burn` 0.22.0 (2026-10-06) | `burn-flex` (pur Rust) | `burn-wgpu` / CubeCL Metal | `burn-cuda` | `burn-rocm` (HIP) | tres actif, un seul code de modele |
| `ort` 2.0.0-rc.14 (ONNX Runtime 1.31) | oui | CoreML EP | CUDA / TensorRT EP | **MIGraphX seulement** | toujours en rc |
| `candle-core` 0.11.0 | oui | oui | oui | **non** | elimine pour ROCm |
| `tch` 0.26 (libtorch) | oui | MPS | oui | build ROCm de libtorch | 2 Go de libtorch, a eviter |
| `tract-onnx` 0.23.9 | oui | non | non | non | CPU seul, utile comme 2e oracle CPU |

Points verifies :

- **ROCm dans ONNX Runtime :** le ROCm EP a ete retire de l'arbre source en 1.23 ; AMD recommande
  MIGraphX. `ort` expose encore une feature `rocm` mais elle ne vise plus une version maintenue.
  Pour AMD, `ort` veut donc dire MIGraphX.
- **Burn :** `burn-ndarray`, `burn-tch` et `burn-candle` sont depreciees en 0.22 au profit de
  `burn-flex` (CPU) et des backends CubeCL. CubeCL (0.11.0) compile un meme noyau vers CUDA (PTX),
  HIP (AMDGPU), Metal (MSL, via wgpu ou le runtime `cubecl-metal`), Vulkan et CPU.
- **Padding SAME de TensorFlow :** `burn-nn` calcule le padding `Same` de facon asymetrique, le
  surplus en bas a droite, ce qui est la convention de TF. Le piege identifie dans #22 est donc
  couvert par Burn, a confirmer par le test couche par couche.
- **Precision :** TF active TF32 par defaut sur les GPU Ampere et plus. Pour #27, verifier que les
  backends CubeCL restent en fp32 strict, et l'imposer si besoin.

Recommandation pour #20 : `burn` comme chemin unique, `ort` (CPU, CUDA, CoreML) en feature de
validation croisee, `tract-onnx` en option comme deuxieme reference CPU pur Rust. Trois
implementations independantes qui s'accordent avec TF valent mieux qu'une.

Bas niveau, si un noyau maison s'avere necessaire (pre-traitement des images sur GPU, par exemple) :
ecrire en `#[cube]` CubeCL plutot qu'en `cudarc` 0.19 + `hip-sys` + `objc2-metal` separes, pour
garder un seul code. `cust`/Rust-CUDA (2022) est a ecarter.

## Realigner : porter libssw, ne pas l'emprunter

- `parasail-rs` 0.9.2 est un autre algorithme (autre tie-breaking, autres CIGAR) : pas d'octet-identite.
- `block-aligner` 0.5.1 (2024) : X-drop adaptatif, resultats differents par construction.
- `bio` 4.2.2 : SW scalaire, utile en test seulement.

Le fast_pass_aligner appelle libssw (Striped Smith-Waterman, Farrar) : le port maison est la seule
voie, scalaire d'abord, puis NEON/AVX2 avec `std::arch` et dispatch a l'execution comme les noyaux
de bwa-mem4. `pulp` 0.22 et `wide` 1.7 sont des options si on veut une couche SIMD portable, mais
bwa-mem4 a montre que les intrinseques directes rendent le diff contre le C lisible.

## RNG : rand_mt pour les generateurs, le reste a la main

- `rand_mt` 6.1.0 (2026-10-03) fournit MT19937 et MT19937-64 de reference, avec seeding
  `init_genrand` et `init_by_array`. Couvre `std::mt19937_64` (C++) et le generateur brut de numpy.
- Ce qu'aucun crate ne fournit, et qui est indispensable :
  - `np.random.RandomState.randint` (algorithme legacy par masque et rejet), appele par
    `nucleus/util/utils.py::reservoir_sample` ;
  - `absl::Uniform` (reduction d'intervalle propre a Abseil), appele par `sampling_util.h`.
- `randomkit` 0.1.1 (2018) annonce "numpy.random for Rust" mais n'est pas maintenu : a lire comme
  reference, pas a dependre.

## Pangenome

`gbwt` 0.3.1 et `gbz-base` 0.6.2 sont de Jouni Siren, l'auteur de GBWT/GBZ. Le crate `gbwt` est une
reimplementation partielle qui expose GBZ : suffisant a priori pour lire le graphe dans #50, a
verifier contre ce que `make_examples_pangenome_aware_dv.py` consomme.

## A faire avant de figer

1. Mesurer la stabilite des octets de `tf.Example` sur l'oracle (#4, #8).
2. Comparer le formatage VCF de htslib 1.18 et 1.23 (#34).
3. Prototype InceptionV3 en Burn sur `burn-flex` contre TF CPU sur 1 000 exemples de `testdata`
   (#20, #22), puis le meme graphe sur Metal (M4 Max), CUDA et ROCm.
