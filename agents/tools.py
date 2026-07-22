"""Tool registry — schemas + implementations for every agent tool.

Two classes of tool:

* **Booking tools** (search_flights … retrieve_order) bridge to the real
  Create-Booking MCP server in ``mcp/`` — either in-process (importing
  ``mcp/src/tools/booking_tools.py``, which calls the live APIM gateway), over
  HTTP against a running SSE server, or in ``mock`` mode with canned data so the
  full flow runs offline.

* **Post-order tools** (update_passenger_name, check_refund_eligibility, add_ssr,
  create_case, send_email, …) are not yet implemented as live APIs on the MCP
  server. They are provided here as **schema-correct simulated handlers** so the
  specialist agents are fully wired and testable end-to-end. Each response is
  tagged ``"simulated": true`` — replace the handler body with a real API call
  when the corresponding backend exists. This mirrors the README §7 warning.

Tool schemas use the OpenAI function-calling format, which Azure OpenAI and
OpenAI both accept.
"""

from __future__ import annotations

import hashlib
import json
import sys
from typing import Any, Callable

from .settings import MCP_DIR, SETTINGS

# ═══════════════════════════════════════════════════════════════════════
# Small helpers
# ═══════════════════════════════════════════════════════════════════════


def _ok(**payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False)


def _err(message: str, **extra: Any) -> str:
    return json.dumps({"error": message, **extra}, ensure_ascii=False)


def _pseudo_id(prefix: str, *parts: Any, length: int = 6) -> str:
    """Deterministic short id derived from inputs (no RNG needed)."""
    raw = "|".join(str(p) for p in parts) or prefix
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest().upper()
    alnum = "".join(c for c in digest if c.isalnum())
    return f"{prefix}{alnum[:length]}" if prefix else alnum[:length]


# ═══════════════════════════════════════════════════════════════════════
# MCP booking bridge
# ═══════════════════════════════════════════════════════════════════════


def _ensure_mcp_on_path() -> None:
    p = str(MCP_DIR)
    if p not in sys.path:
        sys.path.insert(0, p)


_BOOKING_FUNCS: dict[str, Callable[..., str]] | None = None


def _load_booking_funcs() -> dict[str, Callable[..., str]]:
    """Lazily import the real MCP booking tool functions (in-process mode)."""
    global _BOOKING_FUNCS
    if _BOOKING_FUNCS is not None:
        return _BOOKING_FUNCS
    _ensure_mcp_on_path()
    from src.tools.booking_tools import (  # type: ignore  # noqa: E402
        tool_search_flights, tool_create_cart, tool_update_passengers,
        tool_get_service_catalog, tool_get_seat_map, tool_add_seats,
        tool_add_ancillaries, tool_retrieve_cart, tool_confirm_booking,
        tool_retrieve_order,
    )
    _BOOKING_FUNCS = {
        "search_flights": tool_search_flights,
        "create_cart": tool_create_cart,
        "update_passengers": tool_update_passengers,
        "get_service_catalog": tool_get_service_catalog,
        "get_seat_map": tool_get_seat_map,
        "add_seats": tool_add_seats,
        "add_ancillaries": tool_add_ancillaries,
        "retrieve_cart": tool_retrieve_cart,
        "confirm_booking": tool_confirm_booking,
        "retrieve_order": tool_retrieve_order,
    }
    return _BOOKING_FUNCS


# Positional argument order for each booking tool (matches booking_tools.py).
_BOOKING_ARG_ORDER: dict[str, list[str]] = {
    "search_flights": ["trip_type", "departure_location", "arrival_location",
                       "departure_date", "passengers", "fare_type", "return_date"],
    "create_cart": ["sku_ids", "airline_id", "agent_id"],
    "update_passengers": ["checkout_id", "passengers"],
    "get_service_catalog": ["checkout_id", "promotion_code"],
    "get_seat_map": ["checkout_id", "flight_id", "promotion_code"],
    "add_seats": ["checkout_id", "traveller"],
    "add_ancillaries": ["checkout_id", "traveller"],
    "retrieve_cart": ["checkout_id"],
    "confirm_booking": ["checkout_id"],
    "retrieve_order": ["order_id"],
}

