#!/usr/bin/env python3
"""
Download 50+ quantum cryptography research papers from arXiv.
Covers: QKD, PQC, quantum attacks, lattice crypto, BB84, E91, Shor's, Grover's.
Output: /mnt/deepa/quantum/datasets/papers/cryptography/
"""
import arxiv
import json
import time
import pathlib
import hashlib
from datetime import datetime

PAPER_DIR = pathlib.Path("/mnt/deepa/quantum/datasets/papers/cryptography")
PAPER_DIR.mkdir(parents=True, exist_ok=True)

# Search queries covering all 24 QC scenarios
QUERIES = [
    # QKD protocols
    ("QKD BB84 quantum key distribution security", 8),
    ("E91 Ekert entanglement quantum cryptography Bell inequality", 5),
    ("measurement device independent MDI-QKD", 4),
    ("twin field TF-QKD continuous variable CV-QKD", 4),
    # PQC
    ("CRYSTALS-Kyber ML-KEM lattice post-quantum cryptography", 6),
    ("CRYSTALS-Dilithium ML-DSA digital signature lattice", 5),
    ("SPHINCS+ hash-based signature post-quantum", 4),
    ("NTRU Falcon BIKE post-quantum lattice code", 4),
    # Attacks
    ("Shor algorithm factoring RSA quantum computer", 5),
    ("Grover search algorithm symmetric cryptography AES", 4),
    ("harvest now decrypt later quantum threat timeline", 3),
    # General
    ("post-quantum cryptography migration NIST FIPS 203 204 205", 5),
    ("quantum random number generator QRNG photon", 3),
]

client = arxiv.Client(page_size=10, delay_seconds=2, num_retries=3)
manifest = []
downloaded = 0
seen_ids = set()

for query, max_results in QUERIES:
    print(f"\nSearching: {query[:60]}... (max {max_results})")
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )

    for paper in client.results(search):
        raw_id = paper.entry_id.split("/")[-1]
        if raw_id in seen_ids:
            print(f"  [DUP]  {paper.title[:50]}")
            continue
        seen_ids.add(raw_id)

        arxiv_id = raw_id.replace("v", "_v")
        safe_title = "".join(
            c if c.isalnum() or c in " -_" else "_" for c in paper.title[:60]
        )
        filename = f"{arxiv_id}_{safe_title}.pdf".replace(" ", "_")
        filepath = PAPER_DIR / filename

        if filepath.exists():
            print(f"  [SKIP] {paper.title[:50]}")
        else:
            try:
                paper.download_pdf(dirpath=str(PAPER_DIR), filename=filename)
                print(f"  [OK]   {paper.title[:50]}")
                downloaded += 1
                time.sleep(1)
            except Exception as e:
                print(f"  [FAIL] {e}")
                filepath = PAPER_DIR / filename  # may not exist

        manifest.append({
            "arxiv_id": raw_id,
            "title": paper.title,
            "authors": [a.name for a in paper.authors[:3]],
            "year": paper.published.year,
            "abstract": paper.summary[:500],
            "categories": paper.categories,
            "pdf_path": str(filepath),
            "query_category": query.split()[0],
            "downloaded": filepath.exists(),
        })

# Save manifest
manifest_path = PAPER_DIR / "manifest.json"
with open(manifest_path, "w") as f:
    json.dump(manifest, f, indent=2, default=str)

actually_downloaded = sum(1 for m in manifest if m["downloaded"])
print(f"\n[DONE] Downloaded {downloaded} new papers this run")
print(f"[DONE] Total on disk: {actually_downloaded}")
print(f"[DONE] Total in manifest: {len(manifest)}")
print(f"[DONE] Directory: {PAPER_DIR}")
