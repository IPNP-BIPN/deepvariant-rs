//! Outils de comparaison a l'oracle : exemples, CVO, VCF.

pub mod canonical;

use std::io;
use std::path::Path;

use deepvariant_rs_io::example::{Example, Feature};
use deepvariant_rs_io::tfrecord;

#[derive(Debug, Default, PartialEq)]
pub struct ExamplesReport {
    pub left: usize,
    pub right: usize,
    /// Paires identiques octet par octet.
    pub raw_identical: usize,
    /// Paires aux memes features une fois triees par cle (l'ordre de la map est aleatoire chez
    /// l'oracle, voir ROADMAP.md).
    pub feature_identical: usize,
    /// Premiere paire differente en features : (indice, cle ou "<cles>").
    pub first_mismatch: Option<(usize, String)>,
}

/// Cles triees, `variant/encoded` canonicalise : ce que l'oracle fixe vraiment.
fn sorted(mut ex: Example) -> io::Result<Example> {
    ex.features.sort_by(|a, b| a.0.cmp(&b.0));
    for (key, value) in &mut ex.features {
        if let ("variant/encoded", Feature::Bytes(v)) = (key.as_str(), value) {
            for b in v {
                *b = canonical::canonical(b, &canonical::VARIANT).map_err(io::Error::other)?;
            }
        }
    }
    Ok(ex)
}

/// Compare deux TFRecord d'exemples enregistrement par enregistrement, dans l'ordre.
pub fn examples(left: &Path, right: &Path) -> io::Result<ExamplesReport> {
    let read = |p: &Path| -> io::Result<Vec<Vec<u8>>> {
        tfrecord::open(p)?
            .collect::<Result<_, _>>()
            .map_err(io::Error::other)
    };
    let (l, r) = (read(left)?, read(right)?);
    let mut rep = ExamplesReport {
        left: l.len(),
        right: r.len(),
        ..Default::default()
    };
    for (i, (a, b)) in l.iter().zip(&r).enumerate() {
        if a == b {
            rep.raw_identical += 1;
            rep.feature_identical += 1;
            continue;
        }
        let ea = sorted(Example::decode(a).map_err(io::Error::other)?)?;
        let eb = sorted(Example::decode(b).map_err(io::Error::other)?)?;
        if ea == eb {
            rep.feature_identical += 1;
        } else if rep.first_mismatch.is_none() {
            let key = ea
                .features
                .iter()
                .zip(&eb.features)
                .find(|(x, y)| x != y)
                .map_or("<cles>".to_string(), |(x, y)| {
                    if x.0 == y.0 {
                        x.0.clone()
                    } else {
                        "<cles>".to_string()
                    }
                });
            rep.first_mismatch = Some((i, key));
        }
    }
    Ok(rep)
}

/// Compare deux TFRecord de `DeepVariantCall` (sortie `--candidates`) modulo les champs non ordonnes.
/// Renvoie (gauche, droite, octets identiques, canoniques identiques, premiere divergence).
pub fn candidates(
    left: &Path,
    right: &Path,
) -> io::Result<(usize, usize, usize, usize, Option<usize>)> {
    let read = |p: &Path| -> io::Result<Vec<Vec<u8>>> {
        tfrecord::open(p)?
            .collect::<Result<_, _>>()
            .map_err(io::Error::other)
    };
    let (l, r) = (read(left)?, read(right)?);
    let (mut raw, mut canon, mut first) = (0, 0, None);
    for (i, (a, b)) in l.iter().zip(&r).enumerate() {
        raw += usize::from(a == b);
        let ca =
            canonical::canonical(a, &canonical::DEEP_VARIANT_CALL).map_err(io::Error::other)?;
        let cb =
            canonical::canonical(b, &canonical::DEEP_VARIANT_CALL).map_err(io::Error::other)?;
        if ca == cb {
            canon += 1;
        } else {
            first.get_or_insert(i);
        }
    }
    Ok((l.len(), r.len(), raw, canon, first))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn write(path: &Path, exs: &[Example]) {
        let mut w = tfrecord::create(path).unwrap();
        for e in exs {
            w.write_record(&e.encode()).unwrap();
        }
        w.finish().unwrap();
    }

    #[test]
    fn key_order_is_ignored_values_are_not() {
        let a = Example {
            features: vec![
                ("a".into(), Feature::Int64(vec![1])),
                ("b".into(), Feature::Int64(vec![2])),
            ],
        };
        let mut swapped = a.clone();
        swapped.features.reverse();
        let mut changed = a.clone();
        changed.features[1].1 = Feature::Int64(vec![3]);

        let dir = std::env::temp_dir();
        let pid = std::process::id();
        let (p1, p2) = (
            dir.join(format!("dvd-{pid}-1")),
            dir.join(format!("dvd-{pid}-2")),
        );
        write(&p1, &[a.clone(), a.clone(), a]);
        write(&p2, &[swapped.clone(), changed, swapped]);
        let rep = examples(&p1, &p2).unwrap();
        std::fs::remove_file(&p1).unwrap();
        std::fs::remove_file(&p2).unwrap();
        assert_eq!(
            rep,
            ExamplesReport {
                left: 3,
                right: 3,
                raw_identical: 0,
                feature_identical: 2,
                first_mismatch: Some((1, "b".into())),
            }
        );
    }
}
