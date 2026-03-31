"""CLI: python -m challonge_sync [--force] [--reset-db]"""
from __future__ import annotations

import argparse
import os

from .pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Sincronização Challonge → SQLite")
    parser.add_argument("--force", action="store_true", help="Reprocessar todos os torneios")
    parser.add_argument(
        "--reset-db",
        action="store_true",
        dest="reset_db",
        help="Apaga e recria o arquivo SQLite (destrutivo)",
    )
    args = parser.parse_args()
    username = os.environ.get("CHALLONGE_USERNAME")
    api_key = os.environ.get("CHALLONGE_API_KEY")
    if not username or not api_key:
        raise SystemExit(
            "Defina CHALLONGE_USERNAME e CHALLONGE_API_KEY no ambiente."
        )
    run_pipeline(
        username=username,
        api_key=api_key,
        force=args.force,
        reset_db=args.reset_db,
    )


if __name__ == "__main__":
    main()
