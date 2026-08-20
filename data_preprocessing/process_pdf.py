"""correct one so far
PEL PDF Document Processor (Phase 1: Data Preparation) — Google Colab T4
========================================================================
Best-of-both merge:
  • Local VLM (Qwen2-VL-7B-Instruct, 4-bit) — zero API cost, runs on T4
  • PaddleOCR bug FIXED — uses correct .ocr() API
  • OCR text CLEANING — auto-fixes 11OO→1100, Voltaee→Voltage, etc.
  • Smart VLM prompts — asks for markdown tables on spec pages
  • Google Drive paths + disk cache — survives Colab runtime resets
  • Just paste into a Colab cell and run. No other setup needed.

Outputs (saved to your Drive):
  - output_folder_for_pel/<pdf>_structured.json
  - output_folder_for_pel/<pdf>_full.md
  - output_folder_for_pel/<pdf>_flat.txt
  - output_folder_for_pel/<pdf>_summary.json
"""

import os
import sys
import io
import json
import re
import hashlib
import tempfile
from pathlib import Path
from datetime import datetime

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, EasyOcrOptions
from docling_core.types.doc import TextItem

from PIL import Image


# ==================================================================
# CONFIG
# ==================================================================

# --- VLM ---
VLM_MODE = "auto"   # "auto" | "always" | "off"
VLM_MODEL_ID = "Qwen/Qwen2-VL-7B-Instruct"
# VLM_MODEL_ID = "Qwen/Qwen2-VL-2B-Instruct"  # uncomment if 7B OOMs on T4
VLM_USE_4BIT = True
VLM_MIN_PICTURE_AREA_PX = 130 * 130
VLM_AUTO_MIN_OCR_CHARS = 250
VLM_MAX_CONTEXT_CHARS = 600
VLM_MAX_NEW_TOKENS = 400

# --- PaddleOCR ---
PADDLE_FALLBACK_MODE = "auto"   # "auto" | "always" | "off"
MIN_ACCEPTABLE_DOCLING_CHARS = 8
UPSCALE_MIN_SHORT_SIDE = 640
UPSCALE_MAX_SCALE = 3.0
PADDLE_MIN_LINE_CONFIDENCE = 0.5

# --- Paths (Google Drive) ---
INPUT_DIR = Path("/content/drive/MyDrive/PEL_RAG/input_folder_for_pel")
OUTPUT_DIR = Path("/content/drive/MyDrive/PEL_RAG/output_folder_for_pel")
VLM_CACHE_DIR = Path("/content/drive/MyDrive/PEL_RAG/vlm_cache")

# --- Docling ---
OCR_MODE = "pdf_aware_layout_regions"


# ==================================================================
# OCR TEXT CLEANING — applied to ALL text before saving
# ==================================================================

