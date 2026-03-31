"""Sincronização com API (equivalente a ChallongeSyncCommand)."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Callable

from . import client as challonge_client
from .rules import (
    adjust_date_year,
    determine_category_sync,
    resolve_tournament_year,
    should_skip_participant_name,
    should_skip_tournament_name,
)

LogFn = Callable[[str], None]


def _now_sqlite() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _scores_csv_value(m: dict[str, Any]) -> str | None:
    sc = m.get("scores_csv")
    if sc is None:
        return None
    if isinstance(sc, str):
        return sc
    return json.dumps(sc, ensure_ascii=False)


def sync_tournaments(conn: sqlite3.Connection, http: Any, *, log: LogFn) -> None:
    data = challonge_client.fetch_tournaments_json(http, log)
    for item in data:
        t = item["tournament"]
        name = t["name"]
        if should_skip_tournament_name(name):
            log(f"Ignorando torneio: {name}")
            continue
        started_raw = t.get("started_at")
        completed_raw = t.get("completed_at")
        started_at = adjust_date_year(started_raw, name) if started_raw else None
        completed_at = adjust_date_year(completed_raw, name) if completed_raw else None
        tyear = resolve_tournament_year(started_at, completed_at, name)
        if tyear is not None and tyear < 2022:
            log(f"Ignorando torneio por ser anterior a 2022: {name} (ano {tyear})")
            continue
        cid = int(t["id"])
        category = determine_category_sync(name)
        raw = json.dumps(t, ensure_ascii=False)
        row = conn.execute(
            "SELECT id FROM challonge_tournaments WHERE challonge_id = ?",
            (cid,),
        ).fetchone()
        now = _now_sqlite()
        if row is None:
            conn.execute(
                """
                INSERT INTO challonge_tournaments (
                    challonge_id, name, category, url, tournament_type, state,
                    started_at, completed_at, open_signup, hold_third_place_match,
                    participants_count, description, raw_data, synced, last_sync_at,
                    created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    cid,
                    name,
                    category,
                    t["url"],
                    t["tournament_type"],
                    t["state"],
                    started_at,
                    completed_at,
                    1 if t.get("open_signup") else 0,
                    1 if t.get("hold_third_place_match") else 0,
                    int(t.get("participants_count") or 0),
                    t.get("description"),
                    raw,
                    0,
                    None,
                    now,
                    now,
                ),
            )
            log(f"Sincronizando torneio (novo): {name} (ID: {cid})")
        else:
            conn.execute(
                """
                UPDATE challonge_tournaments SET
                    name = ?, category = ?, url = ?, tournament_type = ?, state = ?,
                    started_at = ?, completed_at = ?, open_signup = ?, hold_third_place_match = ?,
                    participants_count = ?, description = ?, raw_data = ?, updated_at = ?
                WHERE challonge_id = ?
                """,
                (
                    name,
                    category,
                    t["url"],
                    t["tournament_type"],
                    t["state"],
                    started_at,
                    completed_at,
                    1 if t.get("open_signup") else 0,
                    1 if t.get("hold_third_place_match") else 0,
                    int(t.get("participants_count") or 0),
                    t.get("description"),
                    raw,
                    now,
                    cid,
                ),
            )
            log(f"Sincronizando torneio: {name} (ID: {cid})")
    conn.commit()


def _get_tournaments_to_sync(conn: sqlite3.Connection, force: bool) -> list[sqlite3.Row]:
    if force:
        return list(conn.execute("SELECT * FROM challonge_tournaments ORDER BY id"))
    return list(conn.execute("SELECT * FROM challonge_tournaments WHERE synced = 0 ORDER BY id"))


def _local_pid_for_challonge(conn: sqlite3.Connection, challonge_pid: Any) -> int | None:
    if challonge_pid is None:
        return None
    row = conn.execute(
        "SELECT id FROM challonge_participants WHERE challonge_id = ?",
        (int(challonge_pid),),
    ).fetchone()
    return int(row["id"]) if row else None


