"""Mescla participantes duplicados (ChallongeMergeParticipantsCommand), sem prompt interativo."""
from __future__ import annotations

import json
import os
import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Callable

LogFn = Callable[[str], None]

REPO_ROOT = Path(__file__).resolve().parent.parent


def _merge_decisions_path() -> Path:
    env = os.environ.get("MERGE_DECISIONS_PATH")
    if env:
        return Path(env).expanduser().resolve()
    return REPO_ROOT / "merge_decisions.json"


def _load_merge_decisions() -> dict[str, bool]:
    p = _merge_decisions_path()
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _ascii_fold(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def normalize_name_for_comparison(s: str) -> str:
    s = _ascii_fold(s)
    s = re.sub(r"\s+", " ", s)
    s = s.replace(". ", " ").replace(".", " ")
    s = s.strip()
    return s.lower()


def normalize_to_ascii_lower(s: str) -> str:
    s = _ascii_fold(s)
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    s = re.sub(r"\s+", " ", s)
    s = s.strip()
    return s.lower()


def extract_surname(name: str) -> str | None:
    normalized = normalize_to_ascii_lower(name)
    tokens = [t for t in normalized.split() if t]
    if not tokens:
        return None
    stopwords = {"da", "de", "do", "das", "dos", "e"}
    filtered = [t for t in tokens if t not in stopwords]
    if not filtered:
        return None
    return filtered[-1]


def are_names_effectively_identical(str1: str, str2: str) -> bool:
    norm1 = normalize_name_for_comparison(str1)
    norm2 = normalize_name_for_comparison(str2)
    ws1 = norm1.replace(" ", "")
    ws2 = norm2.replace(" ", "")
    return ws1 == ws2


def _levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        return _levenshtein(b, a)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, c1 in enumerate(a):
        cur = [i + 1]
        for j, c2 in enumerate(b):
            ins = prev[j + 1] + 1
            delete = cur[j] + 1
            sub = prev[j] + (c1 != c2)
            cur.append(min(ins, delete, sub))
        prev = cur
    return prev[-1]


def calculate_similarity(str1: str, str2: str) -> float:
    if are_names_effectively_identical(str1, str2):
        return 100.0
    s1 = normalize_name_for_comparison(str1)
    s2 = normalize_name_for_comparison(str2)
    if s1 == s2:
        return 100.0

    surname1 = extract_surname(str1)
    surname2 = extract_surname(str2)
    if surname1 is not None and surname2 is not None:
        if surname1 != surname2:
            d = _levenshtein(surname1, surname2)
            mx = max(len(surname1), len(surname2))
            if mx == 0:
                return 0.0
            surname_similarity = (1 - (d / mx)) * 100
            if surname_similarity < 75:
                return 0.0

    first_char1 = s1[0] if s1 else ""
    first_char2 = s2[0] if s2 else ""
    lev = _levenshtein(s1, s2)
    max_length = max(len(s1), len(s2))
    if max_length == 0:
        return 100.0
    similarity = (1 - (lev / max_length)) * 100
    if first_char1 != first_char2:
        similarity *= 0.7
    return similarity


def merge_participants(
    conn: sqlite3.Connection,
    *,
    exact_only: bool,
    similarity: float = 80.0,
    max_group_size: int = 0,
    log: LogFn,
) -> None:
    log("Iniciando processo de mesclagem de participantes...")
    decisions = _load_merge_decisions()
    participants = list(conn.execute("SELECT * FROM challonge_participants"))
    merged = 0
    similar_groups: list[list[sqlite3.Row]] = []
    processed: set[int] = set()

    if exact_only:
        log("Buscando grupos com nomes efetivamente idênticos...")
        for p1 in participants:
            if p1["id"] in processed:
                continue
            exact_group = [p1]
            processed.add(p1["id"])
            for p2 in participants:
                if p2["id"] in processed or p1["id"] == p2["id"]:
                    continue
                if max_group_size > 0 and len(exact_group) >= max_group_size:
                    break
                if are_names_effectively_identical(p1["name"], p2["name"]):
                    exact_group.append(p2)
                    processed.add(p2["id"])
            similar_groups.append(exact_group)
        dupes = [g for g in similar_groups if len(g) > 1]
        log(f"Encontrados {len(dupes)} grupos com duplicatas efetivamente idênticas.")
    else:
        log(f"Buscando grupos com similaridade >= {similarity}%...")
        for p1 in participants:
            if p1["id"] in processed:
                continue
            current_group = [p1]
            processed.add(p1["id"])
            for p2 in participants:
                if p2["id"] in processed or p1["id"] == p2["id"]:
                    continue
                if max_group_size > 0 and len(current_group) >= max_group_size:
                    break
                if calculate_similarity(p1["name"], p2["name"]) >= similarity:
                    current_group.append(p2)
                    processed.add(p2["id"])
            similar_groups.append(current_group)
        dupes = [g for g in similar_groups if len(g) > 1]
        log(f"Encontrados {len(dupes)} grupos com similaridade >= {similarity}%.")

    for group in similar_groups:
        if len(group) <= 1:
            continue
        log(f"\nEncontrado grupo de participantes similares ({len(group)} participantes):")
        for p in group:
            log(f"- {p['name']} (ID: {p['id']})")

        participant_ids = [int(p["id"]) for p in group]
        key = "-".join(str(x) for x in sorted(participant_ids))
        should_merge = decisions.get(key)

        all_identical = all(
            are_names_effectively_identical(group[0]["name"], p["name"]) for p in group
        )

        if all_identical:
            should_merge = True
            log("Nomes efetivamente idênticos - mesclagem automática.")
        elif should_merge is None:
            log(
                "Grupo sem decisão persistida em merge_decisions.json — "
                "pulando mesclagem (defina a chave no JSON ou use apenas exact-only)."
            )
            continue
        else:
            log(
                "Usando decisão persistida: "
                + ("mesclar" if should_merge else "não mesclar")
            )

        if not should_merge:
            continue

        main = group[0]
        main_id = int(main["id"])
        for idx, participant in enumerate(group):
            if idx == 0:
                continue
            pid = int(participant["id"])
            conn.execute(
                "UPDATE challonge_matches SET player1_id = ? WHERE player1_id = ?",
                (main_id, pid),
            )
            conn.execute(
                "UPDATE challonge_matches SET player2_id = ? WHERE player2_id = ?",
                (main_id, pid),
            )
            conn.execute(
                "UPDATE challonge_matches SET winner_id = ? WHERE winner_id = ?",
                (main_id, pid),
            )
            conn.execute(
                "UPDATE challonge_matches SET loser_id = ? WHERE loser_id = ?",
                (main_id, pid),
            )
            conn.execute("DELETE FROM challonge_participants WHERE id = ?", (pid,))
            merged += 1
        log(f"Participantes mesclados com sucesso em: {main['name']}")

    conn.commit()
    log(f"\nProcesso concluído! {merged} participantes foram mesclados.")
