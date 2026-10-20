//! Un TFRecord golden de l'oracle relu puis reecrit donne les memes octets (decompresses).

use std::io::Read;
use std::path::PathBuf;

use deepvariant_rs_io::tfrecord;

/// `DV_ORACLE_DIR`, sinon `reference/deepvariant` (fetch_oracle.sh) ou un `deepvariant` voisin
/// d'un dossier parent.
fn oracle_dir() -> Option<PathBuf> {
    if let Some(d) = std::env::var_os("DV_ORACLE_DIR") {
        return Some(d.into());
    }
    let here = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    here.ancestors()
        .flat_map(|a| [a.join("reference/deepvariant"), a.join("../deepvariant")])
        .find(|d| d.join("deepvariant/testdata").is_dir())
}

#[test]
fn golden_examples_round_trip() {
    let Some(dir) = oracle_dir() else {
        eprintln!("oracle absent (DV_ORACLE_DIR), test saute");
        return;
    };
    let testdata = dir.join("deepvariant/testdata");
    for name in [
        "golden.calling_examples.tfrecord.gz",
        "golden.training_examples.tfrecord.gz",
        "golden.calling_candidates.tfrecord.gz",
    ] {
        let path = testdata.join(name);
        let mut raw = Vec::new();
        flate2::read::MultiGzDecoder::new(std::fs::File::open(&path).unwrap())
            .read_to_end(&mut raw)
            .unwrap();

        let mut w = tfrecord::Writer::new(Vec::new());
        let mut n = 0;
        for rec in tfrecord::open(&path).unwrap() {
            w.write_record(&rec.unwrap()).unwrap();
            n += 1;
        }
        assert!(n > 0, "{name} vide");
        assert!(w.into_inner() == raw, "{name} : octets differents");
    }
}

#[test]
fn gzip_create_then_open() {
    let path = std::env::temp_dir().join(format!("dv-io-{}.tfrecord.gz", std::process::id()));
    let mut w = tfrecord::create(&path).unwrap();
    w.write_record(b"x").unwrap();
    w.write_record(b"yz").unwrap();
    w.finish().unwrap();
    let recs: Vec<_> = tfrecord::open(&path).unwrap().map(Result::unwrap).collect();
    std::fs::remove_file(&path).unwrap();
    assert_eq!(recs, vec![b"x".to_vec(), b"yz".to_vec()]);
}
