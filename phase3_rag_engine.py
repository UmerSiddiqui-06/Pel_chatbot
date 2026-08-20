"""
PHASE 3 — Query Pipeline, Retrieval & Answer Generation for PEL RAG.

Architecture:
    User Query → LLM Query Understanding → [Exact Match | Vector Search | BM25]
              → RRF Fusion → Cross-Encoder Reranker → Top-5 Chunks → LLM Answer

Reads   : .env (GEMINI_API_KEY), ChromaDB, BM25 index, Exact-match index, chunks JSONL
Output  : Terminal-based interactive chatbot
"""
from __future__ import annotations

import json
import os
import pickle
import re
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from dotenv import load_dotenv

import config

# ── Load environment variables ───────────────────────────────────────────
load_dotenv()

# ── Optional imports with graceful degradation ───────────────────────────
try:
    import chromadb
    from chromadb.utils import embedding_functions
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    raise ImportError("ChromaDB not installed. Run: pip install chromadb")
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    raise ImportError("google-genai not installed. Run: pip install google-genai")
try:
    from sentence_transformers import CrossEncoder
    RERANKER_AVAILABLE = True
except ImportError:
    RERANKER_AVAILABLE = False
    print("⚠️  sentence-transformers not installed. Reranking will be skipped.")
    print("   Install with: pip install sentence-transformers")

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    raise ImportError("rank-bm25 not installed. Run: pip install rank-bm25")


# ════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ════════════════════════════════════════════════════════════════════════

@dataclass
class QueryUnderstanding:
    original_query: str
    translated_query: str
    language: str
    is_roman_urdu: bool
    error_codes: List[str] = field(default_factory=list)
    model_names: List[str] = field(default_factory=list)
    intent: str = "general"
    product_category: Optional[str] = None
    confidence: float = 1.0


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    metadata: Dict
    score: float = 0.0
    source: str = ""  # 'exact', 'vector', 'bm25', 'rrf', 'rerank'


# ════════════════════════════════════════════════════════════════════════
# GEMINI CLIENT — Robust Fallback Chain
# ════════════════════════════════════════════════════════════════════════
# ════════════════════════════════════════════════════════════════════════
# GEMINI CLIENT — New SDK (google-genai) matching your PDF script exactly
# ════════════════════════════════════════════════════════════════════════

class GeminiClient:
    """
    Wrapper around the NEW google-genai SDK (same as your PDF extraction script).
    Tries models in order; if one fails (quota/rate-limit/404), tries the next.
    """

    def __init__(self, model_names: List[str], api_key: Optional[str] = None):
        try:
            from google import genai
            from google.genai import types as genai_types
        except ImportError:
            raise ImportError(
                "google-genai not installed. Run: pip install google-genai"
            )

        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY not found. Set it in .env or pass api_key explicitly."
            )

        self.client = genai.Client(api_key=self.api_key)
        self.types = genai_types
        self.model_names = model_names

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.1,
        max_output_tokens: int = 2048,
        json_mode: bool = False,
    ) -> str:
        """
        Generate text with automatic fallback across configured models.
        Rate limits and unavailable models skip immediately; transient errors
        get one short retry before moving to the next model.
        """
        last_error = None
        max_attempts = 2
        retry_delay = 1.0

        for model_name in self.model_names:
            for attempt in range(1, max_attempts + 1):
                try:
                    config = self.types.GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=max_output_tokens,
                        system_instruction=system_instruction,
                        response_mime_type="application/json" if json_mode else None,
                    )

                    response = self.client.models.generate_content(
                        model=model_name,
                        contents=[prompt],
                        config=config,
                    )

                    if not response.text:
                        raise RuntimeError(f"Empty response from {model_name}")

                    return response.text

                except Exception as e:
                    err = str(e)
                    last_error = e
                    is_rate_limited = (
                        "429" in err
                        or "resource_exhausted" in err.lower()
                        or "rate limit" in err.lower()
                        or "quota exceeded" in err.lower()
                    )
                    is_unavailable = (
                        "404" in err
                        or "not found" in err.lower()
                        or "no longer available" in err.lower()
                    )

                    if is_rate_limited or is_unavailable:
                        reason = "rate limited" if is_rate_limited else "unavailable"
                        print(f"   ⚠️  {model_name} {reason}; trying next model")
                        break

                    print(f"   ⚠️  Attempt {attempt} with {model_name} failed: {err[:120]}...")

                    if attempt < max_attempts:
                        time.sleep(retry_delay)

        raise RuntimeError(f"All Gemini models exhausted. Last error: {last_error}")

