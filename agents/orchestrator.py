"""Supervisor orchestrator.

Classifies the customer's intent, extracts entities, and runs the correct chain
of specialist agents (README §6 routing table), threading ids/context between
them. Detects escalation triggers (fraud/legal/VIP) and surfaces them instead of
auto-acting.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from .agent import Agent, AgentResult
from .definitions import (
    AGENTS_BY_ID, INTENT_KEYWORDS, INTENT_ROUTING, SUPERVISOR, get_agent,
)
from .events import (
    AGENT_COMPLETED, AGENT_STARTED, ENTITIES_EXTRACTED, ESCALATION_DETECTED,
    INTENT_CLASSIFIED, RUN_COMPLETED, RUN_STARTED, EventSink, NullSink,
)
from .knowledge import get_knowledge_base
from .llm import LLMClient, build_client
from .settings import SETTINGS

# ─── Entity extraction ──────────────────────────────────────────────────
_PNR_LABELLED = re.compile(
    r"(?:pnr|booking|order|reference|ref|locator)\D{0,12}?\b([A-Z0-9]{6})\b", re.I)
_PNR_BARE = re.compile(r"\b(?=[A-Z0-9]{6}\b)(?=[A-Z0-9]*\d)[A-Z0-9]{6}\b")
_LAST_NAME = re.compile(r"last\s*name\s*(?:is|:)?\s*([A-Za-z][A-Za-z'\-]+)", re.I)
_ROUTE = re.compile(r"\bfrom\s+([A-Z]{3})\s+to\s+([A-Z]{3})\b", re.I)
_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")

# Cues for the combined "new booking + extras" intent (checked before the scan).
_NEW_BOOKING_CUES = ("book a flight", "book flight", "book me", "new booking",
                     "flight from", "fly from", "reserve a", "book a ")
_ANCILLARY_CUES = ("bag", "seat", "meal", "lounge", "wifi", "ancillary")

_ESCALATION = [
    ("fraud", ("fraud", "stolen card", "stolen payment", "unauthori", "scam")),
    ("legal", ("lawsuit", "legal action", "sue you", "my lawyer", "regulator", "complaint to")),
    ("vip", ("platinum", "vip", "diamond member", "top tier")),
    ("safety", ("safety", "security threat", "bomb", "weapon")),
    ("media", ("twitter", "social media", "journalist", "press", "go public")),
]


def extract_entities(message: str) -> dict[str, Any]:
    ents: dict[str, Any] = {}

    m = _PNR_LABELLED.search(message)
    if m:
        ents["pnr"] = m.group(1).upper()
    else:
        m = _PNR_BARE.search(message.upper())
        if m:
            ents["pnr"] = m.group(0).upper()

    m = _LAST_NAME.search(message)
    if m:
        ents["last_name"] = m.group(1)

    m = _ROUTE.search(message)
    if m:
        ents["origin"] = m.group(1).upper()
        ents["destination"] = m.group(2).upper()

    m = _DATE.search(message)
    if m:
        ents["departure_date"] = m.group(1)

    return ents


def detect_escalation(message: str) -> tuple[bool, str]:
    low = message.lower()
    for reason, keywords in _ESCALATION:
        if any(k in low for k in keywords):
            return True, reason
    return False, ""


# ─── Result container ───────────────────────────────────────────────────
@dataclass
class OrchestratorResult:
    user_message: str
    intent: str
    entities: dict[str, Any]
    chain: list[str]
    results: list[AgentResult] = field(default_factory=list)
    escalation: str = ""
    backend: str = "heuristic"

    def transcript(self) -> str:
        header = f"Intent: {self.intent}  |  Route: {' → '.join(self.chain) or '(none)'}"
        if self.escalation:
            header += f"  |  ⚠ escalation: {self.escalation}"
        blocks = [header]
        for r in self.results:
            blocks.append(f"\n─── {r.agent_name} ───\n{r.content}")
        return "\n".join(blocks)

    @property
    def final_answer(self) -> str:
        return self.results[-1].content if self.results else ""


# ═══════════════════════════════════════════════════════════════════════
# Orchestrator
# ═══════════════════════════════════════════════════════════════════════
class Orchestrator:
    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm if llm is not None else build_client(SETTINGS)
        self.backend = self.llm.model_label if self.llm else "heuristic"
        self._agents: dict[str, Agent] = {}

    def _agent(self, agent_id: str) -> Agent:
        if agent_id not in self._agents:
            self._agents[agent_id] = Agent(get_agent(agent_id), self.llm)
        return self._agents[agent_id]

    # ── intent classification ──────────────────────────────────────────
    def classify_intent(self, message: str, entities: dict[str, Any]) -> str:
        heuristic = self._classify_heuristic(message, entities)
        if heuristic != "UNKNOWN":
            return heuristic
        if self.llm is not None:
            llm_intent = self._classify_llm(message, entities)
            if llm_intent in INTENT_ROUTING:
                return llm_intent
        return heuristic

    @staticmethod
    def _classify_heuristic(message: str, entities: dict[str, Any]) -> str:
        low = message.lower()
        # A new booking that also asks for extras is a two-agent chain. Detect it
        # before the single-intent scan (where "bag"/"seat" would match ancillary).
        if ("rebook" not in low
                and any(c in low for c in _NEW_BOOKING_CUES)
                and any(c in low for c in _ANCILLARY_CUES)):
            return "NEW_BOOKING_WITH_ANCILLARY"
        for intent, keywords in INTENT_KEYWORDS:
            if any(k in low for k in keywords):
                return intent
        if entities.get("pnr"):
            return "RETRIEVE_BOOKING"
        return "UNKNOWN"

    def _classify_llm(self, message: str, entities: dict[str, Any]) -> str:
        """Run the Supervisor agent and read its route_to_agent decision."""
        result = self._agent("supervisor").run(message, entities)
        for call in result.tool_calls:
            if call.name == "route_to_agent":
                try:
                    intent = json.loads(call.result).get("intent", "")
                except (json.JSONDecodeError, TypeError):
                    intent = call.arguments.get("intent", "")
                intent = (intent or "").upper().replace(" ", "_").replace("-", "_")
                if intent in INTENT_ROUTING:
                    return intent
        return "UNKNOWN"

    # ── main entry ─────────────────────────────────────────────────────
    def handle(self, message: str, sink: EventSink | None = None,
               prior_entities: dict[str, Any] | None = None) -> OrchestratorResult:
        sink = sink or NullSink()
        sink.emit(RUN_STARTED, message=message, backend=self.backend)

        entities = dict(prior_entities or {})   # session carry-over (e.g. PNR from earlier)
        entities.update(extract_entities(message))
        sink.emit(ENTITIES_EXTRACTED, entities=entities)

        escalate, reason = detect_escalation(message)
        intent = self.classify_intent(message, entities)
        chain = list(INTENT_ROUTING.get(intent, []))

        result = OrchestratorResult(
            user_message=message, intent=intent, entities=entities,
            chain=chain, escalation=reason, backend=self.backend,
        )

        if escalate:
            sink.emit(ESCALATION_DETECTED, reason=reason)
            notice = self._escalation_notice(reason, message, entities)
            result.results.append(notice)
            sink.emit(RUN_COMPLETED, intent=intent, chain=chain, escalation=reason,
                      final_answer=notice.content, steps=1)
            return result

        sink.emit(INTENT_CLASSIFIED, intent=intent, chain=chain, backend=self.backend)

        if not chain:
            cl: AgentResult = self._clarify(message)
            result.results.append(cl)
            sink.emit(RUN_COMPLETED, intent=intent, chain=chain,
                      final_answer=cl.content, steps=1)
            return result

        upstream_parts: list[str] = []
        total = len(chain)
        for i, agent_id in enumerate(chain, 1):
            agent = self._agent(agent_id)
            sink.emit(AGENT_STARTED, agent_id=agent_id, agent_name=agent.definition.name,
                      step=i, total=total)
            agent_result = agent.run(
                message, entities, upstream="\n".join(upstream_parts) or None, sink=sink)
            result.results.append(agent_result)
            sink.emit(AGENT_COMPLETED, agent_id=agent_id, agent_name=agent_result.agent_name,
                      step=i, total=total, content=agent_result.content,
                      tool_count=len(agent_result.tool_calls))
            # Thread discovered ids forward to the next agent in the chain.
            entities.update(agent_result.entities_from_tools())
            upstream_parts.append(f"[{agent_result.agent_name}] {agent_result.content}")

        result.entities = entities
        sink.emit(RUN_COMPLETED, intent=intent, chain=chain,
                  final_answer=result.final_answer, steps=total)
        return result

    # ── fallbacks ──────────────────────────────────────────────────────
    def _escalation_notice(self, reason: str, message: str,
                           entities: dict[str, Any]) -> AgentResult:
        kb = get_knowledge_base(SUPERVISOR.kb)
        hits = kb.retrieve(f"escalation {reason}", top_k=1)
        target = hits[0].snippet(300) if hits else ""
        content = (
            f"⚠ **Escalation triggered ({reason}).** Per the escalation matrix this must go to "
            f"a human team — I will not auto-process it.\n\n{target}"
        )
        return AgentResult(
            agent_id="supervisor", agent_name=SUPERVISOR.name,
            content=content, backend=self.backend,
        )

    def _clarify(self, message: str) -> AgentResult:
        content = (
            "I couldn't confidently classify that request. Could you tell me which you need: "
            "book a new flight, retrieve a booking, change a flight or name, cancel/refund, "
            "rebooking, add baggage/seats/SSR, a medical clearance, a payment issue, or a case "
            "update? (A PNR + last name helps for anything on an existing booking.)"
        )
        return AgentResult(
            agent_id="supervisor", agent_name=SUPERVISOR.name,
            content=content, backend=self.backend,
        )
