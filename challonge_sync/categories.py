"""Atualização de categorias (UpdateTournamentCategories)."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Callable

from .rules import determine_category_refresh

LogFn = Callable[[str], None]


def update_all_tournament_categories(conn: sqlite3.Connection, log: LogFn) -> None:
    log("Iniciando atualização das categorias dos torneios...")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    rows = list(conn.execute("SELECT id, name FROM challonge_tournaments"))
    updated = 0
    for r in rows:
        cat = determine_category_refresh(r["name"])
        conn.execute(
            "UPDATE challonge_tournaments SET category = ?, updated_at = ? WHERE id = ?",
            (cat, now, r["id"]),
        )
        log(f"Torneio '{r['name']}' atualizado para categoria: {cat}")
        updated += 1
    conn.commit()
    log(f"Processo concluído. {updated} torneios atualizados.")