_BOOKING_DEFAULTS: dict[str, dict[str, Any]] = {
    "search_flights": {"fare_type": "Economy", "return_date": ""},
    "create_cart": {"airline_id": "AY", "agent_id": "MCP-Agent"},
    "get_service_catalog": {"promotion_code": ""},
    "get_seat_map": {"promotion_code": ""},
}

_BOOKING_TOOLS = set(_BOOKING_ARG_ORDER)


def _call_booking_inprocess(name: str, args: dict[str, Any]) -> str:
    funcs = _load_booking_funcs()
    fn = funcs[name]
    defaults = _BOOKING_DEFAULTS.get(name, {})
    ordered = []
    for key in _BOOKING_ARG_ORDER[name]:
        if key in args:
            ordered.append(args[key])
        elif key in defaults:
            ordered.append(defaults[key])
        else:
            return _err(f"Missing required argument '{key}' for {name}.")
    return fn(*ordered)


def _call_booking_http(name: str, args: dict[str, Any]) -> str:
    import httpx  # local import; only needed in http mode

    url = f"{SETTINGS.mcp_http_url.rstrip('/')}/api/tools/{name}"
    headers = {"Content-Type": "application/json"}
    if SETTINGS.mcp_api_key:
        headers["Authorization"] = f"Bearer {SETTINGS.mcp_api_key}"
    try:
        resp = httpx.post(url, json={"arguments": args}, headers=headers, timeout=60.0)
    except Exception as exc:  # noqa: BLE001
        return _err(f"MCP HTTP call failed: {exc}", tool=name)
    if resp.status_code >= 400:
        return _err(f"MCP HTTP {resp.status_code}", tool=name, body=resp.text[:500])
    data = resp.json()
    result = data.get("result", data)
    return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)


def _call_booking_mock(name: str, args: dict[str, Any]) -> str:
    """Canned, internally-consistent booking data for offline demos."""
    if name == "search_flights":
        route = f"{args.get('departure_location', 'HEL')}-{args.get('arrival_location', 'LHR')}"
        sku = _pseudo_id("SKU", route, args.get("departure_date"), length=10)
        return _ok(simulated=True, tool=name, offers=[{
            "skuId": sku, "airline": "AY", "route": route,
            "departureDate": args.get("departure_date"),
            "flightNumber": "AY1331", "cabin": args.get("fare_type", "Economy"),
            "price": {"value": 189.00, "currencyCode": "EUR"},
            "fareFamily": "Classic",
        }])
    if name == "create_cart":
        sku_ids = args.get("sku_ids", [])
        checkout = _pseudo_id("CHK", *sku_ids, length=12)
        return _ok(simulated=True, tool=name, checkoutId=checkout,
                   cartId=_pseudo_id("CART", checkout, length=10),
                   passengers=[{"passengerId": "PAX1", "passengerTypeCode": "ADT"}],
                   connections=[{"flights": [{"id": _pseudo_id("FLT", checkout, length=8)}]}])
    if name == "update_passengers":
        return _ok(simulated=True, tool=name, checkoutId=args.get("checkout_id"),
                   status="passengers_updated",
                   passengers=args.get("passengers", []))
    if name == "get_service_catalog":
        return _ok(simulated=True, tool=name, services=[
            {"skuId": "SVC-BAG23", "name": "Extra bag 23kg", "price": {"value": 45, "currencyCode": "EUR"}},
            {"skuId": "SVC-MEAL", "name": "Hot meal", "price": {"value": 15, "currencyCode": "EUR"}},
            {"skuId": "SVC-LOUNGE", "name": "Lounge access", "price": {"value": 39, "currencyCode": "EUR"}},
        ])
    if name == "get_seat_map":
        return _ok(simulated=True, tool=name, flightId=args.get("flight_id"),
                   seats=[{"seat": "12A", "available": True, "price": {"value": 12, "currencyCode": "EUR"}},
                          {"seat": "12B", "available": True, "price": {"value": 12, "currencyCode": "EUR"}},
                          {"seat": "5C", "available": True, "price": {"value": 18, "currencyCode": "EUR"}}])
    if name in ("add_seats", "add_ancillaries"):
        return _ok(simulated=True, tool=name, checkoutId=args.get("checkout_id"),
                   status="added", detail=args.get("traveller", []))
    if name == "retrieve_cart":
        return _ok(simulated=True, tool=name, checkoutId=args.get("checkout_id"),
                   totalPrice={"value": 189.00, "currencyCode": "EUR"},
                   passengers=[{"passengerId": "PAX1", "name": "PENDING"}],
                   readyToConfirm=True)
    if name == "confirm_booking":
        pnr = _pseudo_id("", args.get("checkout_id"), length=6)
        return _ok(simulated=True, tool=name, orderId=pnr, pnr=pnr, status="CONFIRMED")
    if name == "retrieve_order":
        oid = args.get("order_id", "ABC123")
        return _ok(simulated=True, tool=name, pnr=oid, status="CONFIRMED",
                   passengers=[{"passengerId": "PAX1", "firstName": "SAMPLE",
                                "lastName": "PASSENGER", "passengerTypeCode": "ADT"}],
                   flights=[{"flightNumber": "AY1331", "route": "HEL-LHR",
                             "departure": "2026-08-20T08:10", "arrival": "2026-08-20T09:20"}],
                   services=[], seats=[], payment={"method": "VISA", "last4": "4242"})
    return _err(f"No mock for booking tool '{name}'.", tool=name)


