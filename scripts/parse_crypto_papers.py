#!/usr/bin/env python3
"""
Parse downloaded quantum cryptography PDFs.
Extracts: title, authors, abstract, algorithms, sections, figures, scenario mapping.
Output: /mnt/deepa/quantum/datasets/papers/cryptography/parsed_papers.json
"""
import json
import pathlib
import re
import sys

try:
    import fitz  # PyMuPDF
except ImportError:
    print("PyMuPDF not installed. Run: pip3 install PyMuPDF")
    sys.exit(1)

PAPER_DIR = pathlib.Path("/mnt/deepa/quantum/datasets/papers/cryptography")
MANIFEST_PATH = PAPER_DIR / "manifest.json"
OUTPUT_PATH = PAPER_DIR / "parsed_papers.json"

# ---------------------------------------------------------------------------
# Algorithm keyword lists
# ---------------------------------------------------------------------------

ALGORITHM_KEYWORDS = {
    "BB84": ["bb84", "bennett brassard", "prepare-and-measure"],
    "E91": ["e91", "ekert", "chsh"],
    "QKD": ["qkd", "quantum key distribution", "quantum key"],
    "QBER": ["qber", "quantum bit error"],
    "MDI-QKD": ["mdi-qkd", "measurement device independent"],
    "TF-QKD": ["tf-qkd", "twin field"],
    "CV-QKD": ["cv-qkd", "continuous variable qkd", "gaussian modulation"],
    "RSA": ["rsa", "rivest shamir adleman", "factoring"],
    "AES": ["aes", "advanced encryption standard", "rijndael"],
    "ECDSA": ["ecdsa", "elliptic curve digital signature"],
    "ECDH": ["ecdh", "elliptic curve diffie"],
    "Kyber": ["kyber", "ml-kem", "crystals-kyber"],
    "Dilithium": ["dilithium", "ml-dsa", "crystals-dilithium"],
    "SPHINCS+": ["sphincs", "slh-dsa", "hash-based signature"],
    "NTRU": ["ntru", "ntruencrypt"],
    "Falcon": ["falcon signature", "falcon-512", "falcon-1024"],
    "BIKE": ["bike", "bit flipping key encapsulation"],
    "Lattice": ["lattice", "module lwe", "ring lwe", "rlwe", "mlwe"],
    "Shor": ["shor", "shor's algorithm", "period finding"],
    "Grover": ["grover", "grover's algorithm", "amplitude amplification"],
    "QRNG": ["qrng", "quantum random number", "photon randomness"],
    "Bell": ["bell inequality", "bell test", "bell state"],
    "NIST PQC": ["nist pqc", "nist post-quantum", "fips 203", "fips 204", "fips 205"],
    "Harvest": ["harvest now decrypt later", "hndl", "store now decrypt later"],
}

IMPLEMENTATION_KEYWORDS = [
    "python", "qiskit", "pennylane", "openssl", "implementation",
    "experiment", "simulation", "prototype", "we implement", "open source",
    "github", "code available", "software", "framework", "library",
]

# ---------------------------------------------------------------------------
# Scenario keyword mapping
# ---------------------------------------------------------------------------

