"""
PEL PDF → Clean Markdown via Gemini (Incremental + Auto-Combine)
================================================================
- Processes only the pages you request
- Automatically combines ALL previously extracted pages into one final .md
- Caching on Google Drive
"""

import os
import sys
import hashlib
import re
import time
from pathlib import Path
from datetime import datetime
from io import BytesIO

from PIL import Image
import pymupdf as fitz
from google.colab import userdata
from google import genai
from google.genai import types

# ==================================================================
# CONFIG
# ==================================================================
GEMINI_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash",
    "gemini-3-flash-preview",
    "gemini-3.5-flash-lite",
]

DPI = 220
PAGE_RANGE = (1, 15)               # ← change this each time (e.g. (16, 30))
MAX_RETRIES = 3
RETRY_DELAY = 6

INPUT_DIR  = Path("/content/drive/MyDrive/PEL_RAG/input_folder_for_pel")
OUTPUT_DIR = Path("/content/drive/MyDrive/PEL_RAG/output_folder_for_pel")
CACHE_DIR  = Path("/content/drive/MyDrive/PEL_RAG/gemini_page_cache")

# ==================================================================
# STRICT PROMPT
# ==================================================================
SYSTEM_PROMPT = """You are a STRICT OCR and visual document extraction engine for PEL (Pakistan Electronics Limited) technical service manuals.

Your ONLY job is to convert the given page image into clean, structured Markdown.

This is a CLOSED-WORLD extraction task.

CRITICAL RULES:
1. Output ONLY clean Markdown. Never say "this image shows", "the page contains", "I can see", etc.
2. Start directly with the real content.
3. Completely IGNORE and NEVER mention:
   - The "PEL Customer Care" logo
   - Any cartoon of workers / yellow hats
   - Decorative images, emojis, or branding that has no technical value
4. Extract ONLY what is explicitly visible in the image.
5. NEVER invent, infer, summarize, or add objectives, benefits, conclusions, extra headings, or explanations.
6. If there is a table:
   - Reproduce every visible row and column perfectly
   - Keep exact structure, numbers, model codes, units
   - Repeat values for merged/spanned cells
   - Use "-" only for truly empty cells
7. Model numbers are critical. Keep them exactly as written (e.g. PRLP 1100, PRGD 1400).
8. Preserve original language (English / Urdu / Chinese) exactly.
9. Do not paraphrase.
10. Structure with Markdown headings only when they are actually present on the page.

Output format for every page:

## PAGE {page_number}

(then the full clean content of the page)
"""

# ==================================================================
# SETUP
# ==================================================================
def setup_client():
    api_key = userdata.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("❌ GEMINI_API_KEY not found in Colab Secrets!")
    return genai.Client(api_key=api_key)

# ==================================================================
# RENDER PAGE
# ==================================================================
def render_page(pdf_path: Path, page_index: int, dpi: int = DPI) -> Image.Image:
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    doc.close()
    return img

# ==================================================================
# RUN GEMINI ON ONE PAGE
# ==================================================================
def run_gemini_on_page(client, pil_image: Image.Image, page_number: int) -> str:
    prompt = SYSTEM_PROMPT.replace("{page_number}", str(page_number))

    buffered = BytesIO()
    pil_image.convert("RGB").save(buffered, format="JPEG", quality=92)
    img_bytes = buffered.getvalue()

    for model_name in GEMINI_MODELS:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[
                        types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                        types.Part.from_text(text=prompt),
                    ],
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        max_output_tokens=8192,
                    )
                )

                result = response.text.strip()
                result = re.sub(
                    r'^(Here is the extracted content|The page contains|This page shows|Sure,? here).*?\n+',
                    '', result, flags=re.I
                )
                if not result.startswith("## PAGE"):
                    result = f"## PAGE {page_number}\n\n{result}"

                print(f"    ✓ Success with {model_name}")
                return result

            except Exception as e:
                err = str(e)
                print(f"    Attempt {attempt} with {model_name} failed: {err[:120]}...")
                if "404" in err or "not found" in err.lower() or "no longer available" in err.lower():
                    break
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)

    return f"## PAGE {page_number}\n\n[ERROR] All models failed for this page."

