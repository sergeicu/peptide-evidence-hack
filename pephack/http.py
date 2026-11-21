"""One shared HTTP layer: polite rate limiting, retries, on-disk cache,
and an offline mode that replays fixtures so tests need no network.

Why a cache: these are free public APIs and forty teams will hammer them from
one room's IP. Cache everything. A cached hit costs nothing and keeps the APIs
answering all day.

Set PEPHACK_OFFLINE=1 to serve every request from data/fixtures/ instead.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = Path(os.environ.get("PEPHACK_CACHE", REPO_ROOT / "cache"))
FIXTURE_DIR = REPO_ROOT / "data" / "fixtures"

# Documented courtesy limits. Keep them.
#   NCBI E-utilities: 3 req/s without an API key, 10 with one.
#   openFDA: 240 req/min and 1000 req/day without a key.
#   Europe PMC and ClinicalTrials.gov: no published hard limit, be decent.
DEFAULT_MIN_INTERVAL = 0.34

_last_call: dict[str, float] = {}


class ApiError(RuntimeError):
    pass


def offline() -> bool:
    return os.environ.get("PEPHACK_OFFLINE", "") not in ("", "0", "false", "False")


def _cache_key(url: str, params: dict[str, Any] | None) -> str:
    blob = url + "?" + json.dumps(params or {}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:24]


def _throttle(host: str, min_interval: float) -> None:
    now = time.monotonic()
    prev = _last_call.get(host)
    if prev is not None:
        wait = min_interval - (now - prev)
        if wait > 0:
            time.sleep(wait)
    _last_call[host] = time.monotonic()


def get(
    url: str,
    params: dict[str, Any] | None = None,
    *,
    fixture: str | None = None,
    parse: str = "json",
    min_interval: float = DEFAULT_MIN_INTERVAL,
    retries: int = 3,
    timeout: int = 30,
    use_cache: bool = True,
) -> Any:
    """GET a URL and return parsed JSON (parse="json") or text (parse="text").

    fixture: filename under data/fixtures/ used when PEPHACK_OFFLINE=1.
    """
    if offline():
        if not fixture:
            raise ApiError(f"offline mode and no fixture registered for {url}")
        path = FIXTURE_DIR / fixture
        if not path.exists():
            raise ApiError(f"offline fixture missing: {path}")
        text = path.read_text()
        return json.loads(text) if parse == "json" else text

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_DIR / f"{_cache_key(url, params)}.{'json' if parse == 'json' else 'txt'}"
    if use_cache and cache_path.exists():
        text = cache_path.read_text()
        return json.loads(text) if parse == "json" else text

    host = requests.utils.urlparse(url).netloc
    last_err: Exception | None = None
    for attempt in range(retries):
        _throttle(host, min_interval)
        try:
            resp = requests.get(
                url,
                params=params,
                timeout=timeout,
                headers={
                    "User-Agent": "pephack/0.1 (SF x MIT hack day; +https://github.com/sergeicu/peptide-evidence-hack)",
                    "Accept": "application/json" if parse == "json" else "*/*",
                },
            )
        except requests.RequestException as exc:
            last_err = exc
            time.sleep(1.5 * (attempt + 1))
            continue

        # 429 and 5xx are worth retrying; 4xx is a bug in your request.
        if resp.status_code == 429 or 500 <= resp.status_code < 600:
            last_err = ApiError(f"{resp.status_code} from {host}")
            time.sleep(2.0 * (attempt + 1))
            continue
        if not resp.ok:
            raise ApiError(f"{resp.status_code} from {url}: {resp.text[:300]}")

        text = resp.text
        if use_cache:
            cache_path.write_text(text)
        return resp.json() if parse == "json" else text

    raise ApiError(f"giving up on {url} after {retries} attempts: {last_err}")