OCR_CORRECTIONS = [
    # Model numbers: letter O / o instead of digit 0
    (r'\b11OO\b', '1100'),
    (r'\b11[oO][oO]\b', '1100'),
    (r'\b14OO\b', '1400'),
    (r'\b14[oO][oO]\b', '1400'),
    (r'\bPRLP\s+11OO', 'PRLP 1100'),
    (r'\bPRLP\s+14OO', 'PRLP 1400'),
    (r'\bPRGD\s+14OO', 'PRGD 1400'),
    (r'\bPRUP\s+2550', 'PRUP 2550'),

    # Common word misreads
    (r'\bVoltaee\b', 'Voltage'),
    (r'\bVoltaee/Frequency\b', 'Voltage/Frequency'),
    (r'\bWelght\b', 'Weight'),
    (r'\bGross\s+Welght\b', 'Gross Weight'),
    (r'\bNet\s+Welght\b', 'Net Weight'),
    (r'\bConsumptlon\b', 'Consumption'),
    (r'\bPower\s+Consumptlon\b', 'Power Consumption'),
    (r'\bCurrent\s+Consumptlon\b', 'Current Consumption'),
    (r'\bMechankcal\b', 'Mechanical'),
    (r'\bNatujal\b', 'Natural'),
    (r'\bAvallable\b', 'Available'),
    (r'\bClmate\b', 'Climate'),
    (r'\bDefrostine\b', 'Defrosting'),
    (r'\bHeleht\b', 'Height'),
    (r'\bCablnet\b', 'Cabinet'),
    (r'\bWlthout\b', 'Without'),
    (r'\bWlre\b', 'Wire'),
    (r'\bChlld\b', 'Child'),
    (r'\bLockwlth\b', 'Lock with'),
    (r'\bKex\b', 'Key'),
    (r'\bHumldlty\b', 'Humidity'),
    (r'\bHumldity\b', 'Humidity'),
    (r'\bRefrlgerator\b', 'Refrigerator'),
    (r'\bRefrleerant\b', 'Refrigerant'),
    (r'\bEvaporator\b', 'Evaporator'),
    (r'\bCondenser\b', 'Condenser'),
    (r'\bCoollng\b', 'Cooling'),
    (r'\bFreezine\b', 'Freezing'),
    (r'\bAdjustable\b', 'Adjustable'),
    (r'\bTemperature\s+Control\b', 'Temperature Control'),
    (r'\bStart\s+Rating\b', 'Star Rating'),

    # Units
    (r'\bUters\b', 'Liters'),
    (r'\bLlters\b', 'Liters'),
    (r'\bLters\b', 'Liters'),
    (r'\bLiters\b', 'Liters'),
    (r'\bAmperes\b', 'Ampere'),
    (r'\bAm pere\b', 'Ampere'),
    (r'\bAmpere\b', 'Ampere'),

    # Feature / brand names
    (r'\bPMi\b', 'PMI'),
    (r'\bINSTA\s*COOL\b', 'Insta Cool'),
    (r'\b@99\s*O\s*0\b', '99.9%'),
    (r'\b@99\.9%\b', '99.9%'),
    (r'\bRGOOa\b', 'R600a'),
    (r'\bR134a\b', 'R134a'),
    (r'\bRoll\s+Bonu\b', 'Roll Bond'),
    (r'\bTube\s+on\s+Shcet\b', 'Tube on Sheet'),

    # Table header fixes
    (r'\bUnlts\b', 'Units'),
    (r'\bDESCRIPTION\b', 'Description'),
    (r'\bPERFORMANCE\b', 'Performance'),
    (r'\bGENERAL FEATURES\b', 'General Features'),
    (r'\bDIMENSIONS\b', 'Dimensions'),
    (r'\bWEIGHT\b', 'Weight'),
    (r'\bINTERNAL\b', 'Internal'),
    (r'\bCAPACITY\b', 'Capacity'),

    # Spacing / compound fixes
    (r'\bFreezer\s*\n\s*Capacity\b', 'Freezer Capacity'),
    (r'\bRefrigerator\s*\n\s*Capacity\b', 'Refrigerator Capacity'),
    (r'\bChlld\s+Lockwlth\s+Kex\b', 'Child Lock with Key'),
    (r'\bShelves\s+Type\b', 'Shelves Type'),
    (r'\bCrispo\s+Tray\b', 'Crispo Tray'),
]


def clean_ocr_text(text: str) -> str:
    """Apply regex-based corrections to fix systematic OCR errors."""
    if not text:
        return text
    for pattern, replacement in OCR_CORRECTIONS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    text = re.sub(r' {2,}', ' ', text)
    return text


# ==================================================================
# PICTURE OCR — PaddleOCR fallback (FIXED API)
# ==================================================================

_paddle_engine = None


def get_paddle_engine():
    global _paddle_engine
    if _paddle_engine is None:
        from paddleocr import PaddleOCR
        _paddle_engine = PaddleOCR(
            lang="en",
            use_angle_cls=True,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            show_log=False,
        )
    return _paddle_engine


