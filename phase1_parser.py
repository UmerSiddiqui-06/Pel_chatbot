"""
PHASE 1 — Structure-Aware Parser & Chunker for the PEL technical manual.

Reads   : output/output_document_updated.md
Writes  : output/chunks/phase1_chunks.jsonl
          output/chunks/phase1_report.json

Key fix: Divider detection is now at the PAGE level, not the section level.
A page is skipped only if its ENTIRE body has < PAGE_DIVIDER_MAX_WORDS words
and no tables. Individual sections are never skipped by word count alone.
"""
from __future__ import annotations

import json
import re
from collections import Counter

import config

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(x, **kwargs):
        return x


# ════════════════════════════════════════════════════════════════════════
# 1. PAGE PARSING
# ════════════════════════════════════════════════════════════════════════
_PAGE_RE = re.compile(config.PAGE_MARKER_RE, re.MULTILINE | re.IGNORECASE)


def parse_pages(raw_text: str) -> list[dict]:
    """Split the raw file into [{'page_num', 'text'}, ...]."""
    matches = list(_PAGE_RE.finditer(raw_text))
    pages = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)
        pages.append({
            "page_num": int(m.group(1)),
            "text": raw_text[start:end].strip(),
        })
    return pages


# ════════════════════════════════════════════════════════════════════════
# 2. PAGE-LEVEL DIVIDER DETECTION (the critical fix)
# ════════════════════════════════════════════════════════════════════════
def is_page_divider(text: str) -> bool:
    """
    A page is a TRUE divider only if its entire body content
    (after removing heading lines and table lines) is very short
    and contains no table.
    
    This catches pages like:
      - "PEL Deep Freezer" (page 30)
      - "4. Error Code & Troubleshooting" (page 122)
      - "7. Installation of Split AC" (page 149)
      - "PEL Range – LED Television / LED TV Troubleshooting" (page 177)
    
    It does NOT catch pages with feature bullets, model lists, etc.
    """
    lines = text.split("\n")
    body_lines = []
    has_table = False

    for line in lines:
        stripped = line.strip()
        # Skip heading lines
        if re.match(r'^#{1,6}\s+', stripped):
            continue
        # Detect table lines
        if stripped.startswith("|") or re.match(r'^\|[\s\-:|]+\|', stripped):
            has_table = True
            continue
        # Skip empty lines
        if not stripped:
            continue
        body_lines.append(stripped)

    if has_table:
        return False  # Pages with tables are NEVER dividers

    body_text = " ".join(body_lines)
    word_count = len(body_text.split())
    return word_count < config.PAGE_DIVIDER_MAX_WORDS


def filter_divider_pages(pages: list[dict]) -> tuple[list[dict], list[int]]:
    """Remove true divider pages. Returns (kept_pages, skipped_page_nums)."""
    kept = []
    skipped = []
    for page in pages:
        if is_page_divider(page["text"]):
            skipped.append(page["page_num"])
        else:
            kept.append(page)
    return kept, skipped


# ════════════════════════════════════════════════════════════════════════
# 3. CONTINUATION-MARKER CLEANING
# ════════════════════════════════════════════════════════════════════════
_CONT_TITLE = re.compile(config.CONT_TITLE_SUFFIX_RE)
_CONT_ANY = re.compile(config.CONT_ANY_RE)


def clean_page(page: dict) -> dict:
    """Strip '(Cont..)' title suffixes and bare 'Cont......' markers."""
    text = page["text"]
    # Remove parenthesised title suffix first
    text = _CONT_TITLE.sub("", text)
    # Detect a real (bare) continuation marker before stripping it
    has_cont = bool(_CONT_ANY.search(text))
    text = _CONT_ANY.sub("", text)
    page["text"] = text.strip()
    page["has_cont"] = has_cont
    return page


