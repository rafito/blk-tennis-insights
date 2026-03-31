"""Orquestração do pipeline completo (equivalente a challonge:sync-all)."""
from __future__ import annotations

from typing import Callable

from . import categories, merge, post_match_ids, sync
from .client import make_client
from .db import connect, init_schema_if_needed, reset_database_file

LogFn = Callable[[str], None]


def run_pipeline(
    *,
    username: str,
    api_key: str,
    force: bool = False,
    reset_db: bool = False,
    log: LogFn | None = None,
) -> None:
    def _log(msg: str) -> None:
        if log:
            log(msg)
        else:
            print(msg)

    if reset_db:
        _log("Resetando banco de dados...")
        reset_database_file()
    else:
        init_schema_if_needed()

    conn = connect()
    try:
        _log("Iniciando sincronização com Challonge...")
        with make_client(username, api_key) as http:
            sync.sync_tournaments(conn, http, log=_log)
            sync.sync_participants_and_matches(conn, http, force=force, log=_log)
        post_match_ids.update_winner_loser_ids(conn, _log)
        merge.merge_participants(conn, exact_only=True, max_group_size=0, log=_log)
        merge.merge_participants(conn, exact_only=False, similarity=80.0, max_group_size=0, log=_log)
        categories.update_all_tournament_categories(conn, _log)
        _log("Sincronização completa concluída com sucesso!")
    finally:
        conn.close()
