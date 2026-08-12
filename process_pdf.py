"""
PEL PDF Document Processor (Phase 1: Data Preparation)
======================================================
This script takes a PDF from the input/ folder, runs Docling with OCR and
table extraction, and saves structured outputs to the output/ folder.

Outputs:
  - <pdf_name>_structured.json : Clean array of items with page numbers, labels, text
  - <pdf_name>_full.md         : Full document markdown export
  - <pdf_name>_flat.txt        : Flat text with clear PAGE markers
  - <pdf_name>_summary.json    : Extraction stats and item counts

Run:
  python process_pdf.py
  python process_pdf.py -i my_input -o my_output
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions


def process_pdf(pdf_path: str, output_dir: str):
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n>>> Processing: {pdf_path.name}")
    print(">>> This may take 5–15 minutes for 188 pages with OCR + table extraction...")
    print(">>> First run will download Docling AI models (~1–2 GB).\n")

    # ------------------------------------------------------------------
    # 1. Configure Docling pipeline
    # ------------------------------------------------------------------
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True               # Extract text from images / scanned pages
    pipeline_options.do_table_structure = True   # Reconstruct table rows & columns
    # pipeline_options.generate_picture_images = True  # Uncomment if you also want image files

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    # ------------------------------------------------------------------
    # 2. Convert PDF
    # ------------------------------------------------------------------
    result = converter.convert(pdf_path)
    doc = result.document

    num_pages = len(doc.pages) if hasattr(doc, "pages") and doc.pages else 0
    print(f">>> Detected {num_pages} pages. Building structured extraction...\n")

    # ------------------------------------------------------------------
    # 3. Iterate document in reading order and build structured data
    # ------------------------------------------------------------------
    structured_items = []

    for item, level in doc.iterate_items():
        entry = {
            "reading_order_index": len(structured_items) + 1,
            "level": level,
            "type": None,
            "label": str(item.label) if hasattr(item, "label") else "unknown",
            "page": None,
            "content": "",
            "bbox": None,
        }

        # --- Provenance (page number + bounding box) ---
        prov_list = getattr(item, "prov", None)
        if prov_list and len(prov_list) > 0:
            prov = prov_list[0]
            entry["page"] = prov.page_no if hasattr(prov, "page_no") else None
            if hasattr(prov, "bbox") and prov.bbox:
                entry["bbox"] = {
                    "l": round(prov.bbox.l, 2),
                    "t": round(prov.bbox.t, 2),
                    "r": round(prov.bbox.r, 2),
                    "b": round(prov.bbox.b, 2),
                }

        # --- Content extraction by type ---
        if entry["label"] == "table":
            entry["type"] = "table"
            try:
                df = item.export_to_dataframe(doc=doc)
                entry["content"] = df.to_markdown(index=False)
            except Exception as e:
                # Fallback: raw text if dataframe fails
                raw = getattr(item, "text", str(item))
                entry["content"] = f"[TABLE EXTRACTION PARTIAL — fallback text]\n{raw}\n[Error: {e}]"

        elif entry["label"] in ("picture", "image"):
            entry["type"] = "image"
            parts = []
            caption = getattr(item, "caption_text", None)
            if caption:
                parts.append(f"Image caption: {caption}")
            # If Docling produced OCR text as part of the picture node
            raw_text = getattr(item, "text", None)
            if raw_text:
                parts.append(f"Extracted text from image: {raw_text}")
            entry["content"] = "\n".join(parts) if parts else "[Image detected — no extractable text]"

        else:
            # paragraph, heading, section_header, caption, list_item, etc.
            entry["type"] = "text"
            entry["content"] = getattr(item, "text", str(item))

        structured_items.append(entry)

    # ------------------------------------------------------------------
    # 4. Build flat text with explicit PAGE markers (easy for quick search)
    # ------------------------------------------------------------------
    flat_lines = []
    current_page = None
    for entry in structured_items:
        if entry["page"] != current_page:
            current_page = entry["page"]
            flat_lines.append(f"\n{'='*70}\n--- PAGE {current_page} ---\n{'='*70}\n")
        flat_lines.append(f"[{entry['label'].upper()} | level={entry['level']}]\n{entry['content']}\n")
    flat_text = "\n".join(flat_lines)

    # ------------------------------------------------------------------
    # 5. Export full markdown (human readable, preserves structure)
    # ------------------------------------------------------------------
    full_markdown = doc.export_to_markdown()

    # ------------------------------------------------------------------
    # 6. Save all outputs
    # ------------------------------------------------------------------
    base_name = pdf_path.stem

    # 6a. Structured JSON (main artifact for next phases)
    json_path = output_dir / f"{base_name}_structured.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "source_pdf": pdf_path.name,
                "total_pages": num_pages,
                "extraction_date": datetime.now().isoformat(),
                "total_items": len(structured_items),
                "items": structured_items,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    # 6b. Full Markdown
    md_path = output_dir / f"{base_name}_full.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# {base_name}\n\n")
        f.write(f"**Source:** {pdf_path.name}  \n")
        f.write(f"**Pages:** {num_pages}  \n")
        f.write(f"**Extracted:** {datetime.now().isoformat()}  \n\n")
        f.write("---\n\n")
        f.write(full_markdown)

    # 6c. Flat text with page markers
    txt_path = output_dir / f"{base_name}_flat.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(flat_text)

    # 6d. Summary report
    breakdown = {}
    for entry in structured_items:
        lbl = entry["label"]
        breakdown[lbl] = breakdown.get(lbl, 0) + 1

    summary_path = output_dir / f"{base_name}_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "source_pdf": pdf_path.name,
                "total_pages": num_pages,
                "total_items": len(structured_items),
                "item_breakdown": breakdown,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    # ------------------------------------------------------------------
    # 7. Print report
    # ------------------------------------------------------------------
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
    print(f"\nTotal items extracted: {len(structured_items)}")
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PEL PDF Document Processor — Phase 1")
    parser.add_argument("--input", "-i", default="input", help="Folder containing the PDF (default: input/)")
    parser.add_argument("--output", "-o", default="output", help="Folder to save results (default: output/)")
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output)

    if not input_dir.exists():
        print(f"\n[ERROR] Input folder not found: {input_dir}")
        print("Please create an 'input' folder and place your PEL PDF inside it.\n")
        sys.exit(1)

    pdf_files = list(input_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"\n[ERROR] No PDF files found in: {input_dir}")
        print("Please place your 188-page PEL PDF in the input folder.\n")
        sys.exit(1)

    if len(pdf_files) > 1:
        print(f"[WARNING] Multiple PDFs found. Processing the first one: {pdf_files[0].name}\n")

    process_pdf(pdf_files[0], output_dir)