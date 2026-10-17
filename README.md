# deepvariant-rs

Reimplementation native en Rust de [DeepVariant](https://github.com/google/deepvariant) 1.10.0,
avec inference sur **CPU, Apple Silicon (Metal), NVIDIA (CUDA) et AMD (ROCm)** depuis un seul code
de modele.

Meme principe que [bwa-mem4](https://github.com/IPNP-BIPN/bwa-mem4) et
[gatk-rs](https://github.com/IPNP-BIPN/gatk-rs) : le critere d'acceptation est l'oracle, pas
"des resultats equivalents".

| Etage | Critere |
|---|---|
| `make_examples` | chaque `tf.Example` identique **octet par octet** a DeepVariant 1.10.0 |
| `call_variants` | probabilites dans une tolerance chiffree, genotypes identiques (voir ROADMAP) |
| `postprocess_variants` | VCF et gVCF **octet-identiques** |
| GPU | VCF identique au chemin CPU, barriere ecrite avant le premier noyau |

Pas d'officiel : ce n'est pas un produit Google. Les poids des modeles ne sont pas redistribues ;
ils sont convertis localement depuis les fichiers publies par Google.

## Statut

Squelette. Rien n'est porte. Le plan, jalon par jalon, est dans [ROADMAP.md](ROADMAP.md) et dans le
[projet GitHub](https://github.com/orgs/IPNP-BIPN/projects).

## Organisation

```
crates/
  dv-core          types, constantes, protos
  dv-io            BAM/CRAM/FASTA/VCF, TFRecord et tf.Example
  dv-allele-counter, dv-caller, dv-realigner, dv-pileup, dv-make-examples
  dv-model         InceptionV3, small model, chargement des poids
  dv-gpu           selection du backend : cpu | metal | cuda | rocm
  dv-postprocess   CVO vers VCF/gVCF
  dv-diff          comparaison a l'oracle
  dv-cli           binaire deepvariant-rs
```

## Developper

```bash
./scripts/check.sh          # fmt, clippy -D warnings, tests
./scripts/fetch_oracle.sh   # sources et image Docker DeepVariant 1.10.0
```

## Licence

BSD-3-Clause, comme DeepVariant, dont ce port est une oeuvre derivee (voir [LICENSE](LICENSE)).