# ════════════════════════════════════════════════════════════════════════
# QUERY UNDERSTANDING ENGINE (Lightweight Models)
# ════════════════════════════════════════════════════════════════════════

class QueryUnderstandingEngine:
    """
    Uses lightweight Gemini models to:
      • Detect language (including Roman Urdu)
      • Translate to English
      • Extract error_codes[] and model_names[]
      • Determine intent and product category
    """

    SYSTEM_PROMPT = """You are a Query Understanding Engine for a PEL (Pakistan Electronics Limited) technical support chatbot.

Analyze the user's query and output a single JSON object with exactly these fields:
{
  "translated_query": "query translated to English (preserve technical terms)",
  "language": "detected language name, e.g., English, Roman Urdu, Urdu, Chinese, Arabic",
  "is_roman_urdu": true or false,
  "error_codes": ["E1", "F1", "5E"] or [],
  "model_names": ["ACE", "APEX", "PRGD-200"] or [],
  "intent": "troubleshooting|specifications|installation|warranty|general",
  "product_category": "air_conditioner|refrigerator|led_television|washing_machine|microwave_oven|water_dispenser|deep_freezer|general|null",
  "confidence": 0.0 to 1.0
}

RULES:
- Error codes are 1-5 characters: E1, F1, 5E, EH01, EL00, PC00, etc.
- PEL AC models: ACE, APEX, ALPHA, ALLURE, REGAL, SUPREME, FIT, SAVER, SUPER, SUBLIME, ALPINE, O-GLORY, ULTIMATE, BOLD, MAJESTIC, AERO, TURBO, JUMBO, etc.
- Refrigerator models often start with PR (e.g., PRGD, PRLP, PRINV).
- Washing machine: PAWM, PWM, FIT-WASH.
- Microwave: PMO.
- Water dispenser: PWD, PCWD.
- Deep freezer: PDF, PVF.
- LED TV: PLD.
- If uncertain about category, use null.
- Output ONLY the JSON object. No markdown, no explanations, no code fences.
"""

    # Fast heuristic for Roman Urdu to save API calls on obvious cases
    ROMAN_URDU_TOKENS = {
        "kya", "hai", "nahi", "kaise", "kahan", "kya", "mera", "apka", "problem",
        "masla", "theek", "nhi", "nhi", "kr", "rha", "rhi", "gya", "gyi", "ho",
        "gya", "chahiye", "bataen", "btao", "krna", "kro", "krain", "kren",
        "kia", "kesy", "kesay", "kahan", "kidhar", "kab", "q", "kyun", "kyon",
        "nhe", "nh", "ni", "nahi", "nhi", "masla", "mushkil", "kharab", "tut",
        "garmi", "sardi", "chalu", "band", "on", "off", "nhi", "horha", "horhi",
    }

    def __init__(self, gemini_client: GeminiClient):
        self.client = gemini_client

    def _heuristic_roman_urdu(self, text: str) -> bool:
        """Quick check to avoid API call for obvious Roman Urdu."""
        words = set(re.findall(r'\b[a-zA-Z]+\b', text.lower()))
        return len(words & self.ROMAN_URDU_TOKENS) >= 2

    def understand(self, query: str) -> QueryUnderstanding:
        # Quick heuristic pre-check
        is_roman = self._heuristic_roman_urdu(query)
        
        prompt = f'Analyze this user query and return JSON only:\n\n"{query}"'
        
        response = self.client.generate(
            prompt=prompt,
            system_instruction=self.SYSTEM_PROMPT,
            temperature=0.0,
            json_mode=True,
        )
        
        # Clean response (sometimes Gemini wraps JSON in markdown)
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            print(f"   ⚠️  JSON parse failed, using fallback parsing. Raw: {response[:200]}")
            # Fallback: construct minimal understanding
            return QueryUnderstanding(
                original_query=query,
                translated_query=query,
                language="Unknown",
                is_roman_urdu=is_roman,
            )
        
        # Validate and sanitize
        translated = data.get("translated_query", query)
        if not translated or translated.strip() == "":
            translated = query
        
        # Ensure error codes are uppercase and clean
        error_codes = [re.sub(r'\s+', '', str(c)).upper() for c in data.get("error_codes", [])]
        error_codes = [c for c in error_codes if c]
        
        # Ensure model names are uppercase
        model_names = [str(m).upper().strip() for m in data.get("model_names", [])]
        model_names = [m for m in model_names if m]
        
        # Override Roman Urdu if heuristic says so but LLM missed it
        if is_roman and not data.get("is_roman_urdu"):
            data["is_roman_urdu"] = True
            if data.get("language", "").lower() not in ("roman urdu", "urdu"):
                data["language"] = "Roman Urdu"
        
        return QueryUnderstanding(
            original_query=query,
            translated_query=translated,
            language=data.get("language", "Unknown"),
            is_roman_urdu=data.get("is_roman_urdu", False),
            error_codes=error_codes,
            model_names=model_names,
            intent=data.get("intent", "general"),
            product_category=data.get("product_category") or None,
            confidence=float(data.get("confidence", 0.8)),
        )


