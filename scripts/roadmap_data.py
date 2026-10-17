"""Source unique des jalons et issues du projet GitHub (scripts/bootstrap_github.py la lit).

Garde en clair ce qui a ete ouvert sur GitHub au demarrage, pour que ROADMAP.md et le tracker
partent du meme texte.
"""

UPSTREAM = "google/deepvariant v1.10.0"

LABELS = [
    ("gpu", "Inference GPU, tous backends", "0e75b6"),
    ("metal", "Backend Metal (Apple Silicon)", "5319e7"),
    ("cuda", "Backend CUDA (NVIDIA)", "76b900"),
    ("rocm", "Backend ROCm/HIP (AMD)", "ed1c24"),
    ("parity", "Parite a l'oracle DeepVariant 1.10.0", "0e8a16"),
    ("make-examples", "Etage make_examples", "fbca04"),
    ("call-variants", "Etage call_variants (modele)", "c5def5"),
    ("postprocess", "Etage postprocess_variants", "bfd4f2"),
    ("io", "Formats : BAM/CRAM/VCF/TFRecord", "d4c5f9"),
    ("perf", "Debit, memoire, profilage", "1d76db"),
    ("ci", "Integration continue et release", "000000"),
    ("decision", "Choix d'architecture a trancher avant le code", "b60205"),
    ("meta", "Issue chapeau d'un jalon", "ededed"),
]

M = {
    "M0": ("M0 : fondations et harnais oracle",
           "Workspace, CI, oracle DeepVariant 1.10.0 epingle, I/O TFRecord/tf.Example et BAM, "
           "outil de diff. Rien n'est porte tant que la comparaison a l'oracle n'existe pas."),
    "M1": ("M1 : make_examples octet-identique",
           "Allele counter, very sensitive caller, realigner, pileup et canaux, orchestration. "
           "Critere : chaque tf.Example identique octet par octet a l'oracle, cles et ordre compris."),
    "M2": ("M2 : call_variants CPU, parite TensorFlow",
           "InceptionV3 en Rust sur CPU avec les poids publies, small model, sortie CVO. "
           "Critere : probabilites dans la tolerance fixee par #DECISION_TOL, genotypes identiques."),
    "M3": ("M3 : backends GPU Metal, CUDA, ROCm",
           "Le meme modele sur les trois GPU, derriere une barriere de parite ecrite avant le premier "
           "noyau. Critere : VCF final identique au chemin CPU."),
    "M4": ("M4 : postprocess_variants et pipeline complet",
           "CVO vers VCF et gVCF octet-identiques, contigs haploides, binaire unique equivalent a "
           "run_deepvariant."),
    "M5": ("M5 : tous les modeles",
           "WES, RNA-seq, PacBio, ONT R10.4, hybride PacBio+Illumina, MAS-Seq : canaux, alt-aligned "
           "pileup, direct phasing."),
    "M6": ("M6 : gate GIAB, performance, release",
           "Concordance hap.py sur HG002, profilage, pipeline en flux, packaging et release."),
    "M7": ("M7 : DeepTrio, DeepSomatic, pangenome",
           "Les variantes de DeepVariant, une fois le noyau stable."),
}

ACCEPT_BYTES = ("**Critere d'acceptation :** sur les jeux de `testdata/` et sur chr20 HG002, la sortie "
                "de l'etage est identique octet par octet a celle de l'oracle 1.10.0 (Docker), "
                "verifiee par `dv-diff`. Le chemin scalaire est la reference ; un chemin SIMD ou "
                "parallele doit s'y comparer par un test nomme.")

