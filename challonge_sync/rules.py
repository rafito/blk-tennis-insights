"""Regras portadas do ChallongeSyncCommand / UpdateTournamentCategories (PHP)."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any


def extract_year_from_name(name: str) -> int | None:
    m = re.search(r"\b(20\d{2})\b", name)
    if m:
        return int(m.group(1))
    m = re.search(r"\b(\d{2})\b", name)
    if m:
        two = int(m.group(1))
        if two >= 20:
            return 2000 + two
    return None


def extract_year_from_date_value(val: Any) -> int | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.year
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00").split("+")[0]).year
        except ValueError:
            try:
                return datetime.strptime(val[:19], "%Y-%m-%d %H:%M:%S").year
            except ValueError:
                return None
    return None


def adjust_date_year(date_value: str | None, name: str) -> str | None:
    if not date_value:
        return None
    try:
        dt = datetime.fromisoformat(date_value.replace("Z", "+00:00").split("+")[0])
    except ValueError:
        try:
            dt = datetime.strptime(date_value[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return date_value
    yname = extract_year_from_name(name)
    if yname and dt.year != yname:
        dt = dt.replace(year=yname)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def resolve_tournament_year(started_at: Any, completed_at: Any, name: str) -> int | None:
    return (
        extract_year_from_date_value(started_at)
        or extract_year_from_date_value(completed_at)
        or extract_year_from_name(name)
    )


def determine_category_sync(name: str) -> str:
    """Categoria durante sync de torneios (ChallongeSyncCommand::determineCategory)."""
    n = name.upper()
    m = re.search(r"(\d)\s*A\s*(?:CLASSE)?", n)
    if m:
        return f"{int(m.group(1))}a CLASSE"
    m = re.search(r"FINALS.*?([ABC])\b", n)
    if m:
        letter = m.group(1)
        return {"A": "3a CLASSE", "B": "4a CLASSE", "C": "5a CLASSE"}[letter]
    m = re.search(r"(\d)/A", n)
    if m:
        return f"{int(m.group(1))}a CLASSE"
    m = re.search(r"(\d)CAT([ABC])", n)
    if m:
        letter = m.group(2)
        return {"A": "3a CLASSE", "B": "4a CLASSE", "C": "5a CLASSE"}[letter]
    m = re.search(r"\d+/(\d)A", n)
    if m:
        return f"{int(m.group(1))}a CLASSE"
    return "3a CLASSE"


def determine_category_refresh(name: str) -> str:
    """Categoria no passo tournaments:update-categories (UpdateTournamentCategories)."""
    n = name.upper()
    m = re.search(r"\dCAT([ABC])", n)
    if m:
        letter = m.group(1)
        return {"A": "3a CLASSE", "B": "4a CLASSE", "C": "5a CLASSE"}[letter]
    m = re.search(r"(\d)A\s*(?:CLASSE)?", n)
    if m:
        num = int(m.group(1))
        if num in (3, 4, 5):
            return {3: "3a CLASSE", 4: "4a CLASSE", 5: "5a CLASSE"}[num]
    m = re.search(r"FINALS.*?([ABC])", n)
    if m:
        letter = m.group(1)
        return {"A": "3a CLASSE", "B": "4a CLASSE", "C": "5a CLASSE"}[letter]
    m = re.search(r"DOBLES.*?(\d)A", n)
    if m:
        num = int(m.group(1))
        if num in (3, 4, 5):
            return {3: "3a CLASSE", 4: "4a CLASSE", 5: "5a CLASSE"}[num]
    return "3a CLASSE"


def should_skip_tournament_name(name: str) -> bool:
    n = name.lower()
    return any(
        x in n
        for x in ("duplas", "dobles", "doubles", "teste", "closed")
    )


def should_skip_participant_name(name: str) -> bool:
    return "/" in name