def _call_booking(name: str, args: dict[str, Any]) -> str:
    mode = SETTINGS.mcp_mode
    if mode == "mock":
        return _call_booking_mock(name, args)
    if mode == "http":
        return _call_booking_http(name, args)
    # default: in-process (real APIM). Fall back to a clear error, never a crash.
    try:
        return _call_booking_inprocess(name, args)
    except ImportError as exc:
        return _err(
            f"Could not import MCP booking tools ({exc}). "
            "Install mcp deps (pip install -r mcp/requirements.txt) or set MCP_MODE=mock.",
            tool=name,
        )
    except Exception as exc:  # noqa: BLE001 — surface APIM/network errors as tool errors
        return _err(f"Booking tool '{name}' failed: {exc}", tool=name)


# ═══════════════════════════════════════════════════════════════════════
# Post-order simulated handlers (schema-correct scaffolds)
# ═══════════════════════════════════════════════════════════════════════

_SIM_NOTE = "Simulated response — wire to a live API to make this real (see README §7)."


def _sim(tool: str, **payload: Any) -> str:
    return json.dumps({"simulated": True, "tool": tool, "note": _SIM_NOTE, **payload},
                      ensure_ascii=False)


def _t_update_passenger_name(a: dict[str, Any]) -> str:
    old = f"{a.get('old_first_name', '')} {a.get('old_last_name', '')}".strip()
    new = f"{a.get('new_first_name', '')} {a.get('new_last_name', '')}".strip()
    diff = sum(1 for x, y in zip(old.lower().ljust(len(new)), new.lower().ljust(len(old))) if x != y)
    diff += abs(len(old) - len(new))
    change_type = "minor_correction" if diff <= 3 else "full_name_change"
    fee = {"minor_correction": 0}.get(change_type, 100)
    return _sim("update_passenger_name", orderId=a.get("order_id"),
                passengerId=a.get("passenger_id"), oldName=old, newName=new,
                changeType=change_type, feeEUR=fee, status="NAME_UPDATED")


def _t_quote_change(a: dict[str, Any]) -> str:
    quote_id = _pseudo_id("QT", a.get("order_id"), a.get("new_departure_date"))
    return _sim("quote_change", quoteId=quote_id, orderId=a.get("order_id"),
                changeFeeEUR=70, fareDifferenceEUR=45, totalEUR=115,
                newDepartureDate=a.get("new_departure_date"))


def _t_confirm_change(a: dict[str, Any]) -> str:
    return _sim("confirm_change", orderId=a.get("order_id"), quoteId=a.get("quote_id"),
                status="CHANGE_CONFIRMED")


