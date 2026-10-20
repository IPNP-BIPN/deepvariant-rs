//! Tous les exemples golden de l'oracle se decodent et se reencodent a l'identique.

use std::collections::BTreeMap;
use std::path::PathBuf;

use deepvariant_rs_io::{example::Example, tfrecord};

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
fn golden_examples_decode_and_reencode() {
    let Some(dir) = oracle_dir() else {
        eprintln!("oracle absent (DV_ORACLE_DIR), test saute");
        return;
    };
    let mut files: Vec<_> = std::fs::read_dir(dir.join("deepvariant/testdata"))
        .unwrap()
        .map(|e| e.unwrap().path())
        .filter(|p| {
            let n = p.file_name().unwrap().to_string_lossy();
            n.contains("examples") && n.ends_with(".tfrecord.gz")
        })
        .collect();
    files.sort();
    assert!(!files.is_empty());
    // Ordres de cles observes, pour #60 : un seul ordre par fichier ou plusieurs ?
    let mut orders: BTreeMap<Vec<String>, usize> = BTreeMap::new();
    let mut total = 0;
    for path in &files {
        for rec in tfrecord::open(path).unwrap() {
            let rec = rec.unwrap();
            let ex = Example::decode(&rec).unwrap_or_else(|e| panic!("{path:?} : {e}"));
            assert!(ex.encode() == rec, "{path:?} : reencodage different");
            assert!(ex.image_encoded().is_some() && ex.image_shape().is_some());
            *orders
                .entry(ex.features.iter().map(|(k, _)| k.clone()).collect())
                .or_default() += 1;
            total += 1;
        }
    }
    eprintln!("{total} exemples dans {} fichiers", files.len());
    for (order, n) in &orders {
        eprintln!("{n:6} {order:?}");
    }
}
