//! Cadrage TFRecord : `u64` longueur LE, CRC32C masque de la longueur, donnees, CRC32C masque des
//! donnees. Voir `tensorflow/core/lib/io/record_writer.cc`.

use std::fmt;
use std::fs::File;
use std::io::{self, BufReader, BufWriter, Read, Write};
use std::path::Path;

use flate2::read::MultiGzDecoder;
use flate2::write::GzEncoder;
use flate2::Compression;

const MASK_DELTA: u32 = 0xa282_ead8;

/// CRC32C masque, comme `tensorflow::crc32c::Mask`.
pub fn masked_crc(data: &[u8]) -> u32 {
    let crc = crc32c::crc32c(data);
    (crc.rotate_right(15)).wrapping_add(MASK_DELTA)
}

#[derive(Debug)]
pub enum Error {
    Io(io::Error),
    /// Fin de fichier au milieu d'un enregistrement.
    Truncated,
    LengthCrc {
        expected: u32,
        found: u32,
    },
    DataCrc {
        expected: u32,
        found: u32,
    },
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Error::Io(e) => write!(f, "tfrecord : {e}"),
            Error::Truncated => write!(f, "tfrecord : enregistrement tronque"),
            Error::LengthCrc { expected, found } => {
                write!(
                    f,
                    "tfrecord : CRC de longueur {found:#010x}, attendu {expected:#010x}"
                )
            }
            Error::DataCrc { expected, found } => {
                write!(
                    f,
                    "tfrecord : CRC de donnees {found:#010x}, attendu {expected:#010x}"
                )
            }
        }
    }
}

impl std::error::Error for Error {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Error::Io(e) => Some(e),
            _ => None,
        }
    }
}

impl From<io::Error> for Error {
    fn from(e: io::Error) -> Self {
        if e.kind() == io::ErrorKind::UnexpectedEof {
            Error::Truncated
        } else {
            Error::Io(e)
        }
    }
}

/// Lecteur en flux : un enregistrement a la fois, memoire bornee par le plus gros enregistrement.
pub struct Reader<R> {
    inner: R,
}

impl<R: Read> Reader<R> {
    pub fn new(inner: R) -> Self {
        Self { inner }
    }

    /// Lit le prochain enregistrement dans `buf`. `Ok(false)` en fin de fichier propre.
    pub fn read_into(&mut self, buf: &mut Vec<u8>) -> Result<bool, Error> {
        let mut header = [0u8; 12];
        // Fin propre seulement si zero octet lu avant l'en-tete.
        let mut got = 0;
        while got < header.len() {
            match self.inner.read(&mut header[got..]) {
                Ok(0) if got == 0 => return Ok(false),
                Ok(0) => return Err(Error::Truncated),
                Ok(n) => got += n,
                Err(e) if e.kind() == io::ErrorKind::Interrupted => {}
                Err(e) => return Err(e.into()),
            }
        }
        let len_bytes: [u8; 8] = header[..8].try_into().unwrap();
        let expected = u32::from_le_bytes(header[8..].try_into().unwrap());
        let found = masked_crc(&len_bytes);
        if found != expected {
            return Err(Error::LengthCrc { expected, found });
        }
        let len = usize::try_from(u64::from_le_bytes(len_bytes)).map_err(|_| Error::Truncated)?;
        buf.clear();
        buf.resize(len, 0);
        self.inner.read_exact(buf)?;
        let mut crc = [0u8; 4];
        self.inner.read_exact(&mut crc)?;
        let expected = u32::from_le_bytes(crc);
        let found = masked_crc(buf);
        if found != expected {
            return Err(Error::DataCrc { expected, found });
        }
        Ok(true)
    }
}

impl<R: Read> Iterator for Reader<R> {
    type Item = Result<Vec<u8>, Error>;

    fn next(&mut self) -> Option<Self::Item> {
        let mut buf = Vec::new();
        match self.read_into(&mut buf) {
            Ok(true) => Some(Ok(buf)),
            Ok(false) => None,
            Err(e) => Some(Err(e)),
        }
    }
}