def looks_like_garbage(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 2:
        return True
    alnum_ratio = sum(c.isalnum() for c in stripped) / len(stripped)
    return alnum_ratio < 0.4


def run_paddle_ocr(pil_image: Image.Image, min_conf: float = PADDLE_MIN_LINE_CONFIDENCE):
    """FIXED: uses correct PaddleOCR .ocr() API."""
    engine = get_paddle_engine()
    with tempfile.TemporaryDirectory() as td:
        tmp_path = os.path.join(td, "crop.png")
        pil_image.save(tmp_path)
        results = engine.ocr(tmp_path, cls=True)

        kept_texts, kept_scores = [], []
        dropped_count = 0

        if results and results[0]:
            for line in results[0]:
                if line is None:
                    continue
                box, (text, score) = line
                text = text.strip()
                if not text:
                    continue
                if score >= min_conf and not looks_like_garbage(text):
                    kept_texts.append(text)
                    kept_scores.append(score)
                else:
                    dropped_count += 1

    if dropped_count:
        print(f"    [OCR] Dropped {dropped_count} low-confidence/garbage line(s)")

    text = "\n".join(kept_texts)
    mean_conf = (sum(kept_scores) / len(kept_scores)) if kept_scores else 0.0
    return text, mean_conf


def maybe_upscale(pil_image: Image.Image) -> Image.Image:
    w, h = pil_image.size
    short_side = min(w, h)
    if short_side == 0:
        return pil_image
    scale = min(UPSCALE_MAX_SCALE, max(1.0, UPSCALE_MIN_SHORT_SIDE / short_side))
    if scale > 1.05:
        return pil_image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    return pil_image


# ==================================================================
# LOCAL VLM — Qwen2-VL (lazy-loaded, 4-bit, disk-cached on Drive)
# ==================================================================

_vlm_model = None
_vlm_processor = None


def get_vlm():
    """Load Qwen2-VL once, keep resident on GPU. First call is slow."""
    global _vlm_model, _vlm_processor
    if _vlm_model is None:
        import torch
        from transformers import Qwen2VLForConditionalGeneration, AutoProcessor, BitsAndBytesConfig

        print(f">>> Loading local VLM: {VLM_MODEL_ID} ...")
        print(">>> This takes 3-5 minutes on first run (download + 4-bit quant)...")

        quant_kwargs = {}
        if VLM_USE_4BIT:
            quant_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
            )

        _vlm_model = Qwen2VLForConditionalGeneration.from_pretrained(
            VLM_MODEL_ID,
            torch_dtype=torch.float16,
            device_map="auto",
            trust_remote_code=True,
            **quant_kwargs,
        )
        _vlm_processor = AutoProcessor.from_pretrained(VLM_MODEL_ID, trust_remote_code=True)
        print(">>> VLM loaded successfully.\n")
    return _vlm_model, _vlm_processor


def is_likely_table_image(page_context: str) -> bool:
    """Heuristic: if page mentions specs, image might be a table."""
    ctx = (page_context or "").lower()
    keywords = ["specification", "technical", "dimension", "capacity", "voltage",
                "power consumption", "weight", "model", "table", "description"]
    return any(kw in ctx for kw in keywords)


