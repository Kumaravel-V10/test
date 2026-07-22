"""Offline smoke test — proves the fleet wires together with no LLM and no network.

Forces heuristic LLM mode + mock MCP mode, then exercises:
  1. Import + definition integrity (15 agents, tools resolvable, KBs present).
  2. Entity extraction + intent routing for representative requests.
  3. A full booking chain through the MCP bridge (mock) — search → confirm.
  4. The refund chain threading refundProposalIds between agents.

Run:  python -m agents.smoke_test      (from the repo root)
Exit code 0 = all checks passed.
"""

from __future__ import annotations

import os

# Force fully-offline mode BEFORE importing anything that reads settings.
os.environ.setdefault("LLM_BACKEND", "heuristic")
os.environ.setdefault("MCP_MODE", "mock")

from agents.definitions import ALL_AGENTS, INTENT_ROUTING, get_agent  # noqa: E402
from agents.knowledge import KB_SOURCES, missing_documents  # noqa: E402
from agents.orchestrator import Orchestrator, extract_entities  # noqa: E402
from agents.tools import TOOL_SCHEMAS, execute_tool  # noqa: E402

_failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"  [{status}] {label}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        _failures.append(label)


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def test_definitions() -> None:
    section("Definitions & wiring")
    check("15 agents defined", len(ALL_AGENTS) == 15, f"got {len(ALL_AGENTS)}")
    for a in ALL_AGENTS:
        for t in a.tools:
            check(f"{a.id}: tool '{t}' has a schema", t in TOOL_SCHEMAS)
        check(f"{a.id}: KB '{a.kb}' has sources", a.kb in KB_SOURCES)
    check("no missing KB documents", not missing_documents(), str(missing_documents()))
    check("every intent routes to known agents",
          all(aid in {x.id for x in ALL_AGENTS}
              for chain in INTENT_ROUTING.values() for aid in chain))


def test_entities() -> None:
    section("Entity extraction")
    e = extract_entities("Please pull up my booking, PNR is 9DVWPJ, last name Ibrahim")
    check("PNR extracted", e.get("pnr") == "9DVWPJ", str(e))
    check("last name extracted", e.get("last_name", "").lower() == "ibrahim", str(e))
    e2 = extract_entities("Book from HEL to LHR on 2026-08-20")
    check("route extracted", e2.get("origin") == "HEL" and e2.get("destination") == "LHR", str(e2))
    check("date extracted", e2.get("departure_date") == "2026-08-20", str(e2))


def test_routing() -> None:
    section("Intent routing")
    orch = Orchestrator()
    cases = {
        "Retrieve PNR 9DVWPJ, last name Ibrahim": ("RETRIEVE_BOOKING", ["booking-retrieval"]),
        "I want to cancel booking 9DVWPJ and get a refund":
            ("CANCEL_AND_REFUND", ["booking-retrieval", "refund", "refund-workflow"]),
        "My name is spelled wrong, it says Jhon but should be John on ABC123":
            ("NAME_CHANGE", ["booking-retrieval", "name-change"]),
        "I need a wheelchair at the airport for booking ABC123":
            ("SSR_REQUEST", ["passenger-ssr"]),
        "My flight was cancelled, I need to be rebooked":
            ("DISRUPTION_REBOOKING", ["disruption-rebooking"]),
    }
    for msg, (intent, chain) in cases.items():
        r = orch.handle(msg)
        check(f"intent «{msg[:34]}…»", r.intent == intent, f"got {r.intent}")
        check(f"chain «{msg[:34]}…»", r.chain == chain, f"got {r.chain}")


def test_escalation() -> None:
    section("Escalation")
    orch = Orchestrator()
    r = orch.handle("This is fraud, my card was stolen and used on booking ABC123")
    check("fraud escalation flagged", r.escalation == "fraud", str(r.escalation))
    check("escalation notice returned", "Escalation triggered" in r.final_answer)


def test_booking_chain() -> None:
    section("Booking chain via MCP bridge (mock)")
    search = execute_tool("search_flights", {
        "trip_type": "OW", "departure_location": "HEL", "arrival_location": "LHR",
        "departure_date": "2026-08-20",
        "passengers": [{"passengerTypeCode": "ADT", "discountCode": "ADT"}],
    })
    import json
    offers = json.loads(search).get("offers", [])
    check("search returned an offer", bool(offers), search)
    sku = offers[0]["skuId"]

    cart = json.loads(execute_tool("create_cart", {"sku_ids": [sku]}))
    checkout = cart.get("checkoutId")
    check("cart returned checkoutId", bool(checkout), str(cart))

    execute_tool("update_passengers", {"checkout_id": checkout, "passengers": [
        {"id": "PAX1", "passengerTypeCode": "ADT",
         "identityDetails": {"firstName": "AVA", "lastName": "NOVAK"},
         "contactDetails": {"email": "a@x.com", "mobile": "+3580000000"}}]})
    review = json.loads(execute_tool("retrieve_cart", {"checkout_id": checkout}))
    check("cart ready to confirm", review.get("readyToConfirm") is True, str(review))
    confirmed = json.loads(execute_tool("confirm_booking", {"checkout_id": checkout}))
    check("confirm returned a PNR", bool(confirmed.get("pnr")), str(confirmed))


def test_refund_chain() -> None:
    section("Refund chain threads refundProposalIds")
    orch = Orchestrator()
    r = orch.handle("Cancel booking 9DVWPJ, last name Ibrahim, and refund me")
    # refund agent should surface proposal ids; workflow agent should consume them.
    joined = " ".join(res.content for res in r.results)
    check("refund eligibility ran", "refundProposalReferences" in joined or "refundProposal" in joined,
          joined[:200])
    check("refund workflow processed", "REFUND_PROCESSED" in joined, joined[-200:])


def main() -> int:
    print("Nevio agents — offline smoke test (heuristic + mock)")
    test_definitions()
    test_entities()
    test_routing()
    test_escalation()
    test_booking_chain()
    test_refund_chain()
    print("\n" + "-" * 60)
    if _failures:
        print(f"FAILED ({len(_failures)}): " + ", ".join(_failures))
        return 1
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
