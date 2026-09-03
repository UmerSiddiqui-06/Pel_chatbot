"""Backend adapter for the fixed, pre-indexed PEL Phase 3 RAG pipeline."""
from pathlib import Path
import sys
from threading import Lock
from typing import TYPE_CHECKING, List, TypedDict
import re
from urllib.parse import quote

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if TYPE_CHECKING:
    from phase3_rag_engine import Phase3Pipeline


class SourceDict(TypedDict, total=False):
    title: str
    page: int
    section: str
    pageRange: str
    videoUrl: str


class AgentResult(TypedDict):
    answer: str
    sources: List[SourceDict]


_pipeline: "Phase3Pipeline | None" = None
_pipeline_lock = Lock()


def _get_pipeline() -> "Phase3Pipeline":
    global _pipeline
    if _pipeline is None:
        with _pipeline_lock:
            if _pipeline is None:
                from phase3_rag_engine import Phase3Pipeline

                _pipeline = Phase3Pipeline()
    return _pipeline


def initialize() -> None:
    """Load the Phase 3 indexes and model weights before serving requests."""
    print("\n🚀 Initializing PEL Phase 3 knowledge agent...", flush=True)
    _get_pipeline()
    print("✅ PEL Phase 3 knowledge agent is ready for queries", flush=True)


_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v"}
_PAGE_RANGE_RE = re.compile(r"(?<!\d)(\d+)(?:\s*-\s*(\d+))?(?!\d)")


def _find_video_for_page(page: object) -> tuple[str | None, str | None]:
    if not isinstance(page, int):
        return None, None

    video_dir = PROJECT_ROOT / "out"
    if not video_dir.is_dir():
        return None, None

    matches = []
    for path in video_dir.iterdir():
        if not path.is_file() or path.suffix.lower() not in _VIDEO_EXTENSIONS:
            continue
        page_match = list(_PAGE_RANGE_RE.finditer(path.stem))[-1:]
        if not page_match:
            continue
        match = page_match[0]
        start = int(match.group(1))
        end = int(match.group(2) or match.group(1))
        if start <= page <= end:
            matches.append((end - start, path.name, f"{start}-{end}" if start != end else str(start)))

    if not matches:
        return None, None

    _, filename, page_range = sorted(matches, key=lambda item: (item[0], item[1].lower()))[0]
    return f"/videos/{quote(filename, safe='')}", page_range


def generate_answer(question: str, conversation_id: str = "default") -> AgentResult:
    """Run the same Phase 3 pipeline used by the terminal chatbot."""
    result = _get_pipeline().run(question)
    sources = []
    for chunk in result.get("top_chunks", []):
        metadata = chunk.metadata
        source = {
            "title": metadata.get("title", "PEL Technical Manual"),
            "page": metadata.get("page_start"),
            "section": metadata.get("section") or metadata.get("title"),
        }
        video_url, page_range = _find_video_for_page(source["page"])
        if video_url:
            source["videoUrl"] = video_url
            source["pageRange"] = page_range
        sources.append(source)

    return {"answer": result["answer"], "sources": sources}