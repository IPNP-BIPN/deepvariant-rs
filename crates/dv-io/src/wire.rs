//! Format filaire protobuf, le strict necessaire pour tf.Example et les diffs.

use std::fmt;

#[derive(Debug, PartialEq)]
pub struct DecodeError(pub &'static str);

impl fmt::Display for DecodeError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "protobuf : {}", self.0)
    }
}

impl std::error::Error for DecodeError {}

pub type Result<T> = std::result::Result<T, DecodeError>;

pub struct Cursor<'a>(pub &'a [u8]);

impl<'a> Cursor<'a> {
    pub fn varint(&mut self) -> Result<u64> {
        let mut v = 0u64;
        for shift in (0..64).step_by(7) {
            let (&b, rest) = self.0.split_first().ok_or(DecodeError("varint tronque"))?;
            self.0 = rest;
            v |= u64::from(b & 0x7f) << shift;
            if b < 0x80 {
                return Ok(v);
            }
        }
        Err(DecodeError("varint trop long"))
    }

    pub fn take(&mut self, n: usize) -> Result<&'a [u8]> {
        if n > self.0.len() {
            return Err(DecodeError("champ tronque"));
        }
        let (head, rest) = self.0.split_at(n);
        self.0 = rest;
        Ok(head)
    }

    pub fn len_delimited(&mut self) -> Result<&'a [u8]> {
        let n = usize::try_from(self.varint()?).map_err(|_| DecodeError("longueur"))?;
        self.take(n)
    }

    /// `(numero, type)` du prochain champ, `None` en fin de message.
    pub fn tag(&mut self) -> Result<Option<(u64, u8)>> {
        if self.0.is_empty() {
            return Ok(None);
        }
        let t = self.varint()?;
        Ok(Some((t >> 3, (t & 7) as u8)))
    }

    pub fn skip(&mut self, wire: u8) -> Result<()> {
        match wire {
            0 => self.varint().map(drop),
            1 => self.take(8).map(drop),
            2 => self.len_delimited().map(drop),
            5 => self.take(4).map(drop),
            _ => Err(DecodeError("type de champ inconnu")),
        }
    }
}

pub fn put_varint(out: &mut Vec<u8>, mut v: u64) {
    while v >= 0x80 {
        out.push(v as u8 | 0x80);
        v >>= 7;
    }
    out.push(v as u8);
}

pub fn put_len(out: &mut Vec<u8>, field: u64, data: &[u8]) {
    put_varint(out, field << 3 | 2);
    put_varint(out, data.len() as u64);
    out.extend_from_slice(data);
}