# (cle, jalon, titre, labels, corps). Les meta issues recoivent les autres en sous-issues.
ISSUES = [
    # ---------------- M0
    ("M0", "M0", "meta(M0) : fondations et harnais oracle", ["meta"],
     "Chapeau du jalon M0. Meme principe que bwa-mem4 et gatk-rs : **on ne porte rien avant de "
     "savoir comparer a l'oracle**. Sous-issues ci-dessous."),
    ("CI", "M0", "ci : matrice Linux x86_64/aarch64 + macOS, gate fmt/clippy/test", ["ci"],
     "Le squelette a deja `.github/workflows/ci.yml` et `scripts/check.sh`. Reste :\n\n"
     "- cache cargo, job hebdomadaire sur `main` (comme bwa-mem4) ;\n"
     "- job `lint-current-stable` pour voir arriver les nouveaux lints clippy ;\n"
     "- job `parity` sur `testdata/` des que #ORACLE et #DIFF existent.\n\n"
     "**Fait quand :** chaque PR passe les trois OS, et `parity` est requis sur `main`."),
    ("ORACLE", "M0", "oracle : epingler DeepVariant 1.10.0 et produire les sorties de reference par etage",
     ["parity"],
     "Image `google/deepvariant:1.10.0`, sources clonees par `scripts/fetch_oracle.sh`.\n\n"
     "Produire et archiver (hors git, hash dans le depot) pour chaque jeu :\n\n"
     "1. `make_examples` : TFRecord d'exemples (`--task` 0..N), candidats, gVCF records ;\n"
     "2. `call_variants` : CVO TFRecord, en CPU **et** en GPU (image `-gpu`) pour mesurer la variabilite amont elle-meme ;\n"
     "3. `postprocess_variants` : VCF et gVCF.\n\n"
     "Jeux : le `testdata` amont (NA12878 chr20 + `ucsc.hg19.chr20.unittest.fasta`), puis HG002 chr20 30x (GIAB v4.2.1).\n\n"
     "**Piege :** les sorties dependent de `--task`/`--num_shards` et des seeds ; noter la ligne de commande exacte a cote de chaque sortie.\n\n"
     "**Fait quand :** `scripts/oracle_run.sh <jeu>` regenere tout et verifie les hash."),
    ("TFREC", "M0", "io : TFRecord + tf.Example octet-identiques (lecture et ecriture, gzip)", ["io", "parity"],
     "Les exemples sont des `tf.Example` serialises dans des TFRecord (souvent `.gz`). L'octet-identite "
     "exige :\n\n"
     "- le cadrage TFRecord (longueur u64 LE, CRC32C masque des deux champs) ;\n"
     "- **l'ordre de serialisation protobuf** de la `Features` map : protobuf C++ trie-t-il les cles "
     "a la serialisation (deterministic) ? A mesurer sur l'oracle avant de choisir prost ;\n"
     "- la compression gzip : comparer le flux **decompresse**, le flux compresse n'est pas un critere.\n\n"
     "Pas de dependance TensorFlow. Lecture en flux, sans tout charger.\n\n"
     "**Fait quand :** relire puis reecrire un TFRecord oracle donne les memes octets decompresses."),
    ("PROTO", "M0", "core : protos deepvariant.proto, realigner.proto et Nucleus via prost", ["io"],
     "Generer les types depuis `deepvariant/protos/*.proto` et les protos Nucleus utilises "
     "(`Read`, `Variant`, `VariantCall`, `Range`, `ReferenceSequence`).\n\n"
     "`MakeExamplesOptions`, `CallVariantsOutput`, `DeepVariantCall`, `PileupImageOptions` en "
     "premier. Les options CLI se construisent comme dans `make_examples_options.py`, y compris les "
     "defauts par `--model_type`.\n\n"
     "**Fait quand :** un `MakeExamplesOptions` texte de l'oracle se relit et se reserialise a l'identique."),
    ("HTS", "M0", "io : lecture BAM/CRAM/FASTA/VCF avec la semantique Nucleus", ["io"],
     "rust-htslib, comme bwa-mem4. Reproduire ce que Nucleus fait en plus de htslib :\n\n"
     "- conversion en proto `Read` (alignement, CIGAR, qualites, aux) ;\n"
     "- filtres par defaut de make_examples (`min_mapping_quality`, duplicates, secondary, "
     "supplementary, QC fail, `keep_legacy_allele_counter_behavior`) ;\n"
     "- requetes par region et ordre des reads retournes.\n\n"
     "**Fait quand :** pour une region donnee, la liste des reads (apres filtres) est identique a celle "
     "de Nucleus, dans le meme ordre."),
    ("DIFF", "M0", "diff : dv-diff, comparaison exemple par exemple, CVO et VCF", ["parity"],
     "L'outil qui rend le reste possible :\n\n"
     "- **exemples** : appariement par (locus, alt alleles), premier champ divergent, et pour "
     "`image/encoded` la premiere cellule (ligne, colonne, canal) differente avec les deux valeurs ;\n"
     "- **CVO** : ecart max/moyen des probabilites, nombre de changements d'argmax ;\n"
     "- **VCF** : diff ligne a ligne en ignorant l'en-tete `##commandline`.\n\n"
     "Sortie lisible et code retour non nul sur divergence (utilisable en CI)."),
    ("DECISION_TOL", "M0", "decision : politique de parite par etage (octet, tolerance flottante, concordance)",
     ["decision", "parity"],
     "A trancher **avant** M2. Proposition :\n\n"
     "| Etage | Critere |\n|---|---|\n"
     "| make_examples | octet-identique |\n"
     "| call_variants CPU | `max |p - p_tf| <= 1e-5`, argmax identique sur 100 % des exemples |\n"
     "| call_variants GPU | memes bornes contre **notre** CPU, determinisme run a run |\n"
     "| postprocess (CVO oracle en entree) | octet-identique |\n"
     "| pipeline complet | VCF identique sur `testdata`, hap.py identique a 4 decimales sur HG002 |\n\n"
     "Point ouvert : l'oracle TF lui-meme varie entre CPU et GPU (#ORACLE le mesure). Si TF GPU "
     "change des GQ, notre borne ne peut pas etre plus stricte que l'amont contre lui-meme."),

    # ---------------- M1
    ("M1", "M1", "meta(M1) : make_examples octet-identique", ["meta", "make-examples"],
     "Chapeau du jalon M1. Ordre de port : allele counter, caller, realigner, pileup, orchestration. "
     "Chaque etage a sa propre comparaison a l'oracle (sorties intermediaires exposees par "
     "`--emit_*` ou par les tests amont)."),
    ("AC", "M1", "make_examples : port de allelecounter.cc", ["make-examples", "parity"],
     "Source : `deepvariant/allelecounter.{h,cc}`.\n\n"
     "Comptage par position : alleles de reference, substitutions, insertions/deletions "
     "normalisees a gauche, `read_alleles`, qualites minimales, `AlleleCounterOptions`. "
     "Attention au comportement `keep_legacy_allele_counter_behavior` et aux soft-clips.\n\n"
     "Reprendre `allelecounter_test.cc` comme tests unitaires Rust.\n\n" + ACCEPT_BYTES),
    ("VSC", "M1", "make_examples : very sensitive caller et gVCF records (variant_calling.cc)",
     ["make-examples", "parity"],
     "Source : `variant_calling.{h,cc}`, `variant_calling_multisample.cc`, `very_sensitive_caller.py`.\n\n"
     "- candidats a partir des comptes : `min_count_snps`, `min_fraction_snps/indels`, "
     "`vsc_min_fraction_multiplier`, alleles multiples ;\n"
     "- `CallsFromAlleleCounts` et records non-variants pour le gVCF (GQ de reference par "
     "position, binarisation) ;\n"
     "- l'ordre des alleles alt dans `DeepVariantCall`.\n\n" + ACCEPT_BYTES),
    ("WS", "M1", "realigner : window_selector (C++ et Python)", ["make-examples", "parity"],
     "Source : `realigner/window_selector.{cc,py}`. Choix des fenetres actives a partir des comptes "
     "(`ws_use_window_selector_model`, modele lineaire de `realigner.proto`), fusion des fenetres "
     "proches, bornes de region.\n\n"
     "Les deux implementations amont coexistent : verifier laquelle 1.10.0 utilise par defaut."),
    ("DBG", "M1", "realigner : assemblage local par graphe de De Bruijn", ["make-examples", "parity"],
     "Source : `realigner/debruijn_graph.{h,cc}`. Construction pour k croissant, elagage des "
     "aretes faibles, detection de cycles, enumeration des haplotypes candidats.\n\n"
     "**Piege :** l'ordre d'enumeration des chemins depend de l'ordre d'iteration des structures "
     "boost/absl ; il faut reproduire cet ordre, pas seulement l'ensemble des haplotypes.\n\n"
     + ACCEPT_BYTES),
    ("FPA", "M1", "realigner : fast_pass_aligner et SSW, scalaire puis SIMD", ["make-examples", "parity", "perf"],
     "Source : `realigner/fast_pass_aligner.{h,cc}`, `realigner/ssw.{h,cc}` (libssw).\n\n"
     "1. Port scalaire de Striped Smith-Waterman, comme reference ;\n"
     "2. alignement read contre haplotype puis haplotype contre reference, recalcul des CIGAR ;\n"
     "3. noyaux NEON et AVX2 derriere un trait, avec `assert_backend_matches_scalar` comme dans "
     "bwa-mem4 (meme regle : premier maximum gagne a egalite, saturation 8 bits puis repli 16 bits).\n\n"
     "Reutiliser ce qui a ete appris dans `bwa-mem4/docs/kernel-ceiling-and-dead-ends.md`.\n\n"
     + ACCEPT_BYTES),
    ("PILEUP", "M1", "pileup : pileup_image_native.cc et les 7 canaux par defaut", ["make-examples", "parity"],
     "Source : `pileup_image_native.{h,cc}`, `channels/`, `pileup_channel_lib.cc`.\n\n"
     "Image 100 x 221 x C (`dv_constants.PILEUP_DEFAULT_*`) : lignes de reference, tri des reads, "
     "`read_base`, `base_quality`, `mapping_quality`, `strand`, `read_supports_variant`, "
     "`base_differs_from_ref`, `insert_size` (WGS). Echantillonnage quand il y a plus de reads que de "
     "lignes.\n\n"
     "Chaque canal est une fonction pure : un test par canal contre l'oracle avant l'image complete.\n\n"
     + ACCEPT_BYTES),
    ("CHAN", "M1", "pileup : canaux optionnels et alt-aligned pileup", ["make-examples", "parity"],
     "Le reste de `channels/` : `haplotype_tag`, `allele_frequency`, `gc_content`, "
     "`homopolymer_*`, `identity`, `gap_compressed_identity`, `read_mapping_percent`, "
     "`avg_base_quality`, `base_methylation`, `base_6ma`, `blank`...\n\n"
     "Et `alt_aligned_pileup_lib.cc` (`diff_channels`, `base_channels`, `rows`) utilise par les "
     "modeles long-reads. Ces canaux deviennent obligatoires en M5."),
    ("RNG", "M1", "make_examples : reproduire exactement les tirages aleatoires (numpy et mt19937_64)",
     ["make-examples", "parity", "decision"],
     "Deux generateurs amont, tous deux a reproduire bit a bit :\n\n"
     "- Python : `np.random.RandomState(1400605801)` dans `make_examples_core.py` "
     "(`utils.reservoir_sample` sur les reads, sous-echantillonnage). Il faut le MT19937 de numpy "
     "**et** son algorithme exact de `randint`/`random_sample`, pas seulement le flux brut ;\n"
     "- C++ : `std::mt19937_64` et `absl::Uniform` dans `sampling_util.h` (`ReservoirSample`). "
     "`absl::Uniform` a son propre algorithme de reduction d'intervalle.\n\n"
     "**Fait quand :** pour une seed et une liste donnees, les indices tires sont identiques "
     "(vecteurs de test generes depuis l'oracle)."),
    ("MEORCH", "M1", "make_examples : regions, shards, filtres et ecriture des exemples", ["make-examples", "parity"],
     "Source : `make_examples_core.py`, `make_examples_native.cc`, `calling_regions_utils.py`, "
     "`exclude_contigs.py`.\n\n"
     "- `--regions`, `--exclude_regions`, partition en `partition_size`, attribution `--task` / "
     "`--num_shards` ;\n"
     "- ordre d'ecriture des exemples et cles du `tf.Example` (`locus`, `variant/encoded`, "
     "`alt_allele_indices/encoded`, `image/shape`, `sequencing_type`...) ;\n"
     "- parallelisme interne (rayon) **sans** changer l'ordre de sortie.\n\n" + ACCEPT_BYTES),

    # ---------------- M2
    ("M2", "M2", "meta(M2) : call_variants CPU, parite TensorFlow", ["meta", "call-variants"],
     "Chapeau du jalon M2. Le modele est un InceptionV3 Keras (`keras_modeling.py`) ; on ne fait "
     "pas d'entrainement, seulement l'inference avec les poids officiels."),
    ("DECISION_FW", "M2", "decision : framework d'inference Rust pour CPU + Metal + CUDA + ROCm",
     ["decision", "gpu", "call-variants"],
     "Contrainte : **un seul code de modele** pour les quatre cibles.\n\n"
     "| Option | CPU | Metal | CUDA | ROCm | Remarque |\n|---|---|---|---|---|---|\n"
     "| Burn (CubeCL) | ndarray / cubecl-cpu | wgpu-Metal | burn-cuda | burn-rocm (HIP) | pur Rust, meme graphe partout |\n"
     "| candle | oui | oui | oui | non | pas de ROCm |\n"
     "| ort (ONNX Runtime) | oui | CoreML EP | CUDA EP | ROCm/MIGraphX EP | binaire C++, bon oracle croise |\n\n"
     "Proposition : **Burn** comme chemin principal, **ort** en feature optionnelle pour valider "
     "independamment (deux implementations qui s'accordent avec TF valent mieux qu'une).\n\n"
     "A mesurer avant de trancher : precision fp32 stricte des convolutions par backend, support "
     "du padding SAME asymetrique de TF, debit batch 1024 sur M4 Max."),
    ("WEIGHTS", "M2", "modele : conversion des poids officiels (SavedModel/checkpoint vers safetensors)",
     ["call-variants"],
     "Les modeles 1.10.0 (WGS, WES, PACBIO, ONT_R104, HYBRID_PACBIO_ILLUMINA, MASSEQ) sont publies "
     "par Google, **pas** redistribues ici.\n\n"
     "- `scripts/convert_weights.py`, lance une fois avec TF, ecrit des safetensors + un JSON "
     "(canaux, forme d'entree, `model.example_info.json`) ;\n"
     "- hash SHA-256 des fichiers source et convertis dans le depot ;\n"
     "- `deepvariant-rs` refuse un modele dont le hash est inconnu sauf `--unsafe-model`."),
    ("INCEPTION", "M2", "modele : InceptionV3 en Rust, couche par couche contre TensorFlow", ["call-variants", "parity"],
     "Source : `keras_modeling.py` (`inceptionv3`, `build_classification_head`).\n\n"
     "Pieges connus :\n\n"
     "- padding `SAME` de TF : asymetrique (plus de padding a droite/en bas) quand le total est impair ;\n"
     "- `BatchNormalization` : epsilon Keras (1e-3), fusion dans la convolution seulement si le test le permet ;\n"
     "- pretraitement de l'entree (mise a l'echelle des uint8) identique a `dv_utils` ;\n"
     "- tete de classification : 3 sorties (hom-ref, het, hom-alt) puis softmax.\n\n"
     "Test : activations intermediaires (`--activation_layers` de `call_variants.py`) comparees couche par couche."),
    ("CV", "M2", "call_variants : lecture des exemples, batchs, ecriture du CVO", ["call-variants", "parity"],
     "Source : `call_variants.py`, `data_providers.py`.\n\n"
     "- lecture en flux du TFRecord, decodage de l'image, batch (`--batch_size`) ;\n"
     "- `CallVariantsOutput` : `variant`, `alt_allele_indices`, `genotype_probabilities`, debug info optionnelle ;\n"
     "- meme ordre de sortie que l'oracle.\n\n"
     "**Fait quand :** CVO conforme a #DECISION_TOL sur `testdata` et chr20."),
    ("SMALL", "M2", "modele : small model (MLP sur caracteristiques des candidats)", ["call-variants", "parity", "perf"],
     "Source : `small_model/` (`inference.py`, `keras_config.py`, `make_small_model_examples.py`).\n\n"
     "Depuis 1.8, un petit modele appelle directement les candidats faciles et ne laisse au CNN que "
     "les cas difficiles. C'est un gain de debit important, a porter tel quel : extraction des "
     "caracteristiques, seuils de confiance, et le meme partage entre les deux chemins."),
    ("CPUBENCH", "M2", "perf : banc call_variants CPU contre TensorFlow (x86 et Apple Silicon)", ["perf", "call-variants"],
     "Exemples/s par coeur, batch 64 a 1024, threads 1 a N. Reference : l'image Docker CPU. "
     "Donne la ligne de base que les GPU devront battre."),

    # ---------------- M3
    ("M3", "M3", "meta(M3) : backends GPU Metal, CUDA, ROCm", ["meta", "gpu"],
     "Chapeau du jalon M3. Meme methode que bwa-mem4 (`docs/gpu-plan.md`) : la barriere d'abord, "
     "les noyaux ensuite, et un repli CPU toujours disponible."),
    ("GPUGATE", "M3", "test(gpu) : barriere de parite GPU, a ecrire avant le premier backend",
     ["gpu", "parity"],
     "Un backend GPU qui donne le bon genotype sur 99,99 % des exemples est un backend faux : sur "
     "un WGS, 0,01 % represente des centaines de variants.\n\n"
     "Tests nommes :\n\n"
     "1. probabilites GPU contre CPU sous la borne #DECISION_TOL ;\n"
     "2. argmax identique, y compris sur un jeu d'exemples **a quasi-egalite** extrait de chr20 ;\n"
     "3. determinisme : deux executions donnent les memes octets de CVO ;\n"
     "4. independance au batch : batch 1, 7, 1024 donnent les memes probabilites ;\n"
     "5. pas de fp16/bf16/TF32 implicite (TF32 est actif par defaut sur Ampere pour les matmul) ;\n"
     "6. VCF final identique au chemin CPU sur `testdata`."),
    ("METAL", "M3", "gpu(metal) : backend Apple Silicon, memoire unifiee", ["gpu", "metal"],
     "Via le framework retenu par #DECISION_FW (Burn wgpu/Metal ou MSL direct).\n\n"
     "- profiter de la memoire unifiee : pas de copie des images entre make_examples et le modele ;\n"
     "- verifier que les convolutions restent en fp32 (pas de `half` silencieux) ;\n"
     "- banc M1 a M4 Max, comparaison au CPU (#CPUBENCH).\n\n"
     "**Fait quand :** #GPUGATE passe sur macOS arm64."),
    ("CUDA", "M3", "gpu(cuda) : backend NVIDIA", ["gpu", "cuda"],
     "- fp32 strict par defaut, TF32 desactive explicitement ;\n"
     "- mode `--precision fp16` optionnel, hors gate, documente comme non conforme ;\n"
     "- cibles : T4, L4, A100, H100 ; comparer a l'image `deepvariant:1.10.0-gpu` et a Parabricks "
     "`deepvariant` comme point de repere de debit.\n\n"
     "**Fait quand :** #GPUGATE passe sur au moins deux architectures NVIDIA."),
    ("ROCM", "M3", "gpu(rocm) : backend AMD via HIP", ["gpu", "rocm"],
     "- ROCm 6.x, cibles MI210/MI300 et RDNA3 grand public ;\n"
     "- meme graphe que CUDA, seul le runtime change ;\n"
     "- l'amont n'a **aucun** support AMD : c'est le seul endroit ou il n'y a pas d'oracle GPU, d'ou "
     "l'importance de la comparaison a notre CPU.\n\n"
     "**Fait quand :** #GPUGATE passe sur une carte AMD."),
    ("SCHED", "M3", "perf(gpu) : pipeline en flux CPU make_examples vers GPU call_variants", ["gpu", "perf"],
     "L'amont 1.10 a `fast_pipeline.cc` (exemples en memoire partagee). Ici, dans un seul processus :\n\n"
     "- canal borne entre les workers make_examples et le consommateur GPU, double buffering ;\n"
     "- plusieurs GPU (un consommateur par device) ;\n"
     "- l'ordre de sortie reste celui de l'oracle (reordonnancement par index d'exemple).\n\n"
     "Les fichiers intermediaires restent disponibles (`--keep-intermediates`) pour le diff."),
    ("GPUCI", "M3", "ci(gpu) : ou faire tourner la barriere GPU", ["ci", "gpu", "decision"],
     "Les runners GitHub standard n'ont ni CUDA ni ROCm. Options : runners GPU payants, runner "
     "auto-heberge (Mac M4 Max du labo pour Metal), instance cloud lancee a la demande. "
     "Decider avant d'annoncer un backend comme supporte."),

    # ---------------- M4
    ("M4", "M4", "meta(M4) : postprocess_variants et pipeline complet", ["meta", "postprocess"],
     "Chapeau du jalon M4."),
    ("PP", "M4", "postprocess : CVO vers VCF octet-identique", ["postprocess", "parity"],
     "Source : `postprocess_variants.py`, `postprocess_variants.cc`.\n\n"
     "- regroupement des CVO multi-alleliques, `get_alt_alleles`, vraisemblances de genotypes a "
     "partir des probabilites, QUAL et GQ (arrondis compris) ;\n"
     "- filtres `RefCall` et `LowQual`, `--qual_filter`, `--cnn_homref_call_min_gq` ;\n"
     "- tri des enregistrements et en-tete VCF.\n\n"
     "Entree pour le test : **le CVO de l'oracle**, pour isoler l'etage. " + ACCEPT_BYTES),
    ("GVCF", "M4", "postprocess : gVCF (blocs de reference, fusion, binarisation des GQ)", ["postprocess", "parity"],
     "Fusion des enregistrements non-variants de make_examples (#VSC) avec les appels, "
     "`--gvcf_gq_binsize`, blocs `<*>`, chevauchements avec les variants.\n\n" + ACCEPT_BYTES),
    ("HAPLOID", "M4", "postprocess : contigs haploides et regions PAR", ["postprocess", "parity"],
     "`--haploid_contigs`, `--par_regions_bed` (chrX/chrY chez les hommes) : regles de genotype et "
     "de GQ specifiques."),
    ("RUN", "M4", "cli : deepvariant-rs run, equivalent de run_deepvariant", ["make-examples", "call-variants", "postprocess"],
     "Un binaire, les memes drapeaux que `scripts/run_deepvariant.py` (`--model_type`, "
     "`--ref`, `--reads`, `--output_vcf`, `--output_gvcf`, `--num_shards`, `--regions`...), plus "
     "`--device cpu|metal|cuda|rocm|auto`.\n\n"
     "Sous-commandes `make_examples`, `call_variants`, `postprocess_variants` pour le diff etage par etage."),

    # ---------------- M5
    ("M5", "M5", "meta(M5) : tous les modeles", ["meta"],
     "Chapeau du jalon M5. Chaque modele = ses canaux, ses options par defaut, son jeu de test oracle."),
    ("WES", "M5", "modeles : WES et RNA-seq (lectures courtes)", ["make-examples", "call-variants", "parity"],
     "Options par defaut propres au WES (pas d'`insert_size`), regions de capture ; RNA-seq "
     "(`split_skip_reads`, modele RNA). Jeux GIAB exome HG002."),
    ("LONG", "M5", "modeles : PacBio HiFi et ONT R10.4 (alt-aligned pileup, haplotypes)",
     ["make-examples", "call-variants", "parity"],
     "- `alt_aligned_pileup`, tri par haplotype (`HP` tag), `phase_reads` ;\n"
     "- `direct_phasing.cc` et `merge_phased_reads.cc` ;\n"
     "- canaux de methylation (`methylation_aware_phasing.cc`, `base_methylation`, `base_6ma`)."),
    ("HYBRID", "M5", "modeles : hybride PacBio+Illumina et MAS-Seq", ["make-examples", "call-variants", "parity"],
     "Deux BAM en entree, `sequencing_type` par read ; MAS-Seq pour l'isoforme."),

    # ---------------- M6
    ("M6", "M6", "meta(M6) : gate GIAB, performance, release", ["meta"],
     "Chapeau du jalon M6."),
    ("GIAB", "M6", "test : gate GIAB HG002 avec hap.py (WGS, WES, PacBio, ONT)", ["parity", "ci"],
     "Comme `bwa-mem4/.github/workflows/giab-gate.yml` : HG002 GIAB v4.2.1, `hap.py` sur les deux "
     "bras (oracle et port), precision, rappel et F1 SNP/INDEL. Un ecart, meme a la 4e decimale, "
     "est un bug tant qu'il n'est pas explique dans `DIVERGENCES.md`."),
    ("PERF", "M6", "perf : profil de bout en bout et objectif de debit", ["perf"],
     "Profil par etage (make_examples est le poste dominant en CPU chez l'amont). Objectifs "
     "chiffres a fixer apres M3 contre : Docker CPU, Docker GPU, Parabricks. Publier avec le "
     "materiel et le nombre de threads, jamais un ratio seul."),
    ("CHAIN", "M6", "integration : bwa-mem4 puis deepvariant-rs sans fichier intermediaire", ["perf"],
     "Pipeline FASTQ vers VCF avec bwa-mem4 (et le tri/markdup de picard-rs). Mesurer ce que "
     "coute le BAM intermediaire et si un flux direct vaut le travail."),
    ("RELEASE", "M6", "ci : release, crates.io, Homebrew, bioconda, Docker", ["ci"],
     "Reprendre `bwa-mem4/.github/workflows/release.yml` : binaires Linux x86_64/aarch64 et macOS, "
     "features GPU par binaire (`-metal`, `-cuda`, `-rocm`), image Docker, recette bioconda."),

    # ---------------- M7
    ("M7", "M7", "meta(M7) : DeepTrio, DeepSomatic, pangenome", ["meta"],
     "Chapeau du jalon M7. Commence quand M4 est ferme."),
    ("TRIO", "M7", "DeepTrio : make_examples multi-echantillon et modeles trio", ["make-examples", "call-variants"],
     "Source : `deeptrio/`, `variant_calling_multisample.cc`. Pileups empiles parent/enfant, "
     "modeles enfant et parent."),
    ("SOMATIC", "M7", "DeepSomatic : tumeur/normal et tumeur seule", ["make-examples", "call-variants"],
     "Source : `make_examples_somatic.py`, `Dockerfile.deepsomatic`. Canaux et postprocess somatiques."),
    ("PANGENOME", "M7", "Pangenome-aware DeepVariant (GBZ)", ["make-examples"],
     "Source : `make_examples_pangenome_aware_dv.py`, `load_gbz_into_shared_memory.py`, gbwt/gbwtgraph. "
     "Necessite un lecteur GBZ en Rust ou un binding."),
    ("TRAIN", "M7", "decision : l'entrainement et les labelers restent en Python/TensorFlow", ["decision"],
     "`train.py`, `labeler/` et le mode `training` de make_examples ne sont pas dans le perimetre. "
     "Le port consomme les modeles publies. A rouvrir seulement si un besoin reel apparait "
     "(modele maison sur un sequenceur non supporte)."),
]
