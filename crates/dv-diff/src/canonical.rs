//! Forme canonique d'un message protobuf : champs non ordonnes tries. Protobuf C++ serialise les
//! maps dans un ordre aleatoire par processus, et les champs repetes remplis en parcourant une map
//! heritent de cet ordre ; le reste suit l'ordre des numeros de champ.

use deepvariant_rs_io::wire::{put_varint, Cursor, Result};

/// Champs non ordonnes d'un message (maps, repetes remplis depuis une map) et sous-messages a
/// canonicaliser recursivement (pour une map : l'entree, valeur = champ 2).
pub struct Spec {
    pub unordered: &'static [u64],
    pub subs: &'static [(u64, &'static Spec)],
}

/// `nucleus.genomics.v1.VariantCall` : `info` = 2.
pub const VARIANT_CALL: Spec = Spec {
    unordered: &[2],
    subs: &[],
};
/// `nucleus.genomics.v1.Variant` : `info` = 10, `calls` = 11.
pub const VARIANT: Spec = Spec {
    unordered: &[10],
    subs: &[(11, &VARIANT_CALL)],
};
/// `DeepVariantCall.SupportingReads` et `SupportingReadsExt` : `read_names` / `read_infos` = 1,
/// remplis en parcourant la map `read_alleles` (`VariantCaller::AddSupportingReads`).
const SUPPORTING_READS: Spec = Spec {
    unordered: &[1],
    subs: &[],
};
const SUPPORTING_READS_ENTRY: Spec = Spec {
    unordered: &[],
    subs: &[(2, &SUPPORTING_READS)],
};
/// `learning.genomics.deepvariant.DeepVariantCall` : `variant` = 1, maps 2, 3, 5, 7, 10,
/// `ref_support` = 4 et `ref_support_ext` = 6 remplis depuis une map.
pub const DEEP_VARIANT_CALL: Spec = Spec {
    unordered: &[2, 3, 4, 5, 7, 10],
    subs: &[
        (1, &VARIANT),
        (2, &SUPPORTING_READS_ENTRY),
        (5, &SUPPORTING_READS_ENTRY),
        (6, &SUPPORTING_READS),
        (10, &SUPPORTING_READS_ENTRY),
    ],
};

pub fn canonical(buf: &[u8], spec: &Spec) -> Result<Vec<u8>> {
    // (numero, cle de tri, rang d'origine, octets du champ complet)
    let mut fields: Vec<(u64, Vec<u8>, usize, Vec<u8>)> = Vec::new();
    let mut c = Cursor(buf);
    loop {
        let before = c.0;
        let Some((field, wire)) = c.tag()? else { break };
        let raw = match spec.subs.iter().find(|(f, _)| *f == field) {
            Some((_, sub)) if wire == 2 => {
                let inner = canonical(c.len_delimited()?, sub)?;
                let mut out = Vec::new();
                put_varint(&mut out, field << 3 | 2);
                put_varint(&mut out, inner.len() as u64);
                out.extend_from_slice(&inner);
                out
            }
            _ => {
                c.skip(wire)?;
                before[..before.len() - c.0.len()].to_vec()
            }
        };
        // Champ ordonne : ordre d'origine garde. Non ordonne : tri sur les octets du champ.
        let key = if spec.unordered.contains(&field) {
            raw.clone()
        } else {
            Vec::new()
        };
        fields.push((field, key, fields.len(), raw));
    }
    fields.sort();
    Ok(fields.into_iter().flat_map(|f| f.3).collect())
}

#[cfg(test)]
mod tests {
    use super::*;
    use deepvariant_rs_io::wire::put_len;

    #[test]
    fn map_entries_are_sorted_repeated_order_kept() {
        let spec = Spec {
            unordered: &[10],
            subs: &[],
        };
        let mut a = Vec::new();
        put_len(&mut a, 7, b"x");
        put_len(&mut a, 7, b"y");
        put_len(&mut a, 10, b"k2");
        put_len(&mut a, 10, b"k1");
        let mut b = Vec::new();
        put_len(&mut b, 7, b"x");
        put_len(&mut b, 7, b"y");
        put_len(&mut b, 10, b"k1");
        put_len(&mut b, 10, b"k2");
        assert_eq!(canonical(&a, &spec).unwrap(), b);

        let mut swapped = Vec::new();
        put_len(&mut swapped, 7, b"y");
        put_len(&mut swapped, 7, b"x");
        assert_ne!(
            canonical(&swapped, &spec).unwrap(),
            canonical(&b, &spec).unwrap()[..6]
        );
    }
}