def build_stream(pages: list[dict]) -> str:
    """Join pages into one stream with inline @@PAGE:N@@ tags."""
    parts = []
    for p in pages:
        parts.append(f"@@PAGE:{p['page_num']}@@")
        parts.append(p["text"])
    return "\n".join(parts)


# ════════════════════════════════════════════════════════════════════════
# 4. HEADING-AWARE CHUNKING
# ════════════════════════════════════════════════════════════════════════
_HEADING = re.compile(config.HEADING_RE)
_PAGE_TAG = re.compile(config.PAGE_TAG_RE)


def chunk_by_headings(stream: str):
    """
    Walk the stream maintaining a heading stack. Emit a chunk whenever the
    heading path changes. Returns (chunks, heading_count).
    Each chunk: {'heading_path': [...], 'content': str, 'pages': [..]}
    """
    lines = stream.split("\n")
    chunks = []
    heading_stack = {}
    cur_path: list[str] = []
    cur_content: list[str] = []
    cur_pages: set[int] = set()
    cur_page = None
    heading_count = 0

    def path_now():
        return [heading_stack[l] for l in sorted(heading_stack)]

    def emit():
        nonlocal cur_content, cur_pages
        text = "\n".join(cur_content).strip()
        if text:
            chunks.append({
                "heading_path": list(cur_path),
                "content": text,
                "pages": sorted(cur_pages),
            })
        cur_content = []
        cur_pages = set()

    for line in lines:
        pm = _PAGE_TAG.match(line.strip())
        if pm:
            cur_page = int(pm.group(1))
            continue

        hm = _HEADING.match(line)
        if hm:
            emit()
            heading_count += 1
            level = len(hm.group(1))
            heading_stack[level] = hm.group(2).strip()
            for l in list(heading_stack.keys()):
                if l > level:
                    del heading_stack[l]
            cur_path = path_now()
            if cur_page is not None:
                cur_pages.add(cur_page)
            continue

        cur_content.append(line)
        if cur_page is not None:
            cur_pages.add(cur_page)

    emit()
    return chunks, heading_count


def merge_continuations(chunks: list[dict]) -> list[dict]:
    """Merge adjacent chunks that share the SAME heading path."""
    if not chunks:
        return []
    merged = [chunks[0]]
    for ch in chunks[1:]:
        if ch["heading_path"] == merged[-1]["heading_path"]:
            merged[-1]["content"] += "\n\n" + ch["content"]
            merged[-1]["pages"] = sorted(set(merged[-1]["pages"]) | set(ch["pages"]))
        else:
            merged.append(ch)
    return merged


# ════════════════════════════════════════════════════════════════════════
# 5. CONTENT-TYPE DETECTION
# ════════════════════════════════════════════════════════════════════════
def is_flowchart(text: str) -> bool:
    if re.search(r"Flowchart", text, re.I):
        return True
    has_yes = bool(re.search(r"\bYes\b", text, re.I))
    has_no = bool(re.search(r"\bNo\b", text, re.I))
    if not (has_yes and has_no):
        return False
    has_check = bool(re.search(r"\bCheck\b", text, re.I))
    has_arrow = bool(re.search(r"→|↓|->", text))
    has_replace = bool(re.search(r"\bReplace\b", text, re.I))
    has_whether = bool(re.search(r"\bwhether\b", text, re.I))
    return has_check or has_arrow or has_replace or has_whether


def classify_content(text: str) -> str:
    has_table = bool(re.search(r"\|[\s\-:|]+\|", text))
    if re.search(r"warranty", text, re.I):
        return "warranty"
    if has_table and re.search(r"error\s*code|\bfault\b|failure", text, re.I):
        return "error_code_table"
    if has_table:
        return "spec_table"
    if re.search(r"installation|installing|\binstall\b", text, re.I):
        return "installation_sop"
    return "text"


