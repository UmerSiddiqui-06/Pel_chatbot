"""Central configuration for the PEL RAG pipeline — Phase 1."""
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────
BASE_DIR       = Path(__file__).resolve().parent
INPUT_MD       = BASE_DIR / "output" / "output_document_updated.md"
OUTPUT_DIR     = BASE_DIR / "output" / "chunks"
OUTPUT_JSON    = OUTPUT_DIR / "phase1_chunks.json"
OUTPUT_JSONL   = OUTPUT_DIR / "phase1_chunks.jsonl"
OUTPUT_REPORT  = OUTPUT_DIR / "phase1_report.json"

# ── Chunking thresholds ──────────────────────────────────────────────────
# PAGE-LEVEL divider detection: a page is a divider if its ENTIRE body
# (excluding headings and tables) has fewer words than this.
PAGE_DIVIDER_MAX_WORDS = 15

# Section-level: only used as a sanity check for truly empty fragments.
# Set very low so real bullet-point content is never killed.
SECTION_MIN_WORDS = 3

MAX_CHUNK_CHARS       = 4000
ATOMIC_FLOW_MAX_CHARS = 12000

# ── Regex ────────────────────────────────────────────────────────────────
PAGE_MARKER_RE       = r'^\s*(?:#{1,6}\s+)?PAGE\s+(\d+)\s*$'
HEADING_RE           = r'^(#{1,6})\s+(.*)$'
CONT_ANY_RE          = r'Cont(?:i|inue)?\.{2,}'
CONT_TITLE_SUFFIX_RE = r'\s*\(Cont(?:i|inue)?\.{1,}\)'
MODEL_CODE_RE        = r'\bP[A-Z]{2,9}[-\s]?\d{2,5}[A-Z0-9]{0,4}\b'

# Inline tag we inject to track page numbers while heading-chunking.
PAGE_TAG_RE = r'@@PAGE:(\d+)@@'