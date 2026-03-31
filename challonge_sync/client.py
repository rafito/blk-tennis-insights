"""Cliente HTTP para API Challonge v1."""
from __future__ import annotations

import time
from typing import Any

import httpx

BASE_URL = "https://api.challonge.com/v1"


def _get_with_retries(
    client: httpx.Client,
    url: str,
    *,
    attempts: int = 3,
    delay_seconds: float = 2.0,
    log,
) -> httpx.Response:
    last: httpx.Response | None = None
    for attempt in range(1, attempts + 1):
        last = client.get(url)
        if last.is_success:
            return last
        if attempt < attempts:
            log(
                f"Aviso: falha HTTP {last.status_code} em {url} "
                f"(tentativa {attempt}/{attempts}); aguardando {delay_seconds}s..."
            )
            time.sleep(delay_seconds)
    assert last is not None
    return last


def fetch_tournaments_json(client: httpx.Client, log) -> list[dict[str, Any]]:
    r = _get_with_retries(client, f"{BASE_URL}/tournaments.json", log=log)
    r.raise_for_status()
    return r.json()


def fetch_participants_json(
    client: httpx.Client, challonge_tournament_id: int, log
) -> list[dict[str, Any]]:
    url = f"{BASE_URL}/tournaments/{challonge_tournament_id}/participants.json"
    r = _get_with_retries(client, url, log=log)
    r.raise_for_status()
    return r.json()


def fetch_matches_json(
    client: httpx.Client, challonge_tournament_id: int, log
) -> list[dict[str, Any]]:
    url = f"{BASE_URL}/tournaments/{challonge_tournament_id}/matches.json"
    r = _get_with_retries(client, url, log=log)
    r.raise_for_status()
    return r.json()


def make_client(username: str, api_key: str) -> httpx.Client:
    return httpx.Client(auth=(username, api_key), timeout=120.0)