def sync_participants_and_matches(
    conn: sqlite3.Connection,
    http: Any,
    *,
    force: bool,
    log: LogFn,
) -> None:
    tournaments = _get_tournaments_to_sync(conn, force)
    log(f"Total de torneios para sincronizar: {len(tournaments)}")
    now = _now_sqlite()
    for tournament in tournaments:
        tid = tournament["id"]
        challonge_tid = int(tournament["challonge_id"])
        tname = tournament["name"]
        try:
            plist = challonge_client.fetch_participants_json(http, challonge_tid, log)
            for pitem in plist:
                p = pitem["participant"]
                if should_skip_participant_name(p["name"]):
                    log(f"Ignorando dupla: {p['name']}")
                    continue
                log(f"Sincronizando participante: {p['name']}")
                pid = int(p["id"])
                raw_p = json.dumps(p, ensure_ascii=False)
                conn.execute(
                    """
                    INSERT INTO challonge_participants (
                        tournament_id, challonge_id, name, seed, display_name, username, email,
                        checked_in, checked_in_at, active, final_rank, raw_data, synced, last_sync_at,
                        created_at, updated_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(challonge_id) DO UPDATE SET
                        tournament_id = excluded.tournament_id,
                        name = excluded.name,
                        seed = excluded.seed,
                        display_name = excluded.display_name,
                        username = excluded.username,
                        email = excluded.email,
                        checked_in = excluded.checked_in,
                        checked_in_at = excluded.checked_in_at,
                        active = excluded.active,
                        final_rank = excluded.final_rank,
                        raw_data = excluded.raw_data,
                        synced = excluded.synced,
                        last_sync_at = excluded.last_sync_at,
                        updated_at = excluded.updated_at,
                        user_id = challonge_participants.user_id,
                        player_id = challonge_participants.player_id
                    """,
                    (
                        tid,
                        pid,
                        p["name"],
                        p.get("seed"),
                        p.get("display_name"),
                        p.get("username"),
                        p.get("email"),
                        1 if p.get("checked_in") else 0,
                        p.get("checked_in_at"),
                        1 if p.get("active", True) else 0,
                        p.get("final_rank"),
                        raw_p,
                        1,
                        now,
                        now,
                        now,
                    ),
                )

            mlist = challonge_client.fetch_matches_json(http, challonge_tid, log)
            for mitem in mlist:
                m = mitem["match"]
                mid = int(m["id"])
                player1_id = _local_pid_for_challonge(conn, m.get("player1_id"))
                player2_id = _local_pid_for_challonge(conn, m.get("player2_id"))
                raw_m = json.dumps(m, ensure_ascii=False)
                w = m.get("winner_id")
                l = m.get("loser_id")
                conn.execute(
                    """
                    INSERT INTO challonge_matches (
                        tournament_id, challonge_id, player1_id, player2_id, round, state,
                        winner_id, loser_id, score, started_at, completed_at, underway, underway_at,
                        scores_csv, raw_data, synced, last_sync_at, created_at, updated_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(challonge_id) DO UPDATE SET
                        tournament_id = excluded.tournament_id,
                        player1_id = excluded.player1_id,
                        player2_id = excluded.player2_id,
                        round = excluded.round,
                        state = excluded.state,
                        winner_id = excluded.winner_id,
                        loser_id = excluded.loser_id,
                        score = excluded.score,
                        started_at = excluded.started_at,
                        completed_at = excluded.completed_at,
                        underway = excluded.underway,
                        underway_at = excluded.underway_at,
                        scores_csv = excluded.scores_csv,
                        raw_data = excluded.raw_data,
                        synced = excluded.synced,
                        last_sync_at = excluded.last_sync_at,
                        updated_at = excluded.updated_at
                    """,
                    (
                        tid,
                        mid,
                        player1_id,
                        player2_id,
                        m.get("round"),
                        m.get("state") or "pending",
                        w,
                        l,
                        m.get("score"),
                        m.get("started_at"),
                        m.get("completed_at"),
                        1 if m.get("underway") else 0,
                        m.get("underway_at"),
                        _scores_csv_value(m),
                        raw_m,
                        1,
                        now,
                        now,
                        now,
                    ),
                )

            conn.execute(
                """
                UPDATE challonge_tournaments SET synced = 1, last_sync_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (now, now, tid),
            )
            conn.commit()
            log(f"Torneio {tname} sincronizado com sucesso")
        except Exception as e:
            log(f"Erro ao sincronizar torneio {tname}: {e}")
            conn.rollback()