def split_large_text(text: str, max_chars: int) -> list[str]:
    paras = re.split(r"\n{2,}", text)
    out, cur, cur_len = [], [], 0
    for p in paras:
        if cur_len + len(p) > max_chars and cur:
            out.append("\n\n".join(cur))
            cur, cur_len = [], 0
        cur.append(p)
        cur_len += len(p) + 2
    if cur:
        out.append("\n\n".join(cur))
    return out


# ════════════════════════════════════════════════════════════════════════
# 6. METADATA EXTRACTION
# ════════════════════════════════════════════════════════════════════════
AC_SERIES = [
    "JUMBO DC PRIME", "JUMBO DC CLASSIC", "JUMBO DC BLACK", "JUMBO DC",
    "TURBO DC ULTIMATE", "TURBO DC ULTRA", "TURBO DC",
    "AERO EXTEND", "AERO PLUS", "AERO",
    "MAJESTIC GLORY", "MAJESTIC T3", "MAJESTIC",
    "ALPHA", "APEX", "ACE", "ALLURE", "REGAL", "SUPREME", "FIT", "SAVER",
    "SUPER", "SUBLIME", "ALPINE", "O-GLORY", "ULTIMATE", "BOLD", "PANASONIC",
]
_AC_SORTED = sorted(AC_SERIES, key=len, reverse=True)
_MODEL_CODE = re.compile(config.MODEL_CODE_RE)


def extract_model_names(text: str) -> list[str]:
    upper = text.upper()
    found = set()
    for name in _AC_SORTED:
        if re.search(r"\b" + re.escape(name) + r"\b", upper):
            found.add(name)
    for m in _MODEL_CODE.finditer(upper):
        found.add(m.group(0).strip())
    return sorted(found)


_ERROR_PREFIX = r"(?:PC|EL|EH|EC|EA|EB|EE|EF|EU|FA|FC|FB|FH|PA|PE|Fb|Eb|E|F|P|L)"
_ERROR_CODE = re.compile(rf"\b{_ERROR_PREFIX}\s?\d{{1,2}}[A-Z]?\b")


def parse_markdown_tables(text: str):
    tables, current = [], []
    for line in text.split("\n"):
        if line.strip().startswith("|"):
            current.append(line.strip())
        else:
            if len(current) >= 2:
                tables.append(current)
            current = []
    if len(current) >= 2:
        tables.append(current)
    parsed = []
    for tbl in tables:
        rows = []
        for row in tbl:
            cells = [c.strip() for c in row.strip("|").split("|")]
            if all(re.match(r"^:?-{2,}:?$", c) or c == "" for c in cells):
                continue
            rows.append(cells)
        if rows:
            parsed.append(rows)
    return parsed


_CODE_HEADER = re.compile(r"(^\s*code\s*$|error\s*code|idu\s*display|fault\s*code)", re.I)
_ERROR_TABLE = re.compile(r"(error|fault|failure|trouble|display)", re.I)


def _codes_from_tables(text: str) -> set[str]:
    codes = set()
    for rows in parse_markdown_tables(text):
        if not rows or not _ERROR_TABLE.search(" ".join(rows[0])):
            continue
        code_cols = [i for i, h in enumerate(rows[0])
                     if _CODE_HEADER.search(h or "") and "inverter" not in h.lower()]
        for row in rows[1:]:
            for ci in code_cols:
                if ci >= len(row):
                    continue
                val = re.sub(r"<br\s*/?>", " ", row[ci]).strip()
                for tok in re.findall(r"\b[A-Z]{0,2}\s?\d{1,2}[A-Z]?\b|\b5E\b", val):
                    tok = tok.replace(" ", "").upper()
                    if tok and len(tok) <= 5:
                        codes.add(tok)
    return codes


def extract_error_codes(text: str) -> list[str]:
    codes = set()
    for m in _ERROR_CODE.finditer(text):
        codes.add(m.group(0).replace(" ", "").upper())
    for _ in re.finditer(r"\b5E\b", text):
        codes.add("5E")
    codes |= _codes_from_tables(text)
    return sorted(codes)