# ==================================================================
# HELPER: Collect ALL cached pages (for final combined file)
# ==================================================================
def collect_all_cached_pages(pdf_name: str, total_pages: int):
    """Return a list of markdown content for every page that already exists in cache, in order."""
    pages = []
    for page_num in range(1, total_pages + 1):
        cache_key = hashlib.sha256(
            f"{pdf_name}_{page_num}_{DPI}_gemini3".encode()
        ).hexdigest()
        cache_file = CACHE_DIR / f"{cache_key}.md"
        if cache_file.exists():
            content = cache_file.read_text(encoding="utf-8")
            pages.append(content)
            pages.append("\n\n---\n")
    return pages

# ==================================================================
# MAIN
# ==================================================================
def process_pdf(pdf_path: Path, output_dir: Path, page_range=None):
    output_dir.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    client = setup_client()

    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()

    start, end = 1, total_pages
    if page_range:
        start, end = page_range
        end = min(end, total_pages)

    print(f">>> Processing {pdf_path.name}")
    print(f">>> Requested pages: {start} → {end}  |  DPI: {DPI}")
    print(f">>> Models: {GEMINI_MODELS}\n")

    # ---------- Process only the requested range ----------
    for page_num in range(start, end + 1):
        print(f"--- Page {page_num}/{end} ---")

        cache_key = hashlib.sha256(
            f"{pdf_path.name}_{page_num}_{DPI}_gemini3".encode()
        ).hexdigest()
        cache_file = CACHE_DIR / f"{cache_key}.md"

        if cache_file.exists():
            print("    [CACHE HIT]")
        else:
            page_img = render_page(pdf_path, page_num - 1, dpi=DPI)
            content = run_gemini_on_page(client, page_img, page_num)
            cache_file.write_text(content, encoding="utf-8")
            print("    [DONE + CACHED]")

        time.sleep(1.2)

    # ---------- Build the COMPLETE combined file from all cached pages ----------
    print("\n>>> Building combined Markdown from ALL extracted pages...")
    all_md = collect_all_cached_pages(pdf_path.name, total_pages)

    if not all_md:
        print("No pages found in cache!")
        return None

    # Count how many real pages we have
    extracted_count = sum(1 for p in all_md if p.startswith("## PAGE"))

    final_md = f"""# {pdf_path.stem}

**Source:** {pdf_path.name}
**Total pages in PDF:** {total_pages}
**Pages extracted so far:** {extracted_count}
**Last update:** {datetime.now().isoformat()}
**Method:** Full-page Gemini @ {DPI} DPI

---

""" + "\n".join(all_md)

    out_path = output_dir / f"{pdf_path.stem}_CLEAN_GEMINI.md"
    out_path.write_text(final_md, encoding="utf-8")

    print("\n" + "="*70)
    print("EXTRACTION COMPLETE")
    print(f"Combined Markdown saved to:\n{out_path}")
    print(f"Total pages currently in the file: {extracted_count}")
    print("="*70)
    return out_path

# ==================================================================
# ENTRY
# ==================================================================
if __name__ == "__main__":
    from google.colab import drive
    drive.mount('/content/drive', force_remount=False)

    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pdfs = list(INPUT_DIR.glob("*.pdf"))
    if not pdfs:
        print("No PDF found in input folder")
        sys.exit(1)

    pdf_path = pdfs[0]
    print(f"Using: {pdf_path.name}")

    # ←←← CHANGE ONLY THIS LINE EACH TIME ←←←
    PAGE_RANGE = (151, 188)          # first run
    # PAGE_RANGE = (16, 30)       # second run
    # PAGE_RANGE = (31, 45)       # third run
    # PAGE_RANGE = None           # process everything remaining

    process_pdf(pdf_path, OUTPUT_DIR, page_range=PAGE_RANGE)