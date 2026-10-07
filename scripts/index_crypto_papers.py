#!/usr/bin/env python3
"""
Index parsed quantum cryptography papers into ChromaDB for RAG search.
Uses sentence-transformers (all-MiniLM-L6-v2) for embeddings.
Output: /mnt/deepa/quantum/api/chromadb/papers  (persistent)
"""
import json
import pathlib
import sys

try:
    import chromadb
except ImportError:
    print("chromadb not installed. Run: pip3 install chromadb")
    sys.exit(1)

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("sentence-transformers not installed. Run: pip3 install sentence-transformers")
    sys.exit(1)

CHROMA_DIR = "/mnt/deepa/quantum/api/chromadb/papers"
PARSED_PATH = "/mnt/deepa/quantum/datasets/papers/cryptography/parsed_papers.json"

pathlib.Path(CHROMA_DIR).mkdir(parents=True, exist_ok=True)


def main():
    if not pathlib.Path(PARSED_PATH).exists():
        print(f"parsed_papers.json not found at {PARSED_PATH}")
        print("Run parse_crypto_papers.py first.")
        sys.exit(1)

    with open(PARSED_PATH) as f:
        papers = json.load(f)

    print(f"Loading {len(papers)} parsed papers...")

    client = chromadb.PersistentClient(path=CHROMA_DIR)

    # Delete and recreate collection for a clean index
    try:
        client.delete_collection("crypto_papers")
        print("Deleted existing collection for fresh index.")
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name="crypto_papers",
        metadata={"hnsw:space": "cosine"},
    )

    print("Loading embedding model (all-MiniLM-L6-v2)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    batch_ids = []
    batch_embeddings = []
    batch_documents = []
    batch_metadatas = []
    BATCH_SIZE = 32

    indexed = 0
    skipped = 0

    for p in papers:
        if not pathlib.Path(p.get("pdf_path", "")).exists():
            skipped += 1
            continue

        arxiv_id = p.get("arxiv_id", "")
        if not arxiv_id:
            skipped += 1
            continue

        # Chunk: title + abstract for the embedding text
        title = p.get("title", "")
        abstract = p.get("abstract_text", "")
        text = f"{title}\n\n{abstract}"

        try:
            embedding = model.encode(text).tolist()
        except Exception as e:
            print(f"  [EMBED ERROR] {arxiv_id}: {e}")
            skipped += 1
            continue

        scenario_ids = p.get("scenario_ids", [])
        algos = p.get("algorithms_found", [])

        batch_ids.append(arxiv_id)
        batch_embeddings.append(embedding)
        batch_documents.append(text[:2000])
        batch_metadatas.append({
            "title": title[:200],
            "scenario_ids": ",".join(scenario_ids),
            "year": str(p.get("year", "")),
            "algorithms": ",".join(algos[:10]),
            "has_implementation": str(p.get("has_implementation", False)),
            "has_python": str(p.get("has_python_code", False)),
            "page_count": str(p.get("page_count", 0)),
            "pdf_path": p.get("pdf_path", "")[:500],
            "citation_key": p.get("citation_key", ""),
        })

        if len(batch_ids) >= BATCH_SIZE:
            collection.upsert(
                ids=batch_ids,
                embeddings=batch_embeddings,
                documents=batch_documents,
                metadatas=batch_metadatas,
            )
            indexed += len(batch_ids)
            print(f"  Indexed batch of {len(batch_ids)} (total: {indexed})")
            batch_ids, batch_embeddings, batch_documents, batch_metadatas = [], [], [], []

    # Flush remaining
    if batch_ids:
        collection.upsert(
            ids=batch_ids,
            embeddings=batch_embeddings,
            documents=batch_documents,
            metadatas=batch_metadatas,
        )
        indexed += len(batch_ids)

    total_in_collection = collection.count()
    print(f"\n[DONE] Indexed this run: {indexed}")
    print(f"[DONE] Skipped: {skipped}")
    print(f"[DONE] Total in ChromaDB collection: {total_in_collection}")
    print(f"[DONE] ChromaDB path: {CHROMA_DIR}")


if __name__ == "__main__":
    main()
