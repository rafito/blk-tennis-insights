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
    """Aplica schema.sql se o banco estiver vazio ou sem tabelas core. Retorna True se aplicou."""
    path = get_db_path()
    if not path.exists():
        _apply_schema(path)
        return True
    conn = sqlite3.connect(str(path), timeout=30.0)
    try:
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='challonge_tournaments'"
        )
        if cur.fetchone():
            return False
    finally:
        conn.close()
    _apply_schema(path)
    return True


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
