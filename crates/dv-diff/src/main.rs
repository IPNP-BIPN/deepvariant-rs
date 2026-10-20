//! `dv-diff examples|candidates A B` : compare deux TFRecord d'exemples ou de candidats. Code de sortie 1 si les features
//! different.

use std::path::Path;
use std::process::ExitCode;

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    let [_, cmd, a, b] = args.as_slice() else {
        eprintln!("usage : dv-diff examples|candidates A B");
        return ExitCode::from(2);
    };
    if cmd == "candidates" {
        return match deepvariant_rs_diff::candidates(Path::new(a), Path::new(b)) {
            Ok((l, r, raw, canon, first)) => {
                println!(
                    "candidats {l} / {r}, octets identiques {raw}, canoniques identiques {canon}"
                );
                if let Some(i) = first {
                    println!("premiere divergence : candidat {i}");
                }
                ExitCode::from(u8::from(l != r || canon != l))
            }
            Err(e) => {
                eprintln!("dv-diff : {e}");
                ExitCode::from(2)
            }
        };
    }
    if cmd != "examples" {
        eprintln!("sous-commande inconnue : {cmd}");
        return ExitCode::from(2);
    }
    match deepvariant_rs_diff::examples(Path::new(a), Path::new(b)) {
        Ok(r) => {
            println!(
                "exemples {} / {}, octets identiques {}, features identiques {}",
                r.left, r.right, r.raw_identical, r.feature_identical
            );
            if let Some((i, key)) = &r.first_mismatch {
                println!("premiere divergence : exemple {i}, feature {key}");
            }
            let ok = r.left == r.right && r.feature_identical == r.left;
            ExitCode::from(u8::from(!ok))
        }
        Err(e) => {
            eprintln!("dv-diff : {e}");
            ExitCode::from(2)
        }
    }
}