def describe_picture_with_vlm(pil_image: Image.Image, page_context: str, ocr_hint: str):
    """Run Qwen2-VL locally. Returns description string or None."""
    buf = io.BytesIO()
    pil_image.convert("RGB").save(buf, format="PNG")
    img_bytes = buf.getvalue()
    cache_key = hashlib.sha256(img_bytes).hexdigest()
    VLM_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = VLM_CACHE_DIR / f"{cache_key}.txt"
    if cache_path.exists():
        cached = cache_path.read_text(encoding="utf-8").strip()
        return cached or None

    try:
        model, processor = get_vlm()
        from qwen_vl_utils import process_vision_info
    except Exception as e:
        print(f"    [WARN] Could not load local VLM: {e}")
        return None

    likely_table = is_likely_table_image(page_context)
    table_instruction = ""
    if likely_table:
        table_instruction = (
            "\nIMPORTANT: This image appears to contain a data table or specification grid. "
            "If so, ALSO output the data as a markdown table with proper columns and rows, "
            "in addition to your prose description. Preserve exact numbers and model codes.\n"
        )

    prompt_text = (
        "You are helping build a searchable knowledge base from a PEL (Pakistan Electronics Limited) "
        "refrigerator and AC service-technician training manual.\n\n"
        f"Same-page context (headings, nearby text):\n{page_context or '(none available)'}\n\n"
        f"OCR text already detected inside this image (may contain misreads — use as hint only):\n{ocr_hint or '(none)'}\n\n"
        "Write 2-4 connected sentences describing what this image shows. Explicitly state:\n"
        "- What product/series this is\n"
        "- Model numbers visible, tied to colors/features\n"
        "- Color options and their names\n"
        "- Feature badges or callouts (energy saving, cooling tech, etc.)\n"
        f"{table_instruction}"
        "If this is a wiring diagram or schematic, describe components and connections.\n"
        "Do NOT invent digits you cannot read clearly.\n"
        "Return ONLY the description, no preamble or labels."
    )

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "image", "image": pil_image.convert("RGB")},
                {"type": "text", "text": prompt_text},
            ],
        }
    ]

    try:
        text = processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        ).to(model.device)

        generated_ids = model.generate(**inputs, max_new_tokens=VLM_MAX_NEW_TOKENS)
        generated_ids_trimmed = [
            out_ids[len(in_ids):]
            for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        description = processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True,
            clean_up_tokenization_spaces=False,
        )[0].strip()
    except Exception as e:
        print(f"    [WARN] Local VLM inference failed: {e}")
        return None

    if description:
        cache_path.write_text(description, encoding="utf-8")
    return description or None


def should_run_vlm(pil_img, docling_text: str, paddle_text: str) -> bool:
    if VLM_MODE == "off" or pil_img is None:
        return False
    w, h = pil_img.size
    if w * h < VLM_MIN_PICTURE_AREA_PX:
        return False
    if VLM_MODE == "always":
        return True
    combined_len = len((docling_text or "").strip()) + len((paddle_text or "").strip())
    return combined_len < VLM_AUTO_MIN_OCR_CHARS


# ==================================================================
# PICTURE ENTRY BUILDER — Docling OCR + PaddleOCR + VLM
# ==================================================================

def get_docling_nested_text(picture_item, doc) -> str:
    lines = []
    try:
        for child, _level in doc.iterate_items(root=picture_item, traverse_pictures=True):
            if isinstance(child, TextItem):
                t = (child.text or "").strip()
                if t:
                    lines.append(t)
    except Exception:
        pass
    return "\n".join(lines)


