"""Uvicorn entry point for the orchestrator API.

    python -m agents.server                 # 127.0.0.1:8100
    python -m agents.server --host 0.0.0.0 --port 8100
    python -m agents.server --reload        # dev auto-reload

Then open http://127.0.0.1:8100/ for the live-workflow UI, or /docs for the API.
"""

from __future__ import annotations

import argparse
import sys

from .settings import SETTINGS


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agents.server", description=__doc__)
    parser.add_argument("--host", default=SETTINGS.api_host)
    parser.add_argument("--port", type=int, default=SETTINGS.api_port)
    parser.add_argument("--reload", action="store_true", help="auto-reload (dev)")
    args = parser.parse_args(argv)

    try:
        import uvicorn
    except ImportError:
        print("uvicorn is required: pip install -r agents/requirements.txt", file=sys.stderr)
        return 1

    print(f"Nevio agents API -> http://{args.host}:{args.port}  (UI: /  |  docs: /docs)")
    if args.reload:
        # reload needs an import string, not an app object.
        uvicorn.run("agents.api:build_app", host=args.host, port=args.port,
                    reload=True, factory=True)
    else:
        from .api import build_app
        uvicorn.run(build_app(), host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
