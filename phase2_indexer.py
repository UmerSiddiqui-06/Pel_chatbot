"""
PHASE 2 — Embedding & Indexing for the PEL RAG pipeline.

Reads   : output/chunks/phase1_chunks.jsonl
Creates : ChromaDB collection (vector search)
          output/chunks/bm25_index.pkl (keyword search)
          output/chunks/exact_match.json (error code / model lookup)
"""
from __future__ import annotations

import json
import pickle
import re
from pathlib import Path

import numpy as np
from tqdm import tqdm

import config


def tokenize(text: str) -> list[str]:
    """Normalize markdown-heavy text into clean lowercase tokens."""
    text = re.sub(r'[*_`#]', ' ', text)
    return re.findall(r"[a-z0-9]+", text.lower())


# ════════════════════════════════════════════════════════════════════════
# 1. LOAD CHUNKS
# ════════════════════════════════════════════════════════════════════════
def load_chunks() -> list[dict]:
    """Load Phase 1 chunks from JSONL."""
    chunks = []
    with open(config.OUTPUT_JSONL, "r", encoding="utf-8") as f:
        for line in f:
            chunks.append(json.loads(line.strip()))
    print(f"✅ Loaded {len(chunks)} chunks from {config.OUTPUT_JSONL}")
    return chunks


# ════════════════════════════════════════════════════════════════════════
# 2. BUILD EMBEDDING TEXT (what we actually embed)
# ════════════════════════════════════════════════════════════════════════
def build_embedding_text(chunk: dict) -> str:
    """
    Construct the text that gets embedded.
    We prepend the heading path (title) so the embedding captures context,
    not just raw content.
    """
    meta = chunk["metadata"]
    parts = []

    # Add heading path for context
    if meta.get("title"):
        parts.append(f"Section: {meta['title']}")

    # Add product category and section for retrieval context
    if meta.get("product_category") and meta["product_category"] != "general":
        parts.append(f"Product: {meta['product_category'].replace('_', ' ')}")

    # Add error codes if present (critical for troubleshooting queries)
    if meta.get("error_codes"):
        parts.append(f"Error Codes: {', '.join(meta['error_codes'])}")

    # Add model names if present
    if meta.get("model_names"):
        parts.append(f"Models: {', '.join(meta['model_names'][:10])}")

    # Add the actual content
    parts.append(chunk["text"])

    return "\n".join(parts)


def build_rerank_text(chunk: dict) -> str:
    """
    Text passed to the cross-encoder for reranking.
    Must include title context so short/table-like chunks retain their
    section/product meaning during reranking.
    """
    meta = chunk["metadata"]
    parts = []

    if meta.get("title"):
        parts.append(meta["title"])

    if meta.get("product_category") and meta["product_category"] != "general":
        parts.append(meta["product_category"].replace("_", " "))

    parts.append(chunk["text"])
    return "\n".join(parts)


# ════════════════════════════════════════════════════════════════════════
# 3. CHROMADB — VECTOR INDEX
# ════════════════════════════════════════════════════════════════════════
def build_chroma_index(chunks: list[dict]) -> None:
    """Embed all chunks and store in ChromaDB with metadata."""
    import chromadb
    from chromadb.utils import embedding_functions

    # Initialize ChromaDB with persistent storage
    client = chromadb.PersistentClient(path=str(config.CHROMA_PERSIST_DIR))

    # Use sentence-transformers embedding function
    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=config.EMBEDDING_MODEL
    )

    # Delete existing collection if it exists (fresh build)
    try:
        client.delete_collection(config.CHROMA_COLLECTION)
    except Exception:
        pass

    collection = client.create_collection(
        name=config.CHROMA_COLLECTION,
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"}  # cosine similarity
    )

    print(f"\n🔄 Embedding {len(chunks)} chunks with {config.EMBEDDING_MODEL}...")
    print("   (First run downloads ~2GB model, subsequent runs use cache)")

    # Prepare data in batches (ChromaDB has batch limits)
    BATCH_SIZE = 32

    for i in tqdm(range(0, len(chunks), BATCH_SIZE), desc="Embedding"):
        batch = chunks[i:i + BATCH_SIZE]

        ids = []
        documents = []
        metadatas = []

        for chunk in batch:
            meta = chunk["metadata"]
            ids.append(chunk["chunk_id"])
            documents.append(build_embedding_text(chunk))
            metadatas.append({
                "title": meta.get("title", ""),
                "page_start": meta.get("page_start", 0),
                "page_end": meta.get("page_end", 0),
                "product_category": meta.get("product_category", "general"),
                "section": meta.get("section", ""),
                "content_type": meta.get("content_type", "text"),
                "model_names": ", ".join(meta.get("model_names", [])),
                "error_codes": ", ".join(meta.get("error_codes", [])),
                "char_count": meta.get("char_count", 0),
            })

        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

    print(f"✅ ChromaDB index built: {collection.count()} chunks stored")
    print(f"   Location: {config.CHROMA_PERSIST_DIR}")


