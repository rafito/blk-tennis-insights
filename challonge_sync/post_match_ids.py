"""Atualiza winner_id/loser_id para IDs locais (ChallongeUpdateMatchIdsCommand)."""
from __future__ import annotations

import sqlite3
from typing import Callable

LogFn = Callable[[str], None]


def update_winner_loser_ids(conn: sqlite3.Connection, log: LogFn) -> None:
    log("Iniciando atualização dos IDs nas partidas...")
    matches = list(
        conn.execute(
            """
            SELECT id, winner_id, loser_id FROM challonge_matches
            WHERE winner_id IS NOT NULL OR loser_id IS NOT NULL
            """
        )
    )
    updated = 0
    skipped = 0
    for m in matches:
        mid = m["id"]
        wid = m["winner_id"]
        lid = m["loser_id"]

        if wid is not None and str(wid).strip() != "":
            try:
                cid = int(wid)
            except (TypeError, ValueError):
                cid = None
            if cid is not None:
                p = conn.execute(
                    "SELECT id FROM challonge_participants WHERE challonge_id = ?",
                    (cid,),
                ).fetchone()
                if p:
                    new_w = int(p["id"])
                    if str(new_w) != str(wid):
                        conn.execute(
                            "UPDATE challonge_matches SET winner_id = ? WHERE id = ?",
                            (new_w, mid),
                        )
                        updated += 1
                else:
                    log(f"Participante vencedor não encontrado para ID {wid}")
                    skipped += 1

        if lid is not None and str(lid).strip() != "":
            try:
                cid = int(lid)
            except (TypeError, ValueError):
                cid = None
            if cid is not None:
                p = conn.execute(
                    "SELECT id FROM challonge_participants WHERE challonge_id = ?",
                    (cid,),
                ).fetchone()
                if p:
                    new_l = int(p["id"])
                    if str(new_l) != str(lid):
                        conn.execute(
                            "UPDATE challonge_matches SET loser_id = ? WHERE id = ?",
                            (new_l, mid),
                        )
                        updated += 1
                else:
                    log(f"Participante perdedor não encontrado para ID {lid}")
                    skipped += 1

    conn.commit()
    log("Atualização concluída!")
    log(f"Total de IDs atualizados: {updated}")
    log(f"Total de IDs ignorados: {skipped}")
