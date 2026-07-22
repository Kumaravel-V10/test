"""Nevio Service Center — Multi-Agent Orchestrator.

A supervisor-orchestrated fleet of 15 airline service-center agents that
route customer requests to specialized agents, ground their answers in the
knowledge base (``knowledge-docs-v1/``), and execute real booking actions
through the Create-Booking MCP server (``mcp/``).

Entry point: ``python -m agents`` (interactive) or ``agents.cli:main``.
"""

from __future__ import annotations

__version__ = "1.0.0"

__all__ = ["__version__"]
