"""Central configuration for the PEL RAG pipeline — Phase 1, 2 & 3."""
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────
BASE_DIR       = Path(__file__).resolve().parent
INPUT_MD       = BASE_DIR / "output" / "output_document_updated.md"
OUTPUT_DIR     = BASE_DIR / "output" / "chunks"
OUTPUT_JSON    = OUTPUT_DIR / "phase1_chunks.json"
OUTPUT_JSONL   = OUTPUT_DIR / "phase1_chunks.jsonl"
OUTPUT_REPORT  = OUTPUT_DIR / "phase1_report.json"

# ── Chunking thresholds ──────────────────────────────────────────────────
PAGE_DIVIDER_MAX_WORDS = 15
SECTION_MIN_WORDS = 3
MAX_CHUNK_CHARS       = 4000
ATOMIC_FLOW_MAX_CHARS = 12000

# ── Regex ────────────────────────────────────────────────────────────────
PAGE_MARKER_RE       = r'^\s*(?:#{1,6}\s+)?PAGE\s+(\d+)\s*$'
HEADING_RE           = r'^(#{1,6})\s+(.*)$'
CONT_ANY_RE          = r'Cont(?:i|inue)?\.{2,}'
CONT_TITLE_SUFFIX_RE = r'\s*\(Cont(?:i|inue)?\.{1,}\)'
MODEL_CODE_RE        = r'\bP[A-Z]{2,9}[-\s]?\d{2,5}[A-Z0-9]{0,4}\b'
PAGE_TAG_RE = r'@@PAGE:(\d+)@@'

# ── Phase 2: Indexing ────────────────────────────────────────────────────
EMBEDDING_MODEL = "BAAI/bge-m3"
CHROMA_PERSIST_DIR = BASE_DIR / "output" / "chroma_db"
BM25_INDEX_PATH = OUTPUT_DIR / "bm25_index.pkl"
EXACT_MATCH_PATH = OUTPUT_DIR / "exact_match.json"
CHROMA_COLLECTION = "pel_manual_chunks"

# ── Phase 3: Retrieval & Answer ──────────────────────────────────────────
# ── Phase 3: Retrieval & Answer ──────────────────────────────────────────
# Gemini API — lightweight models for query understanding (fast & cheap)
# Uses the SAME exact model names & SDK pattern as your PDF extraction script
QUERY_UNDERSTANDING_MODELS = [
    "gemini-3.5-flash-lite",     # primary — keep, fastest+cheapest, good extraction
    "gemini-3.1-flash-lite",     # fallback 1 — stable long-term, won't vanish
    "gemini-3.5-flash",          # fallback 2 — stronger if both lite models rate-limited
]

# Gemini API — strong models for answer generation (quality)
ANSWER_GENERATION_MODELS = [
    "gemini-3.6-flash",         # primary — strongest current flash, good agentic/reasoning
    "gemini-3.5-flash",         # fallback 1 — still solid quality
    "gemini-3.5-flash-lite",    # fallback 2 — last resort, only if both above fail
]

# Cross-Encoder Reranker
# Lightweight CPU reranker; the query is translated to English before this step.
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RERANKER_MAX_LENGTH = 256
CPU_THREADS = 10
RERANKER_BATCH_SIZE = 10

# Retrieval settings
VECTOR_SEARCH_TOP_K = 20
BM25_SEARCH_TOP_K = 20
RRF_K = 60
RRF_TOP_CANDIDATES = 10
FINAL_TOP_K = 5
CATEGORY_SEARCH_MIN_RESULTS = 3
MAX_CHUNK_CONTEXT_CHARS = 1500