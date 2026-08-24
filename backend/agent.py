"""Backend adapter for the fixed, pre-indexed PEL Phase 3 RAG pipeline."""
from pathlib import Path
import sys
from threading import Lock
from typing import TYPE_CHECKING, List, TypedDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if TYPE_CHECKING:
    from phase3_rag_engine import Phase3Pipeline


class SourceDict(TypedDict, total=False):
    title: str
    page: int
    section: str


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


def generate_answer(question: str, conversation_id: str = "default") -> AgentResult:
    """Run the same Phase 3 pipeline used by the terminal chatbot."""
    result = _get_pipeline().run(question)
    sources = []
    for chunk in result.get("top_chunks", []):
        metadata = chunk.metadata
        sources.append({
            "title": metadata.get("title", "PEL Technical Manual"),
            "page": metadata.get("page_start"),
            "section": metadata.get("section") or metadata.get("title"),
        })

    return {"answer": result["answer"], "sources": sources}