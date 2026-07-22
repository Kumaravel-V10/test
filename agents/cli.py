"""Command-line entry point for the multi-agent orchestrator.

Usage:
    python -m agents                       # interactive REPL
    python -m agents -m "Retrieve PNR 9DVWPJ, last name Ibrahim"
    python -m agents --list                # list the 15 agents
    python -m agents --diagnostics         # show backend / KB / MCP status
"""

from __future__ import annotations

import argparse
import sys

from .definitions import ALL_AGENTS, INTENT_ROUTING
from .knowledge import missing_documents
from .llm import build_client
from .orchestrator import Orchestrator
from .settings import KNOWLEDGE_DIR, SETTINGS


def _print_banner(orch: Orchestrator) -> None:
    print("=" * 68)
    print(" Nevio Service Center — Multi-Agent Orchestrator")
    print("=" * 68)
    print(f" LLM backend : {orch.backend}")
    print(f" MCP mode    : {SETTINGS.mcp_mode}"
          + (f" ({SETTINGS.mcp_http_url})" if SETTINGS.mcp_mode == 'http' else ""))
    print(f" Agents      : {len(ALL_AGENTS)}  |  Intents: {len(INTENT_ROUTING)}")
    if orch.backend == "heuristic":
        print(" NOTE        : no LLM configured — running deterministic heuristic mode.")
        print("               Set AZURE_OPENAI_* or OPENAI_API_KEY for full handling.")
    print("=" * 68)


def _list_agents() -> None:
    print(f"{'#':>2}  {'Agent':32}  {'KB':26}  Reasoning")
    print("-" * 78)
    for i, a in enumerate(ALL_AGENTS, 1):
        print(f"{i:>2}  {a.name:32}  {a.kb:26}  {a.reasoning}")


def _diagnostics() -> None:
    print("Backend resolution :", SETTINGS.resolved_backend())
    client = build_client(SETTINGS)
    print("LLM client         :", client.model_label if client else "heuristic (none)")
    print("MCP mode           :", SETTINGS.mcp_mode)
    print("Knowledge dir      :", KNOWLEDGE_DIR)
    missing = missing_documents()
    if missing:
        print("Missing KB docs    :", ", ".join(missing))
    else:
        print("Missing KB docs    : none — all 19 present")


def _run_once(orch: Orchestrator, message: str) -> None:
    result = orch.handle(message)
    print(result.transcript())


def _repl(orch: Orchestrator) -> None:
    print("Type a customer request (or 'quit' to exit).\n")
    while True:
        try:
            message = input("customer> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not message:
            continue
        if message.lower() in {"quit", "exit", ":q"}:
            break
        print()
        _run_once(orch, message)
        print()


def _force_utf8_output() -> None:
    """Windows consoles default to cp1252 and choke on → / ⚠. Force UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 — best effort; older/odd streams
            pass


def main(argv: list[str] | None = None) -> int:
    _force_utf8_output()
    parser = argparse.ArgumentParser(prog="agents", description=__doc__)
    parser.add_argument("-m", "--message", help="handle one message and exit")
    parser.add_argument("--list", action="store_true", help="list all agents")
    parser.add_argument("--diagnostics", action="store_true", help="show runtime status")
    args = parser.parse_args(argv)

    if args.list:
        _list_agents()
        return 0
    if args.diagnostics:
        _diagnostics()
        return 0

    orch = Orchestrator()
    _print_banner(orch)
    if args.message:
        _run_once(orch, args.message)
    else:
        _repl(orch)
    return 0


if __name__ == "__main__":
    sys.exit(main())