# ════════════════════════════════════════════════════════════════════════
# RETRIEVER — Exact Match + Vector (ANN) + BM25
# ════════════════════════════════════════════════════════════════════════

class Retriever:
    """
    Three-path retrieval system:
      1. Exact Match: error_code / model_name → chunk_ids (highest precision)
      2. Vector Search: ChromaDB HNSW ANN (cosine similarity, hierarchical)
      3. BM25: keyword matching for exact terms
    """

    def __init__(self):
        if not CHROMADB_AVAILABLE:
            raise RuntimeError("ChromaDB not available")
        if not BM25_AVAILABLE:
            raise RuntimeError("BM25 not available")

        # ── Load ChromaDB ───────────────────────────────────────────────
        self.chroma_client = chromadb.PersistentClient(path=str(config.CHROMA_PERSIST_DIR))
        
        self.embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=config.EMBEDDING_MODEL
        )
        
        try:
            self.collection = self.chroma_client.get_collection(
                name=config.CHROMA_COLLECTION,
                embedding_function=self.embed_fn,
            )
        except Exception as e:
            raise RuntimeError(
                f"ChromaDB collection '{config.CHROMA_COLLECTION}' not found. "
                f"Run Phase 2 first. Error: {e}"
            )
        
        # ── Load BM25 ───────────────────────────────────────────────────
        with open(config.BM25_INDEX_PATH, "rb") as f:
            bm25_data = pickle.load(f)
        self.bm25: BM25Okapi = bm25_data["bm25"]
        self.bm25_chunk_ids: List[str] = bm25_data["chunk_ids"]
        self.bm25_chunk_texts: List[str] = bm25_data.get("chunk_texts", [])
        
        # ── Load Exact Match Index ──────────────────────────────────────
        with open(config.EXACT_MATCH_PATH, "r", encoding="utf-8") as f:
            self.exact_match = json.load(f)
        
        # ── Load all chunks into memory for fast lookup ─────────────────
        self.chunks_by_id: Dict[str, Dict] = {}
        with open(config.OUTPUT_JSONL, "r", encoding="utf-8") as f:
            for line in f:
                chunk = json.loads(line.strip())
                self.chunks_by_id[chunk["chunk_id"]] = chunk
        
        print(f"   📦 Loaded {len(self.chunks_by_id)} chunks into memory")
        print(f"   📦 ChromaDB collection: {self.collection.count()} vectors")
        print(f"   📦 BM25 index: {len(self.bm25_chunk_ids)} documents")
        print(f"   📦 Exact match: {len(self.exact_match.get('error_codes', {}))} error codes, "
              f"{len(self.exact_match.get('model_names', {}))} models")

    # ── 1. EXACT MATCH ──────────────────────────────────────────────────
    def exact_match_search(
        self,
        error_codes: List[str],
        model_names: List[str]
    ) -> List[Tuple[str, float]]:
        """Direct lookup: error code / model name → chunk IDs. Perfect precision."""
        hits: Dict[str, float] = {}
        
        for code in error_codes:
            code_clean = code.upper().strip().replace(" ", "")
            for chunk_id in self.exact_match.get("error_codes", {}).get(code_clean, []):
                hits[chunk_id] = max(hits.get(chunk_id, 0.0), 1.0)
        
        for model in model_names:
            model_clean = model.upper().strip().replace(" ", "")
            for chunk_id in self.exact_match.get("model_names", {}).get(model_clean, []):
                hits[chunk_id] = max(hits.get(chunk_id, 0.0), 1.0)
        
        # Sort by score desc, then by chunk_id for determinism
        return sorted(hits.items(), key=lambda x: (-x[1], x[0]))

    # ── 2. VECTOR SEARCH (Hierarchical ANN) ─────────────────────────────
    def vector_search(
        self,
        query: str,
        n_results: int = 20,
        product_category: Optional[str] = None,
    ) -> List[Tuple[str, float]]:
        """
        Hierarchical vector search:
          Level 1: If product_category is known, filter ChromaDB to that category.
          Level 2: If too few results, fall back to global search.
        Uses HNSW ANN (cosine distance) for fast retrieval.
        """
        # Hierarchical Level 1: Category-filtered search
        if product_category and product_category != "general":
            try:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=n_results,
                    where={"product_category": product_category},
                    include=["distances"],
                )
                ids = results["ids"][0]
                distances = results["distances"][0]
                
                if len(ids) >= config.CATEGORY_SEARCH_MIN_RESULTS:
                    # Convert cosine distance (0-2) to similarity score (0-1)
                    return [(cid, max(0.0, 1.0 - (d / 2.0))) for cid, d in zip(ids, distances)]
            except Exception as e:
                print(f"   ⚠️  Filtered vector search failed: {e}")
        
        # Hierarchical Level 2: Global search (fallback or no category)
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                include=["distances"],
            )
            ids = results["ids"][0]
            distances = results["distances"][0]
            return [(cid, max(0.0, 1.0 - (d / 2.0))) for cid, d in zip(ids, distances)]
        except Exception as e:
            print(f"   ⚠️  Vector search failed: {e}")
            return []

    # ── 3. BM25 SEARCH ──────────────────────────────────────────────────
    def bm25_search(self, query: str, n_results: int = 20) -> List[Tuple[str, float]]:
        """Token-level keyword matching. Great for model numbers and error codes."""
        def tokenize(text: str) -> List[str]:
            text = re.sub(r'[*_`#]', ' ', text)
            return re.findall(r"[a-z0-9]+", text.lower())

        tokens = tokenize(query)
        if not tokens:
            return []

        scores = self.bm25.get_scores(tokens)
        top_indices = np.argsort(scores)[::-1][:n_results]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append((self.bm25_chunk_ids[idx], float(scores[idx])))
        return results

    def get_chunk(self, chunk_id: str) -> Optional[Dict]:
        """Fetch full chunk data by ID."""
        return self.chunks_by_id.get(chunk_id)


