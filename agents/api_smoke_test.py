"""API smoke test — verifies the HTTP layer end to end (offline).

Forces heuristic + mock mode, builds the FastAPI app, and drives it with the
in-process TestClient (no network, no live server). Skips cleanly with a clear
message if fastapi/uvicorn aren't installed yet.

Run:  python -m agents.api_smoke_test
"""

from __future__ import annotations

import os

os.environ.setdefault("LLM_BACKEND", "heuristic")
os.environ.setdefault("MCP_MODE", "mock")

_failures: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}" + (f" — {detail}" if detail and not cond else ""))
    if not cond:
        _failures.append(label)


def main() -> int:
    print("Nevio agents — API smoke test (heuristic + mock)")
    try:
        from fastapi.testclient import TestClient
    except Exception as exc:  # noqa: BLE001
        print(f"\nSKIPPED — fastapi/testclient not available ({exc}).")
        print("Install with:  pip install -r agents/requirements.txt")
        return 0

    from agents.api import build_app
    client = TestClient(build_app())

    print("\n=== introspection ===")
    h = client.get("/health").json()
    check("health ok", h.get("status") == "healthy", str(h))
    check("health reports 15 agents", h.get("agents") == 15, str(h))
    check("health lists event types", "run.completed" in h.get("event_types", []))

    agents = client.get("/agents").json()
    check("/agents returns 15", len(agents) == 15, str(len(agents)))

    detail = client.get("/agents/refund")
    check("/agents/refund 200", detail.status_code == 200, str(detail.status_code))
    check("agent detail has prompt", bool(detail.json().get("system_prompt")))
    check("/agents/nope 404", client.get("/agents/nope").status_code == 404)

    tools = client.get("/tools").json()
    check("/tools returns schemas", tools.get("total", 0) >= 25, str(tools.get("total")))
    check("/intents returns routing", "CANCEL_AND_REFUND" in client.get("/intents").json())

    print("\n=== POST /chat (full workflow) ===")
    r = client.post("/chat", json={"message": "Cancel booking 9DVWPJ, last name Ibrahim, and refund me",
                                   "session_id": "test-1"})
    check("/chat 200", r.status_code == 200, r.text[:200])
    body = r.json()
    check("intent CANCEL_AND_REFUND", body["intent"] == "CANCEL_AND_REFUND", body["intent"])
    check("chain has 3 agents", len(body["chain"]) == 3, str(body["chain"]))
    check("steps recorded", len(body["steps"]) == 3, str(len(body["steps"])))
    check("events recorded", len(body["events"]) >= 10, str(len(body["events"])))
    tool_names = [t["name"] for s in body["steps"] for t in s["tools"]]
    check("process_refund ran", "process_refund" in tool_names, str(tool_names))
    check("final answer present", bool(body["final_answer"]))

    print("\n=== session carry-over ===")
    client.post("/chat", json={"message": "Retrieve PNR 9DVWPJ, last name Ibrahim", "session_id": "sess-x"})
    r2 = client.post("/chat", json={"message": "cancel it and refund me", "session_id": "sess-x"})
    check("PNR carried across turns", r2.json()["entities"].get("pnr") == "9DVWPJ",
          str(r2.json()["entities"]))

    print("\n=== GET /chat/stream (SSE) ===")
    s = client.get("/chat/stream", params={"message": "Retrieve PNR 9DVWPJ, last name Ibrahim"})
    check("stream 200", s.status_code == 200, str(s.status_code))
    check("stream is event-stream", "text/event-stream" in s.headers.get("content-type", ""),
          s.headers.get("content-type", ""))
    check("stream emits intent.classified", "intent.classified" in s.text)
    check("stream emits run.completed", "run.completed" in s.text)

    print("\n=== reference UI ===")
    ui = client.get("/")
    check("UI served at /", ui.status_code == 200 and "Control Tower" in ui.text)

    print("\n" + "-" * 56)
    if _failures:
        print(f"FAILED ({len(_failures)}): " + ", ".join(_failures))
        return 1
    print("ALL API CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
