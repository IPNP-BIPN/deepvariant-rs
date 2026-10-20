//! `tf.Example` encode et decode a la main, ordre des cles conserve : protobuf C++ serialise la
//! `map<string, Feature>` dans l'ordre de sa table de hachage, qu'on doit pouvoir reproduire.

use crate::wire::{put_len, put_varint, Cursor, DecodeError, Result};

#[derive(Clone, Debug, PartialEq)]
pub enum Feature {
    Bytes(Vec<Vec<u8>>),
    Float(Vec<f32>),
    Int64(Vec<i64>),
}

#[derive(Clone, Debug, Default, PartialEq)]
pub struct Example {
    /// Dans l'ordre du flux.
    pub features: Vec<(String, Feature)>,
}

fn decode_feature(buf: &[u8]) -> Result<Feature> {
    let mut c = Cursor(buf);
    // Feature vide (oneof non renseigne) : on la lit comme une liste d'octets vide.
    let mut out = Feature::Bytes(Vec::new());
    while let Some((field, wire)) = c.tag()? {
        if wire != 2 || !(1..=3).contains(&field) {
            c.skip(wire)?;
            continue;
        }
        let mut list = Cursor(c.len_delimited()?);
        out = match field {
            1 => {
                let mut v = Vec::new();
                while let Some((f, w)) = list.tag()? {
                    match (f, w) {
                        (1, 2) => v.push(list.len_delimited()?.to_vec()),
                        _ => list.skip(w)?,
                    }
                }
                Feature::Bytes(v)
            }
            2 => {
                let mut v = Vec::new();
                while let Some((f, w)) = list.tag()? {
                    match (f, w) {
                        (1, 2) => {
                            let packed = list.len_delimited()?;
                            let (chunks, rest) = packed.as_chunks::<4>();
                            if !rest.is_empty() {
                                return Err(DecodeError("float packe tronque"));
                            }
                            v.extend(chunks.iter().map(|&b| f32::from_le_bytes(b)));
                        }
                        (1, 5) => v.push(f32::from_le_bytes(list.take(4)?.try_into().unwrap())),
                        _ => list.skip(w)?,
                    }
                }
                Feature::Float(v)
            }
            _ => {
                let mut v = Vec::new();
                while let Some((f, w)) = list.tag()? {
                    match (f, w) {
                        (1, 2) => {
                            let mut packed = Cursor(list.len_delimited()?);
                            while !packed.0.is_empty() {
                                v.push(packed.varint()? as i64);
                            }
                        }
                        (1, 0) => v.push(list.varint()? as i64),
                        _ => list.skip(w)?,
                    }
                }
                Feature::Int64(v)
            }
        };
    }
    Ok(out)
}

impl Example {
    pub fn decode(buf: &[u8]) -> Result<Self> {
        let mut ex = Example::default();
        let mut c = Cursor(buf);
        while let Some((field, wire)) = c.tag()? {
            if (field, wire) != (1, 2) {
                c.skip(wire)?;
                continue;
            }
            let mut features = Cursor(c.len_delimited()?);
            while let Some((field, wire)) = features.tag()? {
                if (field, wire) != (1, 2) {
                    features.skip(wire)?;
                    continue;
                }
                let mut entry = Cursor(features.len_delimited()?);
                let (mut key, mut value) = (String::new(), Feature::Bytes(Vec::new()));
                while let Some((f, w)) = entry.tag()? {
                    match (f, w) {
                        (1, 2) => {
                            key = String::from_utf8(entry.len_delimited()?.to_vec())
                                .map_err(|_| DecodeError("cle non UTF-8"))?
                        }
                        (2, 2) => value = decode_feature(entry.len_delimited()?)?,
                        _ => entry.skip(w)?,
                    }
                }
                ex.features.push((key, value));
            }
        }
        Ok(ex)
    }