def build_picture_entry(picture_item, doc, page_context: str = ""):
    """Three-tier: Docling OCR → PaddleOCR → VLM description."""
    # Caption
    caption = None
    try:
        if hasattr(picture_item, "caption_text"):
            caption = picture_item.caption_text(doc)
            caption = caption.strip() if caption else None
    except Exception:
        pass

    # Tier 1: Docling nested OCR
    docling_text = get_docling_nested_text(picture_item, doc)
    docling_ok = len(docling_text.strip()) >= MIN_ACCEPTABLE_DOCLING_CHARS

    # Get image
    pil_img = None
    try:
        pil_img = picture_item.get_image(doc)
    except Exception:
        pass
    pil_img_upscaled = maybe_upscale(pil_img) if pil_img is not None else None

    # Tier 2: PaddleOCR fallback
    paddle_text, paddle_conf = "", 0.0
    should_try_paddle = PADDLE_FALLBACK_MODE == "always" or (
        PADDLE_FALLBACK_MODE == "auto" and not docling_ok
    )
    if should_try_paddle and pil_img_upscaled is not None:
        try:
            paddle_text, paddle_conf = run_paddle_ocr(pil_img_upscaled)
        except Exception as e:
            print(f"    [WARN] PaddleOCR failed: {e}")

    # Pick best OCR
    if len(paddle_text.strip()) > len(docling_text.strip()):
        ocr_text = paddle_text
        ocr_source = "paddleocr"
        ocr_confidence = round(paddle_conf, 3) if paddle_text.strip() else None
    elif docling_ok:
        ocr_text = docling_text
        ocr_source = "docling"
        ocr_confidence = None
    else:
        ocr_text = paddle_text or docling_text
        ocr_source = "paddleocr" if paddle_text.strip() else ("docling" if docling_text.strip() else "none")
        ocr_confidence = round(paddle_conf, 3) if paddle_text.strip() else None

    # Clean OCR text
    ocr_text = clean_ocr_text(ocr_text)

    # Tier 3: VLM description
    vlm_description = None
    used_vlm = should_run_vlm(pil_img, docling_text, paddle_text)
    if used_vlm:
        vlm_description = describe_picture_with_vlm(
            pil_img_upscaled or pil_img, page_context, ocr_text
        )
        used_vlm = vlm_description is not None

    # Assemble
    parts = []
    if caption:
        parts.append(f"[CAPTION] {clean_ocr_text(caption)}")
    if vlm_description:
        parts.append(f"[IMAGE DESCRIPTION] {vlm_description}")
    if ocr_text.strip():
        parts.append(f"[TEXT IN IMAGE] {ocr_text.strip()}")

    content = "\n".join(parts) if parts else "[No extractable content found in image]"
    return content, ocr_source, ocr_confidence, used_vlm


# ==================================================================
# READING ORDER FIX — Recursive XY-Cut
# ==================================================================

def get_projection_gaps(intervals):
    if not intervals:
        return []
    intervals = sorted(intervals)
    merged = [list(intervals[0])]
    for low, high in intervals[1:]:
        if low <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], high)
        else:
            merged.append([low, high])
    gaps = []
    for i in range(len(merged) - 1):
        gaps.append((merged[i][1], merged[i + 1][0]))
    return gaps


def xy_cut(items, min_gap=3.0, depth=0, max_depth=25):
    if len(items) <= 1:
        return items
    if depth >= max_depth:
        return sorted(items, key=lambda it: (-it["bbox"]["t"], it["bbox"]["l"]))

    y_intervals = [(it["bbox"]["b"], it["bbox"]["t"]) for it in items]
    y_gaps = [g for g in get_projection_gaps(y_intervals) if g[1] - g[0] >= min_gap]
    best_y = max(y_gaps, key=lambda g: g[1] - g[0]) if y_gaps else None

    x_intervals = [(it["bbox"]["l"], it["bbox"]["r"]) for it in items]
    x_gaps = [g for g in get_projection_gaps(x_intervals) if g[1] - g[0] >= min_gap]
    best_x = max(x_gaps, key=lambda g: g[1] - g[0]) if x_gaps else None

    y_size = (best_y[1] - best_y[0]) if best_y else -1
    x_size = (best_x[1] - best_x[0]) if best_x else -1

    def try_horizontal():
        cut = (best_y[0] + best_y[1]) / 2
        top = [it for it in items if it["bbox"]["b"] >= cut]
        bottom = [it for it in items if it["bbox"]["t"] <= cut]
        if top and bottom and len(top) < len(items) and len(bottom) < len(items):
            return xy_cut(top, min_gap, depth + 1, max_depth) + xy_cut(bottom, min_gap, depth + 1, max_depth)
        return None

    def try_vertical():
        cut = (best_x[0] + best_x[1]) / 2
        left = [it for it in items if it["bbox"]["r"] <= cut]
        right = [it for it in items if it["bbox"]["l"] >= cut]
        if left and right and len(left) < len(items) and len(right) < len(items):
            return xy_cut(left, min_gap, depth + 1, max_depth) + xy_cut(right, min_gap, depth + 1, max_depth)
        return None

    if y_size >= x_size and best_y:
        out = try_horizontal()
        if out is not None:
            return out
        if best_x:
            out = try_vertical()
            if out is not None:
                return out
    elif best_x:
        out = try_vertical()
        if out is not None:
            return out
        if best_y:
            out = try_horizontal()
            if out is not None:
                return out

    return sorted(items, key=lambda it: (-it["bbox"]["t"], it["bbox"]["l"]))