def detect_product_category(text: str, title: str) -> str:
    blob = (title + "\n" + text).lower()
    checks = [
        ("led_television", ["led television", "led tv", "pld-", "google tv", "coloron"]),
        ("microwave_oven", ["microwave", "pmo", "magnetron", "convection series", "grill function"]),
        ("water_dispenser", ["water dispenser", "pwd-", "pcwd"]),
        ("washing_machine", ["washing machine", "pawm", "pwms", "pwm-", "i-wash", "fit-wash", "fitwash"]),
        ("deep_freezer", ["deep freezer", "pdf-", "pdint", "arctic", "pvf-", "profreeze"]),
        ("refrigerator", ["refrigerator", "prlp", "prgd", "prinv", "digitron", "insta cool", "life pro"]),
        ("air_conditioner", ["air conditioner", "split ac", "inverter ac", "pel ac model",
                             "ac model", " idu", " odu","id pipe sensor", "indoor unit", "outdoor unit",
                             "compressor malfunction", "split air"]),
    ]
    for cat, kws in checks:
        if any(k in blob for k in kws):
            return cat
    return "general"


def detect_section(text: str, content_type: str, title: str) -> str:
    tl = title.lower()
    if content_type == "troubleshooting_flow":
        return "troubleshooting"
    if content_type == "error_code_table":
        return "error_codes"
    if content_type == "warranty":
        return "warranty"
    if content_type == "installation_sop":
        return "installation"
    if content_type == "spec_table":
        return "specifications"
    if "warranty" in tl:
        return "warranty"
    if "installation" in tl or "install" in tl:
        return "installation"
    if "error code" in tl or "troubleshoot" in tl or "fault" in tl:
        return "troubleshooting"
    if re.search(r"troubleshoot|error code|fault", text, re.I):
        return "troubleshooting"
    if re.search(r"installation|install", text, re.I):
        return "installation"
    if re.search(r"warranty", text, re.I):
        return "warranty"
    return "features"


# ════════════════════════════════════════════════════════════════════════
# 7. CHUNK ASSEMBLY
# ════════════════════════════════════════════════════════════════════════
def make_chunk(text, title, page_start, page_end, content_type, pages):
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return {
        "text": text,
        "metadata": {
            "title": title,
            "page_start": page_start,
            "page_end": page_end,
            "source_pages": pages,
            "product_category": detect_product_category(text, title),
            "section": detect_section(text, content_type, title),
            "content_type": content_type,
            "model_names": extract_model_names(text),
            "error_codes": extract_error_codes(text),
            "char_count": len(text),
        },
    }


def process_section(sec: dict) -> list[dict]:
    """
    Process a merged section into one or more chunks.
    
    IMPORTANT: No is_divider() check here. Divider filtering is done
    at the PAGE level before chunking. This ensures short but valid
    content (feature bullets, model lists, etc.) is never skipped.
    """
    content = sec["content"]
    pages = sec["pages"]
    title = " > ".join(sec["heading_path"])
    page_start = pages[0] if pages else None
    page_end = pages[-1] if pages else None

    # Skip only truly empty fragments (sanity check, not content filter)
    if len(content.split()) < config.SECTION_MIN_WORDS:
        return []

    # Rule A: flowcharts stay atomic
    if is_flowchart(content):
        return [make_chunk(content, title, page_start, page_end,
                           "troubleshooting_flow", pages)]

    ctype = classify_content(content)

    # Rule B: tables & warranty stay whole
    if ctype in ("spec_table", "error_code_table", "warranty"):
        return [make_chunk(content, title, page_start, page_end, ctype, pages)]

    # Rule C: large plain text gets split
    if len(content) > config.MAX_CHUNK_CHARS:
        parts = split_large_text(content, config.MAX_CHUNK_CHARS)
        return [make_chunk(p, title, page_start, page_end, ctype, pages)
                for p in parts]

    return [make_chunk(content, title, page_start, page_end, ctype, pages)]


