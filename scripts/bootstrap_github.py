#!/usr/bin/env python3
"""Cree labels, jalons, issues, sous-issues et le projet GitHub depuis roadmap_data.py.

A lancer une seule fois sur un depot neuf : les numeros d'issue sont deduits de l'ordre de
creation (#1, #2, ...), ce qui suppose qu'aucune issue ni PR n'existe deja.
Usage : scripts/bootstrap_github.py IPNP-BIPN/deepvariant-rs [--roadmap-only]
"""
import json, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from roadmap_data import ISSUES, LABELS, M  # noqa: E402

REPO = sys.argv[1]
OWNER = REPO.split("/")[0]
NUM = {key: i + 1 for i, (key, *_) in enumerate(ISSUES)}


def gh(*args, capture=True):
    r = subprocess.run(["gh", *args], check=True, text=True, capture_output=capture)
    return r.stdout.strip() if capture else ""


def resolve(text):
    return re.sub(r"#([A-Z][A-Z0-9_]+)", lambda m: f"#{NUM[m.group(1)]}", text)


def write_roadmap():
    out = ["# Roadmap", "",
           "Une phase = un jalon GitHub. Cible d'acceptation : sorties **octet-identiques** a "
           "DeepVariant 1.10.0 pour make_examples et postprocess_variants, tolerance chiffree pour "
           "le modele (voir #%d). Ce fichier est genere par `scripts/bootstrap_github.py` au "
           "demarrage, puis tenu a la main comme journal des mesures, negatifs compris." % NUM["DECISION_TOL"],
           "", "| Jalon | But |", "|---|---|"]
    out += [f"| {t} | {resolve(d)} |" for t, d in M.values()]
    for mk, (title, _) in M.items():
        out += ["", f"## {title}", ""]
        out += [f"- #{NUM[k]} {t}" for k, m, t, *_ in ISSUES if m == mk and k != mk]
    Path(__file__).parent.parent.joinpath("ROADMAP.md").write_text("\n".join(out) + "\n")


write_roadmap()
if "--roadmap-only" in sys.argv:
    sys.exit(0)

for name, desc, color in LABELS:
    gh("label", "create", name, "-R", REPO, "-d", desc, "-c", color, "--force")

for title, desc in M.values():
    gh("api", f"repos/{REPO}/milestones", "-f", f"title={title}", "-f", f"description={resolve(desc)}")

ids = {}
for key, mk, title, labels, body in ISSUES:
    url = gh("issue", "create", "-R", REPO, "-t", title, "-b", resolve(body),
             "-m", M[mk][0], *sum((["-l", l] for l in labels), []))
    n = int(url.rsplit("/", 1)[1])
    assert n == NUM[key], f"{key}: attendu #{NUM[key]}, obtenu #{n} (depot pas neuf ?)"
    ids[key] = json.loads(gh("api", f"repos/{REPO}/issues/{n}"))["id"]
    print(n, title)

for key, mk, *_ in ISSUES:
    if key != mk:
        gh("api", f"repos/{REPO}/issues/{NUM[mk]}/sub_issues", "-F", f"sub_issue_id={ids[key]}")

proj = json.loads(gh("project", "create", "--owner", OWNER, "--title", "deepvariant-rs roadmap",
                     "--format", "json"))
gh("project", "link", str(proj["number"]), "--owner", OWNER, "--repo", REPO)
for key, *_ in ISSUES:
    gh("project", "item-add", str(proj["number"]), "--owner", OWNER,
       "--url", f"https://github.com/{REPO}/issues/{NUM[key]}")
print("project", proj["url"])