def fix_reading_order(structured_items):
    by_page = {}
    page_order = []
    for it in structured_items:
        p = it["page"]
        if p not in by_page:
            by_page[p] = {"with_bbox": [], "without_bbox": []}
            page_order.append(p)
        if it["bbox"]:
            by_page[p]["with_bbox"].append(it)
        else:
            by_page[p]["without_bbox"].append(it)

    result = []
    for p in page_order:
        ordered = xy_cut(by_page[p]["with_bbox"])
        ordered += by_page[p]["without_bbox"]
        result.extend(ordered)

    for i, it in enumerate(result, start=1):
        it["reading_order_index"] = i

    return result


# ==================================================================
# PAGE CONTEXT — for VLM grounding
# ==================================================================

def build_page_text_context(doc):
    context = {}
    for item, _level in doc.iterate_items():
        label = str(item.label) if hasattr(item, "label") else "unknown"
        if label in ("picture", "image"):
            continue
        prov_list = getattr(item, "prov", None)
        if not prov_list:
            continue
        page_no = prov_list[0].page_no if hasattr(prov_list[0], "page_no") else None
        if page_no is None:
            continue
        if label == "table":
            snippet = "[a technical specification table is on this page]"
        else:
            snippet = (getattr(item, "text", "") or "").strip()
        if snippet:
            context.setdefault(page_no, []).append(snippet)
    return {p: " | ".join(lines)[:VLM_MAX_CONTEXT_CHARS] for p, lines in context.items()}


# ==================================================================
# MAIN PROCESSING
# ==================================================================

def parse_page_range(pages_str):
    if not pages_str:
        return None
    parts = pages_str.split("-")
    if len(parts) != 2:
        return None
    return (int(parts[0]), int(parts[1]))