    /// Serialisation de protobuf C++ : champs dans l'ordre des numeros, repetes numeriques packes.
    pub fn encode(&self) -> Vec<u8> {
        let mut features = Vec::new();
        for (key, value) in &self.features {
            let mut list = Vec::new();
            let field = match value {
                Feature::Bytes(v) => {
                    for b in v {
                        put_len(&mut list, 1, b);
                    }
                    1
                }
                Feature::Float(v) => {
                    if !v.is_empty() {
                        let packed: Vec<u8> = v.iter().flat_map(|x| x.to_le_bytes()).collect();
                        put_len(&mut list, 1, &packed);
                    }
                    2
                }
                Feature::Int64(v) => {
                    if !v.is_empty() {
                        let mut packed = Vec::new();
                        for &x in v {
                            put_varint(&mut packed, x as u64);
                        }
                        put_len(&mut list, 1, &packed);
                    }
                    3
                }
            };
            let mut feature = Vec::new();
            put_len(&mut feature, field, &list);
            let mut entry = Vec::new();
            put_len(&mut entry, 1, key.as_bytes());
            put_len(&mut entry, 2, &feature);
            put_len(&mut features, 1, &entry);
        }
        let mut out = Vec::new();
        put_len(&mut out, 1, &features);
        out
    }

    pub fn get(&self, key: &str) -> Option<&Feature> {
        self.features.iter().find(|(k, _)| k == key).map(|(_, v)| v)
    }

    /// Premier element d'une feature d'octets, comme `dv_utils.example_*`.
    pub fn bytes(&self, key: &str) -> Option<&[u8]> {
        match self.get(key)? {
            Feature::Bytes(v) => v.first().map(Vec::as_slice),
            _ => None,
        }
    }

    pub fn int64s(&self, key: &str) -> Option<&[i64]> {
        match self.get(key)? {
            Feature::Int64(v) => Some(v),
            _ => None,
        }
    }

    pub fn locus(&self) -> Option<&[u8]> {
        self.bytes("locus")
    }
    pub fn variant_encoded(&self) -> Option<&[u8]> {
        self.bytes("variant/encoded")
    }
    pub fn alt_allele_indices_encoded(&self) -> Option<&[u8]> {
        self.bytes("alt_allele_indices/encoded")
    }
    pub fn image_encoded(&self) -> Option<&[u8]> {
        self.bytes("image/encoded")
    }
    pub fn image_shape(&self) -> Option<&[i64]> {
        self.int64s("image/shape")
    }
    pub fn sequencing_type(&self) -> Option<i64> {
        self.int64s("sequencing_type")?.first().copied()
    }
    pub fn label(&self) -> Option<i64> {
        self.int64s("label")?.first().copied()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn round_trip_all_kinds() {
        let ex = Example {
            features: vec![
                ("b".into(), Feature::Bytes(vec![b"xy".to_vec(), vec![]])),
                ("f".into(), Feature::Float(vec![1.5, -0.0])),
                ("i".into(), Feature::Int64(vec![-1, 0, 300])),
                ("e".into(), Feature::Int64(vec![])),
            ],
        };
        let bytes = ex.encode();
        assert_eq!(Example::decode(&bytes).unwrap(), ex);
        assert_eq!(ex.int64s("i"), Some(&[-1, 0, 300][..]));
    }

    #[test]
    fn unpacked_int64_is_accepted() {
        // Feature{int64_list{value: 5, value: 6}} non packe, puis encapsule.
        let list = [0x08, 5, 0x08, 6];
        let mut feature = Vec::new();
        put_len(&mut feature, 3, &list);
        assert_eq!(
            decode_feature(&feature).unwrap(),
            Feature::Int64(vec![5, 6])
        );
    }

    #[test]
    fn truncated_is_an_error() {
        let bytes = Example {
            features: vec![("k".into(), Feature::Int64(vec![1]))],
        }
        .encode();
        assert!(Example::decode(&bytes[..bytes.len() - 1]).is_err());
    }
}
