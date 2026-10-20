#!/usr/bin/env bash
# #60 : lance 3 fois la commande golden "calling" de create_golden.sh dans l'image oracle, puis
# compare les sorties avec dv-diff. Prerequis : scripts/fetch_oracle.sh.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=work/oracle60
mkdir -p "$OUT"
docker run --rm --platform linux/amd64 \
  -v "$PWD/reference/deepvariant/deepvariant/testdata:/testdata:ro" -v "$PWD/$OUT:/out" \
  google/deepvariant:1.10.0 bash -c '
set -euo pipefail
T=/testdata
for i in 1 2 3; do
  /opt/deepvariant/bin/make_examples --mode calling \
    --ref "$T/input/ucsc.hg19.chr20.unittest.fasta.gz" \
    --reads "$T/input/NA12878_S1.chr20.10_10p1mb.bam" \
    --regions chr20:10,000,000-10,010,000 \
    --proposed_variants "$T/input/test_nist.b37_chr20_100kbp_at_10mb.vcf.gz" \
    --confident_regions "$T/input/test_nist.b37_chr20_100kbp_at_10mb.bed" \
    --candidates "/out/candidates.$i.tfrecord.gz" --examples "/out/examples.$i.tfrecord.gz" \
    --gvcf "/out/gvcf.$i.tfrecord.gz" \
    --channel_list=read_base,base_quality,mapping_quality,strand,read_supports_variant,base_differs_from_ref,insert_size \
    --deterministic_serialization > "/out/run.$i.log" 2>&1
done'
cargo build -q -p deepvariant-rs-diff
D=target/debug/dv-diff
G=reference/deepvariant/deepvariant/testdata
for i in 2 3; do
  "$D" examples "$OUT/examples.1.tfrecord.gz" "$OUT/examples.$i.tfrecord.gz"
  "$D" candidates "$OUT/candidates.1.tfrecord.gz" "$OUT/candidates.$i.tfrecord.gz"
  cmp <(gunzip -c "$OUT/gvcf.1.tfrecord.gz") <(gunzip -c "$OUT/gvcf.$i.tfrecord.gz") && echo "gvcf 1 = $i"
done
"$D" examples "$OUT/examples.1.tfrecord.gz" "$G/golden.calling_examples.tfrecord.gz"
"$D" candidates "$OUT/candidates.1.tfrecord.gz" "$G/golden.calling_candidates.tfrecord.gz"