def process_pdf(pdf_path, output_dir, page_range=None):
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        import docling
        print(f">>> Docling version: {getattr(docling, '__version__', 'unknown')}")
    except Exception:
        pass

    print(f"\n>>> Processing: {pdf_path.name}")
    print(f">>> VLM mode: {VLM_MODE} (model: {VLM_MODEL_ID})")
    print(">>> First run downloads Docling models (~1-2 GB) and VLM (~15 GB)...")
    print(">>> This may take 10-20 minutes total. Subsequent runs are much faster.\n")

    # 1. Configure Docling
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.generate_picture_images = True
    pipeline_options.images_scale = 3.0
    pipeline_options.ocr_options = EasyOcrOptions(mode=OCR_MODE)

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )

    # 2. Convert PDF
    if page_range:
        print(f">>> Restricting to page range {page_range} (test mode)\n")
        result = converter.convert(pdf_path, page_range=page_range)
    else:
        result = converter.convert(pdf_path)
    doc = result.document

    num_pages = len(doc.pages) if hasattr(doc, "pages") and doc.pages else 0
    print(f">>> Detected {num_pages} pages.\n")

    # 2b. Page context for VLM
    page_text_context = build_page_text_context(doc) if VLM_MODE != "off" else {}

    print(">>> Building structured extraction...\n")

    # 3. Iterate and build structured data
    structured_items = []
    vlm_call_count = 0

    for item, level in doc.iterate_items():
        entry = {
            "reading_order_index": None,
            "level": level,
            "type": None,
            "label": str(item.label) if hasattr(item, "label") else "unknown",
            "page": None,
            "content": "",
            "bbox": None,
        }

        prov_list = getattr(item, "prov", None)
        if prov_list and len(prov_list) > 0:
            prov = prov_list[0]
            entry["page"] = prov.page_no if hasattr(prov, "page_no") else None
            if hasattr(prov, "bbox") and prov.bbox:
                entry["bbox"] = {
                    "l": round(prov.bbox.l, 2), "t": round(prov.bbox.t, 2),
                    "r": round(prov.bbox.r, 2), "b": round(prov.bbox.b, 2),
                }

        if entry["label"] == "table":
            entry["type"] = "table"
            try:
                df = item.export_to_dataframe(doc=doc)
                md_table = df.to_markdown(index=False)
                entry["content"] = clean_ocr_text(md_table)
            except Exception as e:
                raw = getattr(item, "text", str(item))
                entry["content"] = clean_ocr_text(
                    f"[TABLE EXTRACTION PARTIAL — fallback text]\n{raw}\n[Error: {e}]"
                )

        elif entry["label"] in ("picture", "image"):
            entry["type"] = "image"
            page_context = page_text_context.get(entry["page"], "")
            content, ocr_source, ocr_confidence, used_vlm = build_picture_entry(
                item, doc, page_context=page_context
            )
            entry["content"] = content
            entry["ocr_source"] = ocr_source
            if ocr_confidence is not None:
                entry["ocr_confidence"] = ocr_confidence
            entry["used_vlm"] = used_vlm
            if used_vlm:
                vlm_call_count += 1
                print(f"    [VLM] Described picture on page {entry['page']} (#{vlm_call_count})")

        else:
            entry["type"] = "text"
            raw_text = getattr(item, "text", str(item))
            entry["content"] = clean_ocr_text(raw_text)

        structured_items.append(entry)

    # 3b. Fix reading order
    structured_items = fix_reading_order(structured_items)

    # 4. Build flat text
    flat_lines = []
    current_page = None
    for entry in structured_items:
        if entry["page"] != current_page:
            current_page = entry["page"]
            flat_lines.append(f"\n{'='*70}\n--- PAGE {current_page} ---\n{'='*70}\n")
        flat_lines.append(f"[{entry['label'].upper()} | level={entry['level']}]\n{entry['content']}\n")
    flat_text = "\n".join(flat_lines)

    # 5. Build markdown
    md_lines = []
    current_page = None
    for entry in structured_items:
        if entry["page"] != current_page:
            current_page = entry["page"]
            md_lines.append("\n---\n\n")
            md_lines.append(f"**PAGE {current_page}**\n\n")

        label = (entry.get("label") or "").lower()
        typ = entry.get("type")
        level = entry.get("level") or 0
        content = entry.get("content", "")

        if label in ("section_header", "heading", "title"):
            heading_level = min(6, max(1, level + 1))
            md_lines.append(f"{('#' * heading_level)} {content}\n\n")
        elif label in ("list_item", "bullet", "list"):
            indent = "  " * max(0, level - 1)
            stripped = content.lstrip()
            if stripped and stripped[0] in ("-", "*", "➢", "❑", "•"):
                md_lines.append(f"{indent}{content}\n")
            else:
                md_lines.append(f"{indent}- {content}\n")
        elif typ == "table":
            md_lines.append(content + "\n\n")
        elif typ == "image":
            md_lines.append("**[IMAGE]**\n\n")
            md_lines.append(content + "\n\n")
        else:
            md_lines.append(content + "\n\n")

    full_markdown = "".join(md_lines)

    # 6. Save outputs
    base_name = pdf_path.stem

    json_path = output_dir / f"{base_name}_structured.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "source_pdf": pdf_path.name,
            "total_pages": num_pages,
            "extraction_date": datetime.now().isoformat(),
            "total_items": len(structured_items),
            "vlm_model": VLM_MODEL_ID,
            "vlm_calls_made": vlm_call_count,
            "items": structured_items,
        }, f, ensure_ascii=False, indent=2)

    md_path = output_dir / f"{base_name}_full.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# {base_name}\n\n")
        f.write(f"**Source:** {pdf_path.name}  \n")
        f.write(f"**Pages:** {num_pages}  \n")
        f.write(f"**Extracted:** {datetime.now().isoformat()}  \n")
        f.write(f"**VLM:** {VLM_MODEL_ID} ({vlm_call_count} calls)  \n\n")
        f.write("---\n\n")
        f.write(full_markdown)

    txt_path = output_dir / f"{base_name}_flat.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(flat_text)

    breakdown = {}
    for entry in structured_items:
        lbl = entry["label"]
        breakdown[lbl] = breakdown.get(lbl, 0) + 1

    summary_path = output_dir / f"{base_name}_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "source_pdf": pdf_path.name,
            "total_pages": num_pages,
            "total_items": len(structured_items),
            "item_breakdown": breakdown,
            "vlm_model": VLM_MODEL_ID,
            "vlm_calls_made": vlm_call_count,
        }, f, ensure_ascii=False, indent=2)

    # 7. Report
    print("=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)
    print(f"Output folder : {output_dir.resolve()}")
    print(f"  1. Structured JSON : {json_path.name}")
    print(f"  2. Full Markdown   : {md_path.name}")
    print(f"  3. Flat Text       : {txt_path.name}")
    print(f"  4. Summary         : {summary_path.name}")
    print("\n--- Item Breakdown ---")
    for lbl, cnt in sorted(breakdown.items(), key=lambda x: -x[1]):
        print(f"  {lbl:20s} : {cnt}")
    print(f"\nVLM descriptions: {vlm_call_count} ({VLM_MODEL_ID})")
    print(f"Total items: {len(structured_items)}")
    print("=" * 70)


# ==================================================================
# COLAB ENTRY POINT — paste this entire file into one cell and run
# ==================================================================

if __name__ == "__main__":

    # ================================================================
    # 0. MOUNT GOOGLE DRIVE (if not already mounted)
    # ================================================================
    try:
        from google.colab import drive
        drive.mount('/content/drive', force_remount=False)
        print("Google Drive mounted.\n")
    except ImportError:
        print("[INFO] Not running in Colab — skipping Drive mount.\n")
    except Exception as e:
        print(f"[WARN] Drive mount issue: {e}\n")

    # ================================================================
    # GOOGLE DRIVE PATHS
    # ================================================================
    INPUT_DIR = Path("/content/drive/MyDrive/PEL_RAG/input_folder_for_pel")
    OUTPUT_DIR = Path("/content/drive/MyDrive/PEL_RAG/output_folder_for_pel")

    # ================================================================
    # OPTIONAL PAGE RANGE
    # ================================================================
    # None = process the complete PDF
    # PAGE_RANGE = (1, 20)
    PAGE_RANGE = (1,20)

    # ================================================================
    # CHECK INPUT FOLDER
    # ================================================================
    if not INPUT_DIR.exists():
        print(f"\n[ERROR] Input folder not found:")
        print(f"        {INPUT_DIR}")
        print("\nPlease create this folder in your Google Drive and upload your PDF.")
        sys.exit(1)

    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ================================================================
    # FIND PDF
    # ================================================================
    pdf_files = list(INPUT_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"\n[ERROR] No PDF files found in:")
        print(f"        {INPUT_DIR}")
        print("\nPlease place your PEL PDF inside that folder.")
        sys.exit(1)

    if len(pdf_files) > 1:
        print(f"[WARNING] Multiple PDFs found. Processing the first one: {pdf_files[0].name}\n")

    pdf_path = pdf_files[0]

    # ================================================================
    # START PROCESSING
    # ================================================================
    print("=" * 70)
    print("PEL DOCUMENT PROCESSOR — GOOGLE COLAB (Best Merge)")
    print("=" * 70)
    print(f"Input folder : {INPUT_DIR}")
    print(f"PDF          : {pdf_path.name}")
    print(f"Output folder: {OUTPUT_DIR}")
    print(f"Page range   : {PAGE_RANGE if PAGE_RANGE else 'FULL DOCUMENT'}")
    print(f"VLM model    : {VLM_MODEL_ID} ({'4-bit' if VLM_USE_4BIT else 'full'})")
    print("=" * 70)

    process_pdf(pdf_path=pdf_path, output_dir=OUTPUT_DIR, page_range=PAGE_RANGE)