# ════════════════════════════════════════════════════════════════════════
# RECIPROCAL RANK FUSION (RRF)
# ════════════════════════════════════════════════════════════════════════

class RRFFusion:
    """
    Combines results from multiple retrieval paths using Reciprocal Rank Fusion.
    Formula: score = Σ 1/(k + rank) for each list where the item appears.
    """

    @staticmethod
    def fuse(
        results_lists: List[List[Tuple[str, float]]],
        k: int = 60,
        top_n: int = 20,
    ) -> List[Tuple[str, float]]:
        """
        Args:
            results_lists: List of result lists, each is [(chunk_id, score), ...]
            k: RRF constant (typically 60)
            top_n: Return top-N fused results
        """
        rrf_scores: Dict[str, float] = {}
        
        for results in results_lists:
            for rank, (chunk_id, _) in enumerate(results, start=1):
                if chunk_id not in rrf_scores:
                    rrf_scores[chunk_id] = 0.0
                rrf_scores[chunk_id] += 1.0 / (k + rank)
        
        # Sort by RRF score descending
        fused = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        return fused[:top_n]


# ════════════════════════════════════════════════════════════════════════
# CROSS-ENCODER RERANKER
# ════════════════════════════════════════════════════════════════════════

class CrossEncoderReranker:
    """
    Re-ranks fused candidates using BAAI/bge-reranker-v2-m3.
    This is the heavy-lifter that ensures the top-5 are truly relevant.
    """

    def __init__(self, model_name: str = config.RERANKER_MODEL):
        if not RERANKER_AVAILABLE:
            raise RuntimeError(
                "Cross-encoder not available. Install: pip install sentence-transformers"
            )
        
        print(f"   🔄 Loading cross-encoder: {model_name} ...")
        self.model = CrossEncoder(model_name, max_length=512)
        print(f"   ✅ Cross-encoder ready")

    def rerank(
        self,
        query: str,
        chunks: List[Dict],
        top_k: int = 5,
    ) -> List[RetrievedChunk]:
        if not chunks:
            return []

        # FIX: use title-enriched text, not raw chunk["text"]
        pairs = [[query, build_rerank_text(chunk)] for chunk in chunks]

        scores = self.model.predict(pairs, show_progress_bar=False)

        scored = []
        for chunk, score in zip(chunks, scores):
            scored.append(RetrievedChunk(
                chunk_id=chunk["chunk_id"],
                text=chunk["text"],
                metadata=chunk["metadata"],
                score=float(score),
                source="rerank",
            ))

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]