def _t_check_refund_eligibility(a: dict[str, Any]) -> str:
    proposal = _pseudo_id("RP", a.get("order_id"), a.get("last_name"))
    return _sim("check_refund_eligibility", orderId=a.get("order_id"),
                refundStatus="refundable",
                totalPaidAmount={"value": 189.00, "currencyCode": "EUR"},
                totalUsedAmount={"value": 0.00, "currencyCode": "EUR"},
                totalPenalty={"value": 75.00, "currencyCode": "EUR"},
                netRefund={"value": 114.00, "currencyCode": "EUR"},
                refundProposalReferences=[{"refundProposalId": proposal}],
                nonEligibilityReasons=[])


def _t_process_refund(a: dict[str, Any]) -> str:
    ids = a.get("refund_proposal_ids") or []
    if not ids:
        return _err("refund_proposal_ids is required — run check_refund_eligibility first.",
                    tool="process_refund")
    return _sim("process_refund", orderId=a.get("order_id"), refundProposalIds=ids,
                status="REFUND_PROCESSED",
                refundedAmount={"value": 114.00, "currencyCode": "EUR"},
                refundMethod="VISA ****4242", timeline="5-10 business days")


def _t_search_alternatives(a: dict[str, Any]) -> str:
    return _sim("search_alternatives", orderId=a.get("order_id"), alternatives=[
        {"airBoundId": _pseudo_id("AB", a.get("order_id"), "1"),
         "flightNumber": "AY1333", "departure": "2026-08-20T14:10", "seatsLeft": 9},
        {"airBoundId": _pseudo_id("AB", a.get("order_id"), "2"),
         "flightNumber": "AY1335", "departure": "2026-08-20T19:40", "seatsLeft": 4},
    ])


def _t_auto_rebook(a: dict[str, Any]) -> str:
    return _sim("auto_rebook", orderId=a.get("order_id"), airBoundId=a.get("air_bound_id"),
                status="REBOOKED", feeWaived=True)


def _t_apply_waiver(a: dict[str, Any]) -> str:
    return _sim("apply_waiver", orderId=a.get("order_id"), reason=a.get("reason", "IROP"),
                waivedFeesEUR="ALL", status="WAIVER_APPLIED")


def _t_add_ssr(a: dict[str, Any]) -> str:
    return _sim("add_ssr", orderId=a.get("order_id"), passengerId=a.get("passenger_id"),
                ssrCode=(a.get("ssr_code") or "").upper(), status="SSR_ADDED",
                remarks=a.get("remarks", ""))


def _t_remove_ssr(a: dict[str, Any]) -> str:
    return _sim("remove_ssr", orderId=a.get("order_id"), passengerId=a.get("passenger_id"),
                ssrCode=(a.get("ssr_code") or "").upper(), status="SSR_REMOVED")


def _t_list_ssr(a: dict[str, Any]) -> str:
    return _sim("list_ssr", orderId=a.get("order_id"),
                ssrs=[{"passengerId": "PAX1", "ssrCode": "WCHR", "status": "CONFIRMED"}])


def _t_submit_medical_request(a: dict[str, Any]) -> str:
    case_id = _pseudo_id("MED", a.get("order_id"), a.get("condition"))
    return _sim("submit_medical_request", caseId=case_id, orderId=a.get("order_id"),
                medifRequired=True, status="SUBMITTED_TO_MEDICAL_DESK",
                condition=a.get("condition"), equipment=a.get("equipment", ""))


def _t_check_medical_status(a: dict[str, Any]) -> str:
    return _sim("check_medical_status", caseId=a.get("case_id"), status="UNDER_REVIEW",
                slaHours=48)


def _t_validate_card(a: dict[str, Any]) -> str:
    return _sim("validate_card", scheme=a.get("card_scheme", "VISA"),
                last4=a.get("last4", ""), currency=a.get("currency", "EUR"),
                supported=True, requires3DS=True)


def _t_process_payment(a: dict[str, Any]) -> str:
    return _sim("process_payment", reference=_pseudo_id("PAY", a.get("reference_id")),
                amount=a.get("amount"), currency=a.get("currency", "EUR"),
                method=a.get("method", "CARD"), status="PAYMENT_CAPTURED")


def _t_create_case(a: dict[str, Any]) -> str:
    case_id = _pseudo_id("CASE", a.get("subject"), a.get("order_id"))
    return _sim("create_case", caseId=case_id, subject=a.get("subject"),
                priority=a.get("priority", "P3"), status="OPEN", orderId=a.get("order_id"))


