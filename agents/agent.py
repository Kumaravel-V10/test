"""Agent runtime.

Wraps an :class:`~agents.definitions.AgentDefinition` with a knowledge base and
a tool set, and runs it either through an LLM tool-calling loop or, when no LLM
is configured, a deterministic heuristic that still calls the agent's primary
tool and grounds its reply in retrieved knowledge.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from .definitions import AgentDefinition
from .events import TOOL_CALLED, TOOL_RESULT, EventSink, NullSink
from .knowledge import get_knowledge_base
from .llm import AssistantTurn, LLMClient
from .settings import SETTINGS
from .tools import execute_tool, schemas_for

# Rules every agent operates under (safety + honesty about simulated tools).
_SHARED_RULES = """\
OPERATING RULES (all agents):
- Ground every factual claim in the knowledge-base context provided below.
- Call a tool only when you have its required inputs; otherwise ask for the missing detail.
- Irreversible actions (confirm_booking, process_refund, sending email) require explicit
  customer confirmation first.
- Never request full card numbers, CVV, or passwords in chat.
- Some post-order tools return responses tagged "simulated": true — treat their data as a
  realistic placeholder and say so if the customer needs a guaranteed live result.
"""


@dataclass
class ToolInvocation:
    name: str
    arguments: dict[str, Any]
    result: str


@dataclass
class AgentResult:
    agent_id: str
    agent_name: str
    content: str
    tool_calls: list[ToolInvocation] = field(default_factory=list)
    backend: str = "heuristic"

    def entities_from_tools(self) -> dict[str, Any]:
        """Pull useful ids out of tool results to feed the next agent in a chain."""
        found: dict[str, Any] = {}
        for call in self.tool_calls:
            try:
                data = json.loads(call.result)
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(data, dict):
                continue
            for key in ("checkoutId", "cartId", "orderId", "pnr", "caseId", "quoteId"):
                if key in data and data[key]:
                    found[key] = data[key]
            props = data.get("refundProposalReferences")
            if isinstance(props, list) and props:
                found["refund_proposal_ids"] = [
                    p.get("refundProposalId") for p in props if isinstance(p, dict)
                ]
        return found


# ═══════════════════════════════════════════════════════════════════════
# Heuristic primary-tool mapping (used only when no LLM is configured)
# ═══════════════════════════════════════════════════════════════════════

def _pnr(e: dict[str, Any]) -> str | None:
    return e.get("pnr") or e.get("orderId") or e.get("order_id")


def _last(e: dict[str, Any]) -> str:
    return e.get("last_name") or e.get("lastName") or ""


def _h_retrieve_order(e: dict[str, Any]):
    pnr = _pnr(e)
    return ("retrieve_order", {"order_id": pnr, "last_name": _last(e)}) if pnr else None


def _h_refund(e: dict[str, Any]):
    pnr = _pnr(e)
    return ("check_refund_eligibility", {"order_id": pnr, "last_name": _last(e) or "PASSENGER"}) if pnr else None


def _h_process_refund(e: dict[str, Any]):
    pnr = _pnr(e)
    ids = e.get("refund_proposal_ids")
    if pnr and ids:
        return ("process_refund",
                {"order_id": pnr, "last_name": _last(e) or "PASSENGER", "refund_proposal_ids": ids})
    return None


def _h_search(e: dict[str, Any]):
    o, d = e.get("origin"), e.get("destination")
    date = e.get("departure_date") or e.get("date")
    if o and d and date:
        return ("search_flights", {
            "trip_type": "OW", "departure_location": o, "arrival_location": d,
            "departure_date": date,
            "passengers": [{"passengerTypeCode": "ADT", "discountCode": "ADT"}],
        })
    return None


def _h_list_ssr(e: dict[str, Any]):
    pnr = _pnr(e)
    return ("list_ssr", {"order_id": pnr, "last_name": _last(e)}) if pnr else None


_HEURISTIC_PRIMARY: dict[str, Callable[[dict[str, Any]], Any]] = {
    "booking-retrieval": _h_retrieve_order,
    "refund": _h_refund,
    "refund-workflow": _h_process_refund,
    "name-change": _h_retrieve_order,
    "change-booking": _h_retrieve_order,
    "rebooking": _h_retrieve_order,
    "disruption-rebooking": _h_retrieve_order,
    "create-booking": _h_search,
    "passenger-ssr": _h_list_ssr,
}


# ═══════════════════════════════════════════════════════════════════════
# Agent
# ═══════════════════════════════════════════════════════════════════════

class Agent:
    def __init__(self, definition: AgentDefinition, llm: LLMClient | None):
        self.definition = definition
        self.llm = llm
        self.kb = get_knowledge_base(definition.kb)

    # ── prompt assembly ────────────────────────────────────────────────
    def _system_prompt(self, query: str) -> str:
        kb_context = self.kb.context_block(query, top_k=SETTINGS.kb_top_k)
        return (
            f"{self.definition.system_prompt}\n\n{_SHARED_RULES}\n\n"
            f"KNOWLEDGE BASE ({self.definition.kb}) — retrieved for this request:\n"
            f"{kb_context}\n"
        )

    def _user_prompt(self, query: str, entities: dict[str, Any],
                     upstream: str | None) -> str:
        parts = [f"Customer request:\n{query}"]
        if entities:
            parts.append("Extracted entities:\n" + json.dumps(entities, ensure_ascii=False))
        if upstream:
            parts.append("Context from previous agent(s):\n" + upstream)
        return "\n\n".join(parts)

    # ── tool execution with event emission ─────────────────────────────
    def _exec_tool(self, name: str, args: dict[str, Any], sink: EventSink) -> str:
        sink.emit(TOOL_CALLED, agent_id=self.definition.id,
                  agent_name=self.definition.name, tool=name, arguments=args)
        result = execute_tool(name, args)
        simulated = '"simulated": true' in result or '"simulated":true' in result
        is_error = '"error"' in result
        sink.emit(TOOL_RESULT, agent_id=self.definition.id, tool=name,
                  result=result, simulated=simulated, error=is_error)
        return result

    # ── entry point ────────────────────────────────────────────────────
    def run(self, query: str, entities: dict[str, Any] | None = None,
            upstream: str | None = None, sink: EventSink | None = None) -> AgentResult:
        entities = entities or {}
        sink = sink or NullSink()
        if self.llm is None:
            return self._run_heuristic(query, entities, upstream, sink)
        return self._run_llm(query, entities, upstream, sink)

    # ── LLM path ───────────────────────────────────────────────────────
    def _run_llm(self, query: str, entities: dict[str, Any],
                 upstream: str | None, sink: EventSink) -> AgentResult:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self._system_prompt(query)},
            {"role": "user", "content": self._user_prompt(query, entities, upstream)},
        ]
        tool_schemas = schemas_for(self.definition.tools)
        invocations: list[ToolInvocation] = []

        for _ in range(SETTINGS.max_tool_iterations):
            turn: AssistantTurn = self.llm.chat(messages, tools=tool_schemas or None)
            if not turn.wants_tools:
                return AgentResult(
                    agent_id=self.definition.id, agent_name=self.definition.name,
                    content=turn.content or "(no response)",
                    tool_calls=invocations, backend=self.llm.model_label,
                )
            # Record the assistant turn that requested tools.
            messages.append({
                "role": "assistant",
                "content": turn.content or "",
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.name,
                                  "arguments": json.dumps(tc.arguments, ensure_ascii=False)}}
                    for tc in turn.tool_calls
                ],
            })
            for tc in turn.tool_calls:
                result = self._exec_tool(tc.name, tc.arguments, sink)
                invocations.append(ToolInvocation(tc.name, tc.arguments, result))
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

        # Iteration budget exhausted — ask the model to wrap up without tools.
        final = self.llm.chat(messages, tools=None)
        return AgentResult(
            agent_id=self.definition.id, agent_name=self.definition.name,
            content=final.content or "(stopped after tool-iteration limit)",
            tool_calls=invocations, backend=self.llm.model_label,
        )

    # ── Heuristic path (no LLM configured) ─────────────────────────────
    def _run_heuristic(self, query: str, entities: dict[str, Any],
                       upstream: str | None, sink: EventSink) -> AgentResult:
        invocations: list[ToolInvocation] = []
        primary = _HEURISTIC_PRIMARY.get(self.definition.id)
        if primary is not None:
            spec = primary(entities)
            if spec is not None:
                name, args = spec
                result = self._exec_tool(name, args, sink)
                invocations.append(ToolInvocation(name, args, result))

        hits = self.kb.retrieve(query, top_k=2)
        guidance = "; ".join(h.heading for h in hits) if hits else "general policy"

        lines = [f"**{self.definition.name}** — {self.definition.description}"]
        if invocations:
            inv = invocations[0]
            lines.append(f"Ran `{inv.name}` → {inv.result}")
        else:
            need = self._missing_entity_hint()
            if need:
                lines.append(f"To proceed I need: {need}.")
        lines.append(f"Relevant policy: {guidance} (KB: {self.definition.kb}).")
        lines.append("_Heuristic mode: no LLM backend configured — set AZURE_OPENAI_* or "
                     "OPENAI_API_KEY for full natural-language handling._")

        return AgentResult(
            agent_id=self.definition.id, agent_name=self.definition.name,
            content="\n".join(lines), tool_calls=invocations, backend="heuristic",
        )

    def _missing_entity_hint(self) -> str:
        need_pnr = {"booking-retrieval", "name-change", "change-booking", "refund",
                    "refund-workflow", "rebooking", "disruption-rebooking",
                    "passenger-ssr", "medical-exception"}
        if self.definition.id in need_pnr:
            return "the 6-character PNR and passenger last name"
        if self.definition.id == "create-booking":
            return "origin, destination and departure date"
        return ""
