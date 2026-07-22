"""Knowledge base layer — dependency-free retrieval over ``knowledge-docs-v1/``.

Each of the 15 knowledge bases from the README maps to a subset of the 19
source documents. Documents are split into heading-delimited chunks and scored
against the query with a lightweight TF/overlap ranker. No embeddings, no
external services — this runs anywhere Python does and keeps the whole fleet
demonstrable offline.

If you later move to Azure AI Foundry knowledge bases (as the README
describes), swap :func:`KnowledgeBase.retrieve` for a call to the Foundry
retrieval endpoint — the rest of the orchestrator is unchanged.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from .settings import KNOWLEDGE_DIR

# ─── KB -> source documents (README §3) ─────────────────────────────────
KB_SOURCES: dict[str, list[str]] = {
    "kb-supervisor-orchestrator": [
        "airline_policies.md",
        "intent_classification_examples.json",
        "escalation_matrix.md",
        "api_reference.md",
    ],
    "kb-create-booking": [
        "booking_flow_guide.md",
        "fare_families.md",
        "passenger_type_codes.md",
        "api_reference.md",
    ],
    "kb-booking-retrieval": [
        "api_reference.md",
        "airline_policies.md",
    ],
    "kb-name-change": [
        "name_change_policy.md",
        "api_reference.md",
        "airline_policies.md",
    ],
    "kb-change-booking": [
        "change_booking_rules.md",
        "fare_families.md",
        "api_reference.md",
    ],
    "kb-refund-agent": [
        "refund_policy.md",
        "refund_graphql_schemas.md",
        "api_reference.md",
        "airline_policies.md",
    ],
    "kb-refund-workflow": [
        "refund_graphql_schemas.md",
        "refund_policy.md",
        "api_reference.md",
    ],
    "kb-rebooking": [
        "rebooking_policy.md",
        "fare_families.md",
        "api_reference.md",
    ],
    "kb-disruption-rebooking": [
        "disruption_handling_guide.md",
        "rebooking_policy.md",
        "airline_policies.md",
        "api_reference.md",
    ],
    "kb-ancillary-sales": [
        "ancillary_services_catalogue.md",
        "api_reference.md",
    ],
    "kb-passenger-ssr": [
        "ssr_codes_reference.md",
        "airline_policies.md",
        "api_reference.md",
    ],
    "kb-medical-exception": [
        "medical_clearance_guide.md",
        "airline_policies.md",
    ],
    "kb-payment": [
        "payment_processing_guide.md",
        "api_reference.md",
    ],
    "kb-case-management": [
        "case_management_sla.md",
        "escalation_matrix.md",
    ],
    "kb-communication-summary": [
        "email_templates.md",
        "airline_policies.md",
    ],
}

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_STOPWORDS = frozenset(
    """
    a an and are as at be but by for from has have i if in into is it its of on or
    that the their then there these this to was were will with you your can do does
    my me we our us not no yes need want please would could should about
    """.split()
)


def _tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS and len(t) > 1]


@dataclass
class Chunk:
    doc: str
    heading: str
    text: str
    tokens: frozenset[str] = field(default_factory=frozenset)

    def snippet(self, limit: int = 900) -> str:
        body = self.text.strip()
        if len(body) > limit:
            body = body[:limit].rsplit("\n", 1)[0] + "\n…"
        title = f"[{self.doc}] {self.heading}".strip()
        return f"### {title}\n{body}"


def _split_into_chunks(doc_name: str, content: str) -> list[Chunk]:
    """Split a document into heading-delimited chunks.

    JSON docs (e.g. intent examples) are kept whole; markdown is split on
    ``#``/``##``/``###`` headings so retrieval returns focused sections.
    """
    if doc_name.endswith(".json"):
        return [Chunk(doc=doc_name, heading="(full document)", text=content,
                      tokens=frozenset(_tokenize(content)))]

    chunks: list[Chunk] = []
    current_heading = "(intro)"
    buffer: list[str] = []

    def flush() -> None:
        body = "\n".join(buffer).strip()
        if body:
            joined = f"{current_heading}\n{body}"
            chunks.append(Chunk(doc=doc_name, heading=current_heading, text=body,
                                tokens=frozenset(_tokenize(joined))))

    for line in content.splitlines():
        if re.match(r"^#{1,3}\s+\S", line):
            flush()
            current_heading = line.lstrip("#").strip()
            buffer = []
        else:
            buffer.append(line)
    flush()
    return chunks or [Chunk(doc=doc_name, heading="(full document)", text=content,
                            tokens=frozenset(_tokenize(content)))]


@lru_cache(maxsize=None)
def _load_document(doc_name: str) -> tuple[Chunk, ...]:
    path = KNOWLEDGE_DIR / doc_name
    if not path.is_file():
        return ()
    content = path.read_text(encoding="utf-8", errors="replace")
    return tuple(_split_into_chunks(doc_name, content))


@dataclass
class KnowledgeBase:
    """A named knowledge base backing one agent."""

    name: str
    documents: list[str]

    def all_chunks(self) -> list[Chunk]:
        chunks: list[Chunk] = []
        for doc in self.documents:
            chunks.extend(_load_document(doc))
        return chunks

    def retrieve(self, query: str, top_k: int = 4) -> list[Chunk]:
        """Return the ``top_k`` most relevant chunks for ``query``."""
        q_tokens = _tokenize(query)
        if not q_tokens:
            return self.all_chunks()[:top_k]
        q_counts: dict[str, int] = {}
        for t in q_tokens:
            q_counts[t] = q_counts.get(t, 0) + 1

        scored: list[tuple[float, Chunk]] = []
        for chunk in self.all_chunks():
            if not chunk.tokens:
                continue
            overlap = sum(w for t, w in q_counts.items() if t in chunk.tokens)
            if overlap == 0:
                continue
            # Normalize by chunk size so short, on-point sections rank well.
            score = overlap / (1.0 + (len(chunk.tokens) ** 0.5) / 4.0)
            scored.append((score, chunk))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [chunk for _, chunk in scored[:top_k]]

    def context_block(self, query: str, top_k: int = 4) -> str:
        """Formatted retrieval context to inject into an agent's prompt."""
        hits = self.retrieve(query, top_k=top_k)
        if not hits:
            return "(no matching knowledge-base sections found)"
        return "\n\n".join(chunk.snippet() for chunk in hits)


def get_knowledge_base(kb_name: str) -> KnowledgeBase:
    docs = KB_SOURCES.get(kb_name, [])
    return KnowledgeBase(name=kb_name, documents=docs)


def missing_documents() -> list[str]:
    """Source docs referenced by a KB but absent from ``knowledge-docs-v1/``."""
    referenced = {doc for docs in KB_SOURCES.values() for doc in docs}
    return sorted(doc for doc in referenced if not (KNOWLEDGE_DIR / doc).is_file())
