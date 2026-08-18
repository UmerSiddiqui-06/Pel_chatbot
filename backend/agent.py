"""
Stand-in for the real AI agent (RAG + LLM). Your teammate replaces the
inside of `generate_answer` with their actual pipeline later — the rest
of the backend only ever calls this one function, so nothing else needs
to change when that happens.
"""
from typing import List, TypedDict


class SourceDict(TypedDict, total=False):
    title: str
    page: int
    section: str


class AgentResult(TypedDict):
    answer: str
    sources: List[SourceDict]


def generate_answer(question: str) -> AgentResult:
    lowered = question.lower()

    if "warrant" in lowered:
        return {
            "answer": "PEL air conditioners are covered by a two-year warranty on the compressor and major components, according to the available PEL documentation.",
            "sources": [{"title": "Warranty Policy", "page": 4}],
        }

    if "leave" in lowered:
        return {
            "answer": "Confirmed employees are entitled to 18 annual leave days per calendar year. Leave requests should be submitted at least three working days in advance.",
            "sources": [{"title": "Employee Leave Policy", "page": 6}],
        }

    if "order" in lowered or "status" in lowered:
        return {
            "answer": "I can look up order status once this is connected to PEL's order-management system.",
            "sources": [{"title": "Product Database", "section": "Orders"}],
        }

    return {
        "answer": "I couldn't find a confident answer in PEL's indexed documentation for that. Try rephrasing your question, or check back once more documents have been indexed.",
        "sources": [],
    }