# ════════════════════════════════════════════════════════════════════════
# 4. BM25 — KEYWORD INDEX
# ════════════════════════════════════════════════════════════════════════
def build_bm25_index(chunks: list[dict]) -> None:
    """
    Build a BM25 keyword index for exact term matching.
    This catches exact error codes, model numbers, and technical terms
    that vector search might miss.
    """
    from rank_bm25 import BM25Okapi

    tokenized_docs = []
    for chunk in chunks:
        text = build_embedding_text(chunk)
        tokenized_docs.append(tokenize(text))

    bm25 = BM25Okapi(tokenized_docs)

    # Save the BM25 index + chunk IDs for lookup
    bm25_data = {
        "bm25": bm25,
        "chunk_ids": [c["chunk_id"] for c in chunks],
        "chunk_texts": [c["text"] for c in chunks],
    }

    with open(config.BM25_INDEX_PATH, "wb") as f:
        pickle.dump(bm25_data, f)

    print(f"✅ BM25 index built: {len(chunks)} documents indexed")
    print(f"   Location: {config.BM25_INDEX_PATH}")


# ════════════════════════════════════════════════════════════════════════
# 5. EXACT-MATCH INDEX — Error Codes & Model Names
# ════════════════════════════════════════════════════════════════════════
def build_exact_match_index(chunks: list[dict]) -> None:
    """
    Build a fast lookup dictionary:
      error_code -> [chunk_ids that mention this code]
      model_name -> [chunk_ids that mention this model]

    This is the HIGHEST PRECISION retrieval path.
    When a user asks "E1 error on ACE", we can directly find the exact chunks.
    """
    error_code_index: dict[str, list[str]] = {}
    model_name_index: dict[str, list[str]] = {}

    for chunk in chunks:
        meta = chunk["metadata"]
        chunk_id = chunk["chunk_id"]

        # Index error codes
        for code in meta.get("error_codes", []):
            code_key = code.upper().strip()
            if code_key:
                if code_key not in error_code_index:
                    error_code_index[code_key] = []
                error_code_index[code_key].append(chunk_id)

        # Index model names
        for model in meta.get("model_names", []):
            model_key = model.upper().strip()
            if model_key:
                if model_key not in model_name_index:
                    model_name_index[model_key] = []
                model_name_index[model_key].append(chunk_id)

    exact_match = {
        "error_codes": error_code_index,
        "model_names": model_name_index,
    }

    with open(config.EXACT_MATCH_PATH, "w", encoding="utf-8") as f:
        json.dump(exact_match, f, indent=2, ensure_ascii=False)

    print(f"✅ Exact-match index built:")
    print(f"   Error codes indexed: {len(error_code_index)}")
    print(f"   Model names indexed: {len(model_name_index)}")
    print(f"   Location: {config.EXACT_MATCH_PATH}")


# ════════════════════════════════════════════════════════════════════════
# 6. MAIN
# ════════════════════════════════════════════════════════════════════════
def main():
    print("=" * 60)
    print("  PHASE 2: EMBEDDING & INDEXING")
    print("=" * 60)

    # Step 1: Load chunks
    chunks = load_chunks()

    # Step 2: Build ChromaDB vector index
    build_chroma_index(chunks)

    # Step 3: Build BM25 keyword index
    build_bm25_index(chunks)

    # Step 4: Build exact-match index
    build_exact_match_index(chunks)

    print("\n" + "=" * 60)
    print("  PHASE 2 COMPLETE ✅")
    print("=" * 60)
    print(f"\n  ChromaDB:      {config.CHROMA_PERSIST_DIR}")
    print(f"  BM25 Index:    {config.BM25_INDEX_PATH}")
    print(f"  Exact Match:   {config.EXACT_MATCH_PATH}")
    print(f"\n  Next: Phase 3 (Query Pipeline)")


if __name__ == "__main__":
    main()