# ════════════════════════════════════════════════════════════════════════
# ANSWER GENERATOR (Strong Gemini Models)
# ════════════════════════════════════════════════════════════════════════

class AnswerGenerator:
    """
    Generates the final answer using strong Gemini models.
    Fed with top-5 reranked chunks as context.
    """

    SYSTEM_PROMPT = """You are PEL Technical Support AI — an expert assistant for Pakistan Electronics Limited (PEL) products including ACs, refrigerators, LED TVs, washing machines, microwave ovens, water dispensers, and deep freezers.

Your job is to answer the user's technical question using ONLY the provided context chunks from the official PEL service manual.

CRITICAL RULES:
1. Answer in the SAME LANGUAGE as the user's original query.
2. Cite sources using [chunk_id] when referencing specific information.
3. For troubleshooting: give clear step-by-step instructions.
4. For error codes: explain what the code means and how to fix it.
5. For installation: provide numbered steps.
6. For specifications: quote exact numbers from the context.
7. If the context does NOT contain the answer, say clearly: "I don't have enough information in the manual to answer this."
8. NEVER make up information, model numbers, or error codes not present in the context.
9. Be concise but complete. Use bullet points for clarity.
10. If the user asks in Roman Urdu, reply in Roman Urdu (or simple Urdu script if appropriate).
"""

    def __init__(self, gemini_client: GeminiClient):
        self.client = gemini_client

    def _build_context(self, chunks: List[RetrievedChunk]) -> str:
        """Build context string from top chunks, truncating to avoid token overflow."""
        parts = []
        for ch in chunks:
            # Truncate text to stay within token budget
            text = ch.text[:config.MAX_CHUNK_CONTEXT_CHARS]
            meta = ch.metadata
            title = meta.get("title", "Unknown Section")
            pages = meta.get("page_start", "?")
            parts.append(
                f"--- CHUNK [{ch.chunk_id}] (Page {pages}, Section: {title}) ---\n{text}"
            )
        return "\n\n".join(parts)

    def generate(
        self,
        original_query: str,
        translated_query: str,
        top_chunks: List[RetrievedChunk],
        language: str,
    ) -> str:
        context = self._build_context(top_chunks)
        
        prompt = f"""Original User Query (Language: {language}):
"{original_query}"

English Translation:
"{translated_query}"

CONTEXT FROM PEL TECHNICAL MANUAL:
{context}

INSTRUCTIONS:
- Answer the user's question based ONLY on the context above.
- Respond in {language}.
- Cite chunk IDs like [pel_0001] when referencing facts.
- If the answer is not in the context, say you don't know.

Your Answer:"""

        return self.client.generate(
            prompt=prompt,
            system_instruction=self.SYSTEM_PROMPT,
            temperature=0.2,  # low temp for factual consistency
            max_output_tokens=2048,
        )