SCENARIO_MAP = {
    "QC-01": {
        "name": "BB84 QKD",
        "keywords": ["bb84", "prepare-and-measure", "basis reconciliation", "qber", "sifting"],
    },
    "QC-02": {
        "name": "E91 Entanglement QKD",
        "keywords": ["e91", "ekert", "chsh", "bell inequality", "entangl"],
    },
    "QC-03": {
        "name": "CV-QKD",
        "keywords": ["cv-qkd", "continuous variable", "gaussian modulation", "homodyne"],
    },
    "QC-04": {
        "name": "TF-QKD",
        "keywords": ["twin field", "tf-qkd"],
    },
    "QC-05": {
        "name": "MDI-QKD",
        "keywords": ["mdi-qkd", "measurement device independent", "charlie"],
    },
    "QC-06": {
        "name": "QKD Network",
        "keywords": ["qkd network", "trusted node", "metropolitan qkd", "quantum network"],
    },
    "QC-07": {
        "name": "QRNG",
        "keywords": ["qrng", "quantum random", "photon detector", "min-entropy"],
    },
    "QC-08": {
        "name": "PQC Overview",
        "keywords": ["post-quantum cryptography", "nist pqc", "pqc migration", "quantum threat"],
    },
    "QC-09": {
        "name": "ML-KEM (Kyber)",
        "keywords": ["kyber", "ml-kem", "crystals", "module lattice", "module lwe"],
    },
    "QC-10": {
        "name": "ML-DSA (Dilithium)",
        "keywords": ["dilithium", "ml-dsa", "lattice signature", "module lwe signature"],
    },
    "QC-11": {
        "name": "SLH-DSA (SPHINCS+)",
        "keywords": ["sphincs", "slh-dsa", "hash-based signature", "hypertree", "xmss"],
    },
    "QC-12": {
        "name": "NTRU / Falcon",
        "keywords": ["ntru", "falcon", "ntruencrypt", "falcon-512"],
    },
    "QC-13": {
        "name": "BIKE / Code-Based",
        "keywords": ["bike", "code-based", "mceliece", "qc-mdpc"],
    },
    "QC-14": {
        "name": "Lattice Cryptography",
        "keywords": ["lattice", "rlwe", "ring lwe", "lwe problem", "sis problem"],
    },
    "QC-15": {
        "name": "Shor RSA Attack",
        "keywords": ["shor", "shor's algorithm", "factoring", "period finding", "rsa quantum"],
    },
    "QC-16": {
        "name": "Shor ECC Attack",
        "keywords": ["shor", "elliptic curve quantum", "ecdlp", "discrete logarithm quantum"],
    },
    "QC-17": {
        "name": "Grover AES Attack",
        "keywords": ["grover", "aes quantum", "symmetric quantum", "brute force quantum"],
    },
    "QC-18": {
        "name": "Harvest Now Decrypt Later",
        "keywords": ["harvest now", "hndl", "store now decrypt later", "quantum threat timeline"],
    },
    "QC-19": {
        "name": "TLS PQC Migration",
        "keywords": ["tls pqc", "tls post-quantum", "hybrid kem", "kyber tls", "tls 1.3 pqc"],
    },
    "QC-20": {
        "name": "PKI PQC Migration",
        "keywords": ["pki pqc", "certificate authority pqc", "x.509 pqc", "pqc certificate"],
    },
    "QC-21": {
        "name": "SSH/VPN PQC",
        "keywords": ["ssh pqc", "vpn pqc", "ipsec pqc", "openvpn pqc"],
    },
    "QC-22": {
        "name": "Hybrid Classical-PQC",
        "keywords": ["hybrid", "classical pqc hybrid", "hybrid key exchange", "combiner"],
    },
    "QC-23": {
        "name": "CNSA 2.0 Compliance",
        "keywords": ["cnsa", "nsa suite b", "cnsa 2.0", "nist fips 203"],
    },
    "QC-24": {
        "name": "Quantum Blockchain",
        "keywords": ["quantum blockchain", "pqc blockchain", "post-quantum blockchain"],
    },
}


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract full text from PDF using PyMuPDF."""
    try:
        doc = fitz.open(pdf_path)
        pages_text = []
        for page_num in range(min(len(doc), 30)):  # cap at 30 pages
            page = doc[page_num]
            pages_text.append(page.get_text())
        doc.close()
        return "\n".join(pages_text)
    except Exception as e:
        print(f"    [PDF ERROR] {e}")
        return ""


def extract_title_from_pdf(full_text: str, manifest_title: str) -> str:
    """Try to extract title from first page; fall back to manifest title."""
    lines = [l.strip() for l in full_text.split("\n") if l.strip()]
    # Heuristic: first non-trivial line in first 10 lines
    for line in lines[:10]:
        if len(line) > 20 and not line.lower().startswith("arxiv"):
            return line
    return manifest_title


def extract_abstract(full_text: str) -> str:
    """Find and extract the abstract section."""
    lower = full_text.lower()
    abstract_start = lower.find("abstract")
    if abstract_start == -1:
        return full_text[:600]
    segment = full_text[abstract_start: abstract_start + 2000]
    # Stop at common section headers
    for stop in ["1 introduction", "1. introduction", "keywords", "index terms"]:
        idx = segment.lower().find(stop)
        if idx > 50:
            return segment[:idx].strip()
    return segment[:800].strip()


def find_algorithms(text: str) -> list:
    """Scan text for known algorithm names."""
    lower = text.lower()
    found = []
    for algo, keywords in ALGORITHM_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in lower:
                if algo not in found:
                    found.append(algo)
                break
    return found


def detect_scenarios(text: str) -> list:
    """Map paper to scenario IDs based on keyword presence."""
    lower = text.lower()
    matched = []
    for scenario_id, info in SCENARIO_MAP.items():
        for kw in info["keywords"]:
            if kw.lower() in lower:
                matched.append(scenario_id)
                break
    return matched if matched else ["QC-08"]  # default: PQC Overview


def has_implementation(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in IMPLEMENTATION_KEYWORDS)


def has_python(text: str) -> bool:
    lower = text.lower()
    return "python" in lower or "qiskit" in lower or "pennylane" in lower


def extract_sections(text: str) -> list:
    """Extract section headings from text."""
    sections = []
    for line in text.split("\n"):
        stripped = line.strip()
        # Match "1 Introduction", "2.1 Background", all-caps headings
        if re.match(r"^\d+[\.\d]*\s+[A-Z][A-Za-z ]{3,}", stripped):
            sections.append(stripped[:80])
        elif re.match(r"^[A-Z][A-Z ]{5,}$", stripped) and len(stripped) < 60:
            sections.append(stripped)
    return sections[:20]


def count_figures(text: str) -> int:
    count = 0
    for line in text.split("\n"):
        if re.search(r"\bFig(ure)?\.?\s*\d+", line, re.IGNORECASE):
            count += 1
    return count


def make_citation_key(authors: list, year: int, title: str) -> str:
    last = authors[0].split()[-1] if authors else "Unknown"
    word = re.sub(r"[^A-Za-z]", "", title.split()[0]) if title.split() else "Paper"
    return f"{last}{year}_{word}"


def get_impl_snippet(text: str) -> str:
    lower = text.lower()
    for kw in ["we implement", "our implementation", "we propose", "we simulate"]:
        idx = lower.find(kw)
        if idx != -1:
            return text[idx: idx + 200].replace("\n", " ").strip()
    return ""


def parse_paper(entry: dict) -> dict:
    pdf_path = entry.get("pdf_path", "")
    if not pathlib.Path(pdf_path).exists():
        return None

    print(f"  Parsing: {entry['title'][:60]}")
    full_text = extract_text_from_pdf(pdf_path)
    if not full_text:
        return None

    try:
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        doc.close()
    except Exception:
        page_count = 0

    abstract = extract_abstract(full_text)
    algorithms = find_algorithms(full_text)
    scenarios = detect_scenarios(full_text)
    sections = extract_sections(full_text)
    figure_count = count_figures(full_text)
    impl_snippet = get_impl_snippet(full_text)
    authors = entry.get("authors", [])
    year = entry.get("year", 0)
    title = entry.get("title", "")

    return {
        "arxiv_id": entry.get("arxiv_id", ""),
        "title": title,
        "authors": authors,
        "year": year,
        "abstract_text": abstract,
        "page_count": page_count,
        "algorithms_found": algorithms,
        "scenario_ids": scenarios,
        "has_implementation": has_implementation(full_text),
        "has_python_code": has_python(full_text),
        "key_sections": sections,
        "figure_count": figure_count,
        "implementation_snippet": impl_snippet,
        "pdf_path": pdf_path,
        "citation_key": make_citation_key(authors, year, title),
        "categories": entry.get("categories", []),
        "query_category": entry.get("query_category", ""),
    }


def main():
    if not MANIFEST_PATH.exists():
        print(f"Manifest not found at {MANIFEST_PATH}")
        print("Run download_crypto_papers.py first.")
        sys.exit(1)

    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

    print(f"Parsing {len(manifest)} manifest entries...")
    parsed = []
    skipped = 0

    for entry in manifest:
        result = parse_paper(entry)
        if result:
            parsed.append(result)
        else:
            skipped += 1

    with open(OUTPUT_PATH, "w") as f:
        json.dump(parsed, f, indent=2, default=str)

    # Stats
    scenarios_covered = set()
    for p in parsed:
        scenarios_covered.update(p.get("scenario_ids", []))

    print(f"\n[DONE] Parsed: {len(parsed)} papers")
    print(f"[DONE] Skipped (no PDF): {skipped}")
    print(f"[DONE] Scenarios covered: {len(scenarios_covered)}")
    print(f"[DONE] Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