def _t_update_case(a: dict[str, Any]) -> str:
    return _sim("update_case", caseId=a.get("case_id"), status=a.get("status", "IN_PROGRESS"),
                note=a.get("note", ""))


def _t_close_case(a: dict[str, Any]) -> str:
    return _sim("close_case", caseId=a.get("case_id"), status="CLOSED",
                resolution=a.get("resolution", ""))


def _t_generate_summary(a: dict[str, Any]) -> str:
    return _sim("generate_summary", orderId=a.get("order_id"),
                summary="Concise case summary generated from interaction notes.")


def _t_send_email(a: dict[str, Any]) -> str:
    return _sim("send_email", to=a.get("to"), template=a.get("template"),
                orderId=a.get("order_id"), status="DRAFTED_PENDING_SEND")


def _t_route_to_agent(a: dict[str, Any]) -> str:
    # The orchestrator normally drives routing; this exists so the supervisor
    # agent can also emit a structured routing decision when run via an LLM.
    return _ok(target_agent=a.get("target_agent"), intent=a.get("intent"),
               priority=a.get("priority", "medium"),
               extracted_entities=a.get("extracted_entities", {}),
               chain_next=a.get("chain_next", ""))


_SIM_HANDLERS: dict[str, Callable[[dict[str, Any]], str]] = {
    "update_passenger_name": _t_update_passenger_name,
    "quote_change": _t_quote_change,
    "confirm_change": _t_confirm_change,
    "check_refund_eligibility": _t_check_refund_eligibility,
    "process_refund": _t_process_refund,
    "search_alternatives": _t_search_alternatives,
    "auto_rebook": _t_auto_rebook,
    "apply_waiver": _t_apply_waiver,
    "add_ssr": _t_add_ssr,
    "remove_ssr": _t_remove_ssr,
    "list_ssr": _t_list_ssr,
    "submit_medical_request": _t_submit_medical_request,
    "check_medical_status": _t_check_medical_status,
    "validate_card": _t_validate_card,
    "process_payment": _t_process_payment,
    "create_case": _t_create_case,
    "update_case": _t_update_case,
    "close_case": _t_close_case,
    "generate_summary": _t_generate_summary,
    "send_email": _t_send_email,
    "route_to_agent": _t_route_to_agent,
}


# ═══════════════════════════════════════════════════════════════════════
# Public dispatch
# ═══════════════════════════════════════════════════════════════════════


def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """Execute a tool by name and return a JSON string result."""
    args = arguments or {}
    if name in _BOOKING_TOOLS:
        return _call_booking(name, args)
    handler = _SIM_HANDLERS.get(name)
    if handler is None:
        return _err(f"Unknown tool '{name}'.")
    return handler(args)


# ═══════════════════════════════════════════════════════════════════════
# Tool schemas (OpenAI function-calling format)
# ═══════════════════════════════════════════════════════════════════════

def _fn(name: str, description: str, properties: dict[str, Any],
        required: list[str]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": True,
            },
        },
    }


_STR = {"type": "string"}


TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    # ── Booking tools (mirror the real MCP server signatures) ──────────
    "search_flights": _fn(
        "search_flights",
        "Search flight offers. Returns SKU IDs used to create a cart.",
        {
            "trip_type": {"type": "string", "enum": ["OW", "RT", "MC"]},
            "departure_location": {**_STR, "description": "IATA code, e.g. HEL"},
            "arrival_location": {**_STR, "description": "IATA code, e.g. LHR"},
            "departure_date": {**_STR, "description": "YYYY-MM-DD"},
            "passengers": {"type": "array", "items": {"type": "object"},
                           "description": '[{"passengerTypeCode":"ADT","discountCode":"ADT"}]'},
            "fare_type": {"type": "string", "enum": ["Economy", "Business", "First"]},
            "return_date": {**_STR, "description": "YYYY-MM-DD, required for RT"},
        },
        ["trip_type", "departure_location", "arrival_location", "departure_date", "passengers"],
    ),
    "create_cart": _fn(
        "create_cart", "Create a booking cart from selected flight SKU IDs.",
        {"sku_ids": {"type": "array", "items": _STR},
         "airline_id": _STR, "agent_id": _STR},
        ["sku_ids"],
    ),
    "update_passengers": _fn(
        "update_passengers", "Add passenger identity + contact details to a cart.",
        {"checkout_id": _STR,
         "passengers": {"type": "array", "items": {"type": "object"}}},
        ["checkout_id", "passengers"],
    ),
    "get_service_catalog": _fn(
        "get_service_catalog", "List ancillary services (bags, meals, wifi) for a cart.",
        {"checkout_id": _STR, "promotion_code": _STR},
        ["checkout_id"],
    ),
    "get_seat_map": _fn(
        "get_seat_map", "Retrieve seat availability + pricing for a flight segment.",
        {"checkout_id": _STR, "flight_id": _STR, "promotion_code": _STR},
        ["checkout_id", "flight_id"],
    ),
    "add_seats": _fn(
        "add_seats", "Assign seats to passengers.",
        {"checkout_id": _STR, "traveller": {"type": "array", "items": {"type": "object"}}},
        ["checkout_id", "traveller"],
    ),
    "add_ancillaries": _fn(
        "add_ancillaries", "Add ancillary services (bags, meals, wifi) to a cart.",
        {"checkout_id": _STR, "traveller": {"type": "array", "items": {"type": "object"}}},
        ["checkout_id", "traveller"],
    ),
    "retrieve_cart": _fn(
        "retrieve_cart", "Retrieve full cart state for review before confirmation.",
        {"checkout_id": _STR}, ["checkout_id"],
    ),
    "confirm_booking": _fn(
        "confirm_booking", "Confirm the booking and create the order (PNR). IRREVERSIBLE.",
        {"checkout_id": _STR}, ["checkout_id"],
    ),
    "retrieve_order": _fn(
        "retrieve_order", "Retrieve a confirmed order by PNR / order id.",
        {"order_id": {**_STR, "description": "6-char PNR, e.g. 9DVWPJ"},
         "last_name": _STR},
        ["order_id"],
    ),

    # ── Name change ────────────────────────────────────────────────────
    "update_passenger_name": _fn(
        "update_passenger_name", "Update a passenger name on an existing booking.",
        {"order_id": _STR, "last_name": _STR, "passenger_id": _STR,
         "old_first_name": _STR, "old_last_name": _STR,
         "new_first_name": _STR, "new_last_name": _STR,
         "title": {"type": "string", "enum": ["MR", "MRS", "MS", "MISS", "DR"]}},
        ["order_id", "passenger_id", "new_first_name", "new_last_name"],
    ),

    # ── Change booking ─────────────────────────────────────────────────
    "quote_change": _fn(
        "quote_change", "Quote change fee + fare difference for a date/route change.",
        {"order_id": _STR, "last_name": _STR, "new_departure_date": _STR,
         "new_origin": _STR, "new_destination": _STR},
        ["order_id"],
    ),
    "confirm_change": _fn(
        "confirm_change", "Apply a previously quoted booking change.",
        {"order_id": _STR, "last_name": _STR, "quote_id": _STR},
        ["order_id", "quote_id"],
    ),

    # ── Refund ─────────────────────────────────────────────────────────
    "check_refund_eligibility": _fn(
        "check_refund_eligibility",
        "Check refund eligibility and compute the refund breakdown (GraphQL query).",
        {"order_id": _STR, "last_name": _STR},
        ["order_id", "last_name"],
    ),
    "process_refund": _fn(
        "process_refund",
        "Execute the CancellationAndRefund mutation. IRREVERSIBLE. Requires refund_proposal_ids.",
        {"order_id": _STR, "last_name": _STR,
         "refund_proposal_ids": {"type": "array", "items": _STR}},
        ["order_id", "last_name", "refund_proposal_ids"],
    ),

    # ── Disruption / rebooking ─────────────────────────────────────────
    "search_alternatives": _fn(
        "search_alternatives", "Find alternative flights for a disrupted itinerary.",
        {"order_id": _STR, "last_name": _STR}, ["order_id"],
    ),
    "auto_rebook": _fn(
        "auto_rebook", "Rebook a passenger onto a chosen alternative flight.",
        {"order_id": _STR, "last_name": _STR, "air_bound_id": _STR},
        ["order_id", "air_bound_id"],
    ),
    "apply_waiver": _fn(
        "apply_waiver", "Waive change fees / fare difference for an airline-caused disruption.",
        {"order_id": _STR, "last_name": _STR, "reason": _STR},
        ["order_id", "reason"],
    ),

    # ── SSR ────────────────────────────────────────────────────────────
    "add_ssr": _fn(
        "add_ssr", "Add a Special Service Request (IATA SSR code) to a passenger.",
        {"order_id": _STR, "last_name": _STR, "passenger_id": _STR,
         "ssr_code": {**_STR, "description": "IATA code, e.g. WCHR, VGML, UMNR"},
         "remarks": _STR},
        ["order_id", "passenger_id", "ssr_code"],
    ),
    "remove_ssr": _fn(
        "remove_ssr", "Remove an SSR from a passenger.",
        {"order_id": _STR, "last_name": _STR, "passenger_id": _STR, "ssr_code": _STR},
        ["order_id", "passenger_id", "ssr_code"],
    ),
    "list_ssr": _fn(
        "list_ssr", "List SSRs on a booking.",
        {"order_id": _STR, "last_name": _STR}, ["order_id"],
    ),

    # ── Medical ────────────────────────────────────────────────────────
    "submit_medical_request": _fn(
        "submit_medical_request", "Open a MEDIF / fit-to-fly clearance case with the medical desk.",
        {"order_id": _STR, "last_name": _STR, "condition": _STR, "equipment": _STR},
        ["order_id", "condition"],
    ),
    "check_medical_status": _fn(
        "check_medical_status", "Check the status of a medical clearance case.",
        {"case_id": _STR}, ["case_id"],
    ),

    # ── Payment ────────────────────────────────────────────────────────
    "validate_card": _fn(
        "validate_card", "Validate card scheme/currency support. Never accepts full PAN or CVV.",
        {"card_scheme": _STR, "last4": _STR, "currency": _STR},
        [],
    ),
    "process_payment": _fn(
        "process_payment", "Capture a payment against a cart or order.",
        {"reference_id": {**_STR, "description": "checkout_id or order_id"},
         "amount": {"type": "number"}, "currency": _STR, "method": _STR},
        ["reference_id", "amount"],
    ),

    # ── Case management ────────────────────────────────────────────────
    "create_case": _fn(
        "create_case", "Open a service case with an SLA priority (P1-P4).",
        {"subject": _STR, "priority": {"type": "string", "enum": ["P1", "P2", "P3", "P4"]},
         "order_id": _STR, "description": _STR},
        ["subject", "priority"],
    ),
    "update_case": _fn(
        "update_case", "Update a case status / add a note.",
        {"case_id": _STR, "status": _STR, "note": _STR}, ["case_id"],
    ),
    "close_case": _fn(
        "close_case", "Close a case with a resolution.",
        {"case_id": _STR, "resolution": _STR}, ["case_id", "resolution"],
    ),

    # ── Communication ──────────────────────────────────────────────────
    "generate_summary": _fn(
        "generate_summary", "Generate a concise case summary.",
        {"order_id": _STR, "interaction_notes": _STR}, [],
    ),
    "send_email": _fn(
        "send_email", "Draft/queue a templated customer email. Customer-facing — confirm first.",
        {"to": _STR, "template": {**_STR, "description": "confirmation|name_change|cancellation|disruption|refund"},
         "order_id": _STR, "variables": {"type": "object"}},
        ["to", "template"],
    ),

    # ── Supervisor ─────────────────────────────────────────────────────
    "route_to_agent": _fn(
        "route_to_agent", "Route the request to a specialized agent.",
        {"target_agent": _STR, "intent": _STR,
         "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
         "extracted_entities": {"type": "object"}, "chain_next": _STR},
        ["target_agent", "intent", "priority"],
    ),
}


def schemas_for(tool_names: tuple[str, ...] | list[str]) -> list[dict[str, Any]]:
    """Return the OpenAI-format schemas for the given tool names (in order)."""
    out: list[dict[str, Any]] = []
    for name in tool_names:
        schema = TOOL_SCHEMAS.get(name)
        if schema is not None:
            out.append(schema)
    return out
