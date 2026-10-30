#!/usr/bin/env python
"""Check docs/references.md bibliographic metadata against Crossref / the RFC Editor (needs internet).

Prints, for every DOI or RFC link found, the registered title/year/publisher so a human can compare them
with the entry. Standard library only; works on Linux and Windows. Nothing here proves a reference is
*relevant* or that TrustSR's novelty claims hold; it only catches wrong/non-existent citations.
"""
import json, pathlib, re, sys, urllib.error, urllib.request

TEXT = (pathlib.Path(__file__).resolve().parent.parent / "docs" / "references.md").read_text(encoding="utf-8")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "trustsr-reference-check/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.status, r.read()


def main() -> int:
    bad = 0
    for doi in sorted(set(re.findall(r"https://doi\.org/(10\.[^\s)]+?)(?=[.\s)]|$)", TEXT))):
        try:
            _, body = get(f"https://api.crossref.org/works/{doi}")
            m = json.loads(body)["message"]
            year = (m.get("issued", {}).get("date-parts") or [[None]])[0][0]
            print(f"OK   {doi}: {m.get('title', ['?'])[0]!r} ({year}) / {m.get('publisher')}")
        except (urllib.error.URLError, OSError, ValueError, KeyError) as exc:
            bad += 1; print(f"FAIL {doi}: {exc}")
    for url in sorted(set(re.findall(r"https://www\.rfc-editor\.org/rfc/rfc\d+", TEXT))):
        try:
            status, _ = get(url); print(f"OK   {url}: HTTP {status}")
        except (urllib.error.URLError, OSError) as exc:
            bad += 1; print(f"FAIL {url}: {exc}")
    print("\nCompare titles/years/authors with docs/references.md by hand; this tool does not do that for you.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