# ════════════════════════════════════════════════════════════════════════
# 8. MAIN
# ════════════════════════════════════════════════════════════════════════
def main() -> None:
    if not config.INPUT_MD.exists():
        raise FileNotFoundError(f"Input not found: {config.INPUT_MD}")

    raw = config.INPUT_MD.read_text(encoding="utf-8")
    pages = parse_pages(raw)

    # ── STEP 1: Filter divider pages at the PAGE level ──────────────────
    kept_pages, skipped_page_nums = filter_divider_pages(pages)
    print(f"Divider pages removed (page-level): {len(skipped_page_nums)} -> {skipped_page_nums}")

    # ── STEP 2: Clean continuation markers ──────────────────────────────
    kept_pages = [clean_page(p) for p in kept_pages]
    cont_pages = [p["page_num"] for p in kept_pages if p["has_cont"]]

    # ── STEP 3: Build stream and chunk by headings ──────────────────────
    stream = build_stream(kept_pages)
    raw_chunks, heading_count = chunk_by_headings(stream)

    if heading_count == 0:
        print("⚠️  WARNING: No Markdown headings detected.")

    # ── STEP 4: Merge adjacent same-path chunks ─────────────────────────
    merged = merge_continuations(raw_chunks)

    # ── STEP 5: Process sections into final chunks ──────────────────────
    all_chunks = []
    tiny_skipped = 0
    for sec in tqdm(merged, desc="Chunking", unit="section"):
        out = process_section(sec)
        if not out:
            tiny_skipped += 1
        all_chunks.extend(out)

    # ── STEP 6: Write output ────────────────────────────────────────────
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Standard JSON array for downstream tools / UI consumption.
    for i, ch in enumerate(all_chunks, 1):
        ch["chunk_id"] = f"pel_{i:04d}"

    with open(config.OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)
        f.write("\n")

    with open(config.OUTPUT_JSONL, "w", encoding="utf-8") as f:
        for ch in all_chunks:
            f.write(json.dumps(ch, ensure_ascii=False) + "\n")

    type_counts = Counter(c["metadata"]["content_type"] for c in all_chunks)
    cat_counts = Counter(c["metadata"]["product_category"] for c in all_chunks)
    report = {
        "input_file": str(config.INPUT_MD),
        "total_pages_parsed": len(pages),
        "divider_pages_removed": skipped_page_nums,
        "headings_detected": heading_count,
        "continuation_marker_pages": cont_pages,
        "raw_chunks_before_merge": len(raw_chunks),
        "sections_after_merge": len(merged),
        "tiny_fragments_skipped": tiny_skipped,
        "total_chunks": len(all_chunks),
        "chunks_by_content_type": dict(type_counts),
        "chunks_by_product_category": dict(cat_counts),
    }
    with open(config.OUTPUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n=== PHASE 1 SUMMARY ===")
    print(f"Pages parsed               : {len(pages)}")
    print(f"Divider pages removed      : {len(skipped_page_nums)} -> {skipped_page_nums}")
    print(f"Headings detected          : {heading_count}")
    print(f"Continuation-marker pages  : {len(cont_pages)} -> {cont_pages}")
    print(f"Raw chunks (pre-merge)     : {len(raw_chunks)}")
    print(f"Sections after merge       : {len(merged)}")
    print(f"Tiny fragments skipped     : {tiny_skipped}")
    print(f"Total chunks produced      : {len(all_chunks)}")
    print("Chunks by content_type     :")
    for k, v in type_counts.most_common():
        print(f"    {k:22s} {v}")
    print(f"\nWrote: {config.OUTPUT_JSON}")
    print(f"Wrote: {config.OUTPUT_JSONL}")
    print(f"Wrote: {config.OUTPUT_REPORT}")


if __name__ == "__main__":
    main()