# ════════════════════════════════════════════════════════════════════════
# PHASE 3 PIPELINE — Orchestrator
# ════════════════════════════════════════════════════════════════════════

class Phase3Pipeline:
    """
    End-to-end pipeline: Query → Understand → Retrieve → Fuse → Rerank → Answer
    """

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file")

        # Lightweight client for query understanding
        self.query_client = GeminiClient(config.QUERY_UNDERSTANDING_MODELS, api_key)
        # Strong client for answer generation
        self.answer_client = GeminiClient(config.ANSWER_GENERATION_MODELS, api_key)

        self.understanding = QueryUnderstandingEngine(self.query_client)
        self.retriever = Retriever()
        self.reranker = CrossEncoderReranker() if RERANKER_AVAILABLE else None
        self.generator = AnswerGenerator(self.answer_client)

    def run(self, query: str) -> Dict:
        start_time = time.time()
        print(f"\n{'━'*60}")
        print(f"  📝 QUERY: {query}")
        print(f"{'━'*60}")

        # ── STEP 1: Query Understanding ─────────────────────────────────
        t0 = time.time()
        print("\n🔍 [1/5] Query Understanding (lightweight Gemini)...")
        qu = self.understanding.understand(query)
        print(f"    Language: {qu.language} {'(Roman Urdu)' if qu.is_roman_urdu else ''}")
        print(f"    English:  {qu.translated_query}")
        print(f"    Intent:   {qu.intent}")
        print(f"    Category: {qu.product_category or 'general'}")
        if qu.error_codes:
            print(f"    Error Codes: {qu.error_codes}")
        if qu.model_names:
            print(f"    Models:      {qu.model_names}")
        print(f"    ⏱️  {time.time()-t0:.2f}s")

        # ── STEP 2: Parallel Retrieval ──────────────────────────────────
        t0 = time.time()
        print("\n🔍 [2/5] Parallel Retrieval...")

        with ThreadPoolExecutor(max_workers=3, thread_name_prefix="retrieval") as executor:
            exact_future = executor.submit(
                self.retriever.exact_match_search,
                qu.error_codes,
                qu.model_names,
            )
            vector_future = executor.submit(
                self.retriever.vector_search,
                qu.translated_query,
                config.VECTOR_SEARCH_TOP_K,
                qu.product_category,
            )
            bm25_future = executor.submit(
                self.retriever.bm25_search,
                qu.translated_query,
                config.BM25_SEARCH_TOP_K,
            )

            exact_results = exact_future.result()
            vector_results = vector_future.result()
            bm25_results = bm25_future.result()

        print(f"    Exact Match: {len(exact_results)} hits")
        print(f"    Vector ANN:  {len(vector_results)} hits")
        print(f"    BM25:        {len(bm25_results)} hits")
        print(f"    ⏱️  {time.time()-t0:.2f}s")

        # ── STEP 3: RRF Fusion ──────────────────────────────────────────
        t0 = time.time()
        print("\n🔍 [3/5] Reciprocal Rank Fusion...")
        fused = RRFFusion.fuse(
            [exact_results, vector_results, bm25_results],
            k=config.RRF_K,
            top_n=config.RRF_TOP_CANDIDATES,
        )
        print(f"    Fused candidates: {len(fused)}")
        print(f"    ⏱️  {time.time()-t0:.2f}s")

        # ── STEP 4: Cross-Encoder Reranking ─────────────────────────────
        t0 = time.time()
        print("\n🔍 [4/5] Cross-Encoder Reranking...")
        
        # Load chunk objects for fused candidates
        candidate_chunks = []
        for chunk_id, _ in fused:
            chunk = self.retriever.get_chunk(chunk_id)
            if chunk:
                candidate_chunks.append(chunk)
        
        if self.reranker:
            top_chunks = self.reranker.rerank(
                qu.translated_query,
                candidate_chunks,
                top_k=config.FINAL_TOP_K,
            )
        else:
            # Fallback: no reranker, just take top fused
            top_chunks = [
                RetrievedChunk(
                    chunk_id=c["chunk_id"],
                    text=c["text"],
                    metadata=c["metadata"],
                    score=0.0,
                    source="rrf",
                )
                for c in candidate_chunks[:config.FINAL_TOP_K]
            ]
        
        print(f"    Top {len(top_chunks)} chunks:")
        for i, ch in enumerate(top_chunks, 1):
            title = ch.metadata.get("title", "Unknown")[:50]
            print(f"      {i}. [{ch.chunk_id}] {title}... (score: {ch.score:.3f})")
        print(f"    ⏱️  {time.time()-t0:.2f}s")

        # ── STEP 5: Answer Generation ───────────────────────────────────
        t0 = time.time()
        print("\n🔍 [5/5] Generating Answer (strong Gemini)...")
        answer = self.generator.generate(
            original_query=query,
            translated_query=qu.translated_query,
            top_chunks=top_chunks,
            language=qu.language,
        )
        print(f"    ⏱️  {time.time()-t0:.2f}s")

        total_time = time.time() - start_time
        print(f"\n{'━'*60}")
        print(f"  ✅ Total pipeline time: {total_time:.2f}s")
        print(f"{'━'*60}")

        return {
            "query": query,
            "understanding": qu,
            "retrieval_stats": {
                "exact_match": len(exact_results),
                "vector": len(vector_results),
                "bm25": len(bm25_results),
                "fused": len(fused),
                "final": len(top_chunks),
            },
            "top_chunks": top_chunks,
            "answer": answer,
            "time_seconds": total_time,
        }


