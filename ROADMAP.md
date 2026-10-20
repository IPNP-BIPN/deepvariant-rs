# Roadmap

Une phase = un jalon GitHub. Cible d'acceptation : sorties **octet-identiques** a DeepVariant 1.10.0 pour make_examples et postprocess_variants, tolerance chiffree pour le modele (voir #8). Ce fichier est genere par `scripts/bootstrap_github.py` au demarrage, puis tenu a la main comme journal des mesures, negatifs compris.

| Jalon | But |
|---|---|
| M0 : fondations et harnais oracle | Workspace, CI, oracle DeepVariant 1.10.0 epingle, I/O TFRecord/tf.Example et BAM, outil de diff. Rien n'est porte tant que la comparaison a l'oracle n'existe pas. |
| M1 : make_examples octet-identique | Allele counter, very sensitive caller, realigner, pileup et canaux, orchestration. Critere : chaque tf.Example identique octet par octet a l'oracle, cles et ordre compris. |
| M2 : call_variants CPU, parite TensorFlow | InceptionV3 en Rust sur CPU avec les poids publies, small model, sortie CVO. Critere : probabilites dans la tolerance fixee par #8, genotypes identiques. |
| M3 : backends GPU Metal, CUDA, ROCm | Le meme modele sur les trois GPU, derriere une barriere de parite ecrite avant le premier noyau. Critere : VCF final identique au chemin CPU. |
| M4 : postprocess_variants et pipeline complet | CVO vers VCF et gVCF octet-identiques, contigs haploides, binaire unique equivalent a run_deepvariant. |
| M5 : tous les modeles | WES, RNA-seq, PacBio, ONT R10.4, hybride PacBio+Illumina, MAS-Seq : canaux, alt-aligned pileup, direct phasing. |
| M6 : gate GIAB, performance, release | Concordance hap.py sur HG002, profilage, pipeline en flux, packaging et release. |
| M7 : DeepTrio, DeepSomatic, pangenome | Les variantes de DeepVariant, une fois le noyau stable. |

## M0 : fondations et harnais oracle

- #2 ci : matrice Linux x86_64/aarch64 + macOS, gate fmt/clippy/test
- #3 oracle : epingler DeepVariant 1.10.0 et produire les sorties de reference par etage
- #4 io : TFRecord + tf.Example octet-identiques (lecture et ecriture, gzip)
- #5 core : protos deepvariant.proto, realigner.proto et Nucleus via prost
- #6 io : lecture BAM/CRAM/FASTA/VCF avec la semantique Nucleus
- #7 diff : dv-diff, comparaison exemple par exemple, CVO et VCF
- #8 decision : politique de parite par etage (octet, tolerance flottante, concordance)

## M1 : make_examples octet-identique

- #10 make_examples : port de allelecounter.cc
- #11 make_examples : very sensitive caller et gVCF records (variant_calling.cc)
- #12 realigner : window_selector (C++ et Python)
- #13 realigner : assemblage local par graphe de De Bruijn
- #14 realigner : fast_pass_aligner et SSW, scalaire puis SIMD
- #15 pileup : pileup_image_native.cc et les 7 canaux par defaut
- #16 pileup : canaux optionnels et alt-aligned pileup
- #17 make_examples : reproduire exactement les tirages aleatoires (numpy et mt19937_64)
- #18 make_examples : regions, shards, filtres et ecriture des exemples

## M2 : call_variants CPU, parite TensorFlow

- #20 decision : framework d'inference Rust pour CPU + Metal + CUDA + ROCm
- #21 modele : conversion des poids officiels (SavedModel/checkpoint vers safetensors)
- #22 modele : InceptionV3 en Rust, couche par couche contre TensorFlow
- #23 call_variants : lecture des exemples, batchs, ecriture du CVO
- #24 modele : small model (MLP sur caracteristiques des candidats)
- #25 perf : banc call_variants CPU contre TensorFlow (x86 et Apple Silicon)

## M3 : backends GPU Metal, CUDA, ROCm

- #27 test(gpu) : barriere de parite GPU, a ecrire avant le premier backend
- #28 gpu(metal) : backend Apple Silicon, memoire unifiee
- #29 gpu(cuda) : backend NVIDIA
- #30 gpu(rocm) : backend AMD via HIP
- #31 perf(gpu) : pipeline en flux CPU make_examples vers GPU call_variants
- #32 ci(gpu) : ou faire tourner la barriere GPU

## M4 : postprocess_variants et pipeline complet

- #34 postprocess : CVO vers VCF octet-identique
- #35 postprocess : gVCF (blocs de reference, fusion, binarisation des GQ)
- #36 postprocess : contigs haploides et regions PAR
- #37 cli : deepvariant-rs run, equivalent de run_deepvariant

## M5 : tous les modeles

- #39 modeles : WES et RNA-seq (lectures courtes)
- #40 modeles : PacBio HiFi et ONT R10.4 (alt-aligned pileup, haplotypes)
- #41 modeles : hybride PacBio+Illumina et MAS-Seq

## M6 : gate GIAB, performance, release

- #43 test : gate GIAB HG002 avec hap.py (WGS, WES, PacBio, ONT)
- #44 perf : profil de bout en bout et objectif de debit
- #45 integration : bwa-mem4 puis deepvariant-rs sans fichier intermediaire
- #46 ci : release, crates.io, Homebrew, bioconda, Docker

## M7 : DeepTrio, DeepSomatic, pangenome

- #48 DeepTrio : make_examples multi-echantillon et modeles trio
- #49 DeepSomatic : tumeur/normal et tumeur seule
- #50 Pangenome-aware DeepVariant (GBZ)
- #51 decision : l'entrainement et les labelers restent en Python/TensorFlow

## Journal des mesures

- 2026-10-20, #60/#93 : les 1 083 exemples des 12 golden `*examples*.tfrecord.gz` de `testdata`
  (v1.10.0) presentent **679 ordres de cles distincts** dans la map `features`. L'ordre est donc
  tire par protobuf C++ a chaque exemple, pas fixe. Consequence : l'octet-identite de l'exemple
  entier n'est pas atteignable ; le critere de make_examples doit etre feature par feature
  (`crates/dv-io/tests/example_oracle.rs`). Chaque exemple se reencode a l'identique quand on
  conserve l'ordre lu, ce qui valide l'encodeur pour tout le reste (packing, longueurs, oneof).
- 2026-10-20, #60 : la commande golden `calling` de `create_golden.sh` lancee 3 fois dans
  `google/deepvariant:1.10.0` (amd64 emule sur Apple Silicon, `scripts/oracle_stability.sh`).
  Les 84 exemples ne sont **jamais** identiques octet par octet entre deux executions, malgre
  `--deterministic_serialization` : ce drapeau ne touche que les protos serialises en Python, les
  exemples le sont en C++ (`make_examples_native.cc:471`). Une fois trie ce qui sort d'une map,
  les 3 executions et le golden sont identiques : 84/84 exemples, 78/78 candidats. Les champs non
  ordonnes sont la map `features` de l'exemple, `info` de `Variant` et `VariantCall`, et dans
  `DeepVariantCall` les maps 2, 3, 5, 7, 10 plus `read_names`, `read_infos`, `ref_support` et
  `ref_support_ext`, remplis en parcourant la map `read_alleles` (`variant_calling.cc:686`). Le
  gVCF est stable octet par octet. Critere propose pour #93 : egalite sous la forme canonique de
  `dv-diff` (`crates/dv-diff/src/canonical.rs`). Non mesure : une deuxieme machine (x86 natif).