pub struct Writer<W> {
    inner: W,
}

impl<W: Write> Writer<W> {
    pub fn new(inner: W) -> Self {
        Self { inner }
    }

    pub fn write_record(&mut self, data: &[u8]) -> io::Result<()> {
        let len = (data.len() as u64).to_le_bytes();
        self.inner.write_all(&len)?;
        self.inner.write_all(&masked_crc(&len).to_le_bytes())?;
        self.inner.write_all(data)?;
        self.inner.write_all(&masked_crc(data).to_le_bytes())
    }

    pub fn into_inner(self) -> W {
        self.inner
    }
}

fn is_gz(path: &Path) -> bool {
    path.extension().is_some_and(|e| e == "gz")
}

/// Ouvre un TFRecord, decompresse en flux si le chemin finit par `.gz` (convention de DeepVariant).
pub fn open(path: impl AsRef<Path>) -> io::Result<Reader<Box<dyn Read>>> {
    let path = path.as_ref();
    let file = File::open(path)?;
    // Un .gz de 0 octet vaut zero enregistrement pour TensorFlow (golden.calling_examples_empty).
    let empty = file.metadata()?.len() == 0;
    let file = BufReader::new(file);
    let inner: Box<dyn Read> = if is_gz(path) && !empty {
        Box::new(BufReader::new(MultiGzDecoder::new(file)))
    } else {
        Box::new(file)
    };
    Ok(Reader::new(inner))
}

/// Cree un TFRecord, compresse en gzip si le chemin finit par `.gz`. Appeler `finish` pour clore
/// le flux gzip proprement.
pub fn create(path: impl AsRef<Path>) -> io::Result<Writer<Box<dyn FinishWrite>>> {
    let path = path.as_ref();
    let file = BufWriter::new(File::create(path)?);
    let inner: Box<dyn FinishWrite> = if is_gz(path) {
        Box::new(GzEncoder::new(file, Compression::default()))
    } else {
        Box::new(file)
    };
    Ok(Writer::new(inner))
}

/// `Write` qui sait se clore (pied gzip, vidage du tampon).
pub trait FinishWrite: Write {
    fn finish(self: Box<Self>) -> io::Result<()>;
}

impl<W: Write> FinishWrite for BufWriter<W> {
    fn finish(mut self: Box<Self>) -> io::Result<()> {
        self.flush()
    }
}

impl<W: Write> FinishWrite for GzEncoder<W> {
    fn finish(self: Box<Self>) -> io::Result<()> {
        (*self).finish()?.flush()
    }
}

impl Writer<Box<dyn FinishWrite>> {
    pub fn finish(self) -> io::Result<()> {
        self.inner.finish()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn masked_crc_of_empty_is_delta() {
        // crc32c("") = 0, donc le masque vaut le delta seul.
        assert_eq!(masked_crc(b""), MASK_DELTA);
    }

    #[test]
    fn round_trip_and_errors() {
        let mut w = Writer::new(Vec::new());
        w.write_record(b"abc").unwrap();
        w.write_record(&[7u8; 1000]).unwrap();
        let bytes = w.into_inner();

        let recs: Vec<_> = Reader::new(&bytes[..]).collect::<Result<_, _>>().unwrap();
        assert_eq!(recs, vec![b"abc".to_vec(), vec![7u8; 1000]]);

        let mut bad = bytes.clone();
        bad[13] ^= 1;
        assert!(matches!(
            Reader::new(&bad[..]).next(),
            Some(Err(Error::DataCrc { .. }))
        ));
        bad[0] ^= 1;
        assert!(matches!(
            Reader::new(&bad[..]).next(),
            Some(Err(Error::LengthCrc { .. }))
        ));
        assert!(matches!(
            Reader::new(&bytes[..bytes.len() - 1]).nth(1),
            Some(Err(Error::Truncated))
        ));
    }
}
