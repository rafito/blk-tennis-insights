"""Conexão SQLite e bootstrap do schema."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_FILE = REPO_ROOT / "schema.sql"


def get_db_path() -> Path:
    env = os.environ.get("BLK_SQLITE_PATH")
    if env:
        return Path(env).expanduser().resolve()
    return (REPO_ROOT / "database.sqlite").resolve()


def connect() -> sqlite3.Connection:
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30.0)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_schema_if_needed() -> bool:
    """Aplica schema.sql se o banco estiver vazio ou sem tabelas core. Retorna True se aplicou.

    Também garante, em toda chamada (schema novo ou banco já existente), que a
    coluna `disqualified` existe em `challonge_participants` e que a view
    `players` a expõe — ver `_ensure_disqualified_column`.
    """
    path = get_db_path()
    applied = False
    if not path.exists():
        _apply_schema(path)
        applied = True
    else:
        conn = sqlite3.connect(str(path), timeout=30.0)
        try:
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='challonge_tournaments'"
            )
            exists = cur.fetchone() is not None
        finally:
            conn.close()
        if not exists:
            _apply_schema(path)
            applied = True

    conn = sqlite3.connect(str(path), timeout=30.0)
    try:
        _ensure_disqualified_column(conn)
    finally:
        conn.close()
    return applied


def _ensure_disqualified_column(conn: sqlite3.Connection) -> None:
    """Garante que challonge_participants tem a coluna disqualified e que a view players a expõe.

    Idempotente: roda em todo init_schema_if_needed(), inclusive contra bancos
    já existentes que nunca reaplicam schema.sql sozinhos.
    """
    cols = [row[1] for row in conn.execute("PRAGMA table_info(challonge_participants)")]
    if "disqualified" not in cols:
        conn.execute(
            "ALTER TABLE challonge_participants ADD COLUMN disqualified INTEGER NOT NULL DEFAULT 0"
        )

    # Só recria a view se ela ainda não existir ou não expuser `disqualified` —
    # evita uma janela DROP→CREATE em que uma conexão concorrente que faça
    # `SELECT * FROM players` receba "no such table: players".
    cur = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='view' AND name='players'"
    )
    row = cur.fetchone()
    current_sql = row[0] if row else None
    if current_sql is None or "disqualified" not in current_sql.lower():
        conn.execute("DROP VIEW IF EXISTS players")
        conn.execute(
            "CREATE VIEW players AS SELECT id, name, disqualified FROM challonge_participants"
        )
    conn.commit()


def _apply_schema(path: Path) -> None:
    if not SCHEMA_FILE.is_file():
        raise FileNotFoundError(f"schema.sql não encontrado em {SCHEMA_FILE}")
    sql = SCHEMA_FILE.read_text(encoding="utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30.0)
    try:
        conn.executescript(sql)
        conn.commit()
    finally:
        conn.close()


def reset_database_file() -> None:
    path = get_db_path()
    if path.exists():
        path.unlink()
    _apply_schema(path)