# ════════════════════════════════════════════════════════════════════════
# MAIN — Interactive Terminal Chatbot
# ════════════════════════════════════════════════════════════════════════

def build_rerank_text(chunk: Dict) -> str:
    """
    Text passed to the cross-encoder for reranking.
    This intentionally includes the title context so short chunks (tables,
    model spec blocks, installation bullets) retain their section/product
    meaning during reranking.
    """
    meta = chunk.get("metadata", {})
    parts = []

    if meta.get("title"):
        parts.append(meta["title"])

    if meta.get("product_category") and meta["product_category"] != "general":
        parts.append(meta["product_category"].replace("_", " "))

    parts.append(chunk.get("text", ""))
    return "\n".join(part for part in parts if part)


def print_banner():
    print("\n" + "╔" + "═"*58 + "╗")
    print("║" + " "*15 + "PEL RAG CHATBOT — PHASE 3" + " "*18 + "║")
    print("║" + " "*10 + "Type your query below (any language)" + " "*12 + "║")
    print("║" + " "*15 + "Commands: 'quit', 'exit', 'q'" + " "*16 + "║")
    print("╚" + "═"*58 + "╝")

def main():
    print_banner()
    
    try:
        pipeline = Phase3Pipeline()
    except Exception as e:
        print(f"\n❌ Failed to initialize pipeline: {e}")
        print("   Make sure you have:")
        print("   • Run Phase 1 and Phase 2 to build indexes")
        print("   • Set GEMINI_API_KEY in your .env file")
        print("   • Installed dependencies: chromadb, rank-bm25, sentence-transformers, google-generativeai")
        return

    while True:
        try:
            query = input("\n🧑 You: ").strip()
            
            if query.lower() in ("quit", "exit", "q"):
                print("\n👋 Shutting down. Goodbye!")
                break
            
            if not query:
                continue
            
            result = pipeline.run(query)
            
            print(f"\n🤖 PEL AI ({result['understanding'].language}):")
            print(result["answer"])
            
            # Show sources
            sources = [c.chunk_id for c in result["top_chunks"]]
            print(f"\n📚 Sources: {', '.join(sources)}")
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()