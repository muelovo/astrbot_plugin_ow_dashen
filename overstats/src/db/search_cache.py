"""Local cache of successful bnet search results.

When the Dashen search endpoint is temporarily closed, the plugin can still
resolve a BattleTag that it has searched successfully before.  The cache is a
small standalone SQLite file so it never mixes with the match statistics
database.
"""

from __future__ import annotations

import asyncio
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from overstats.config import is_database_write_enabled
    from overstats.paths import get_overstats_data_dir
except ModuleNotFoundError:  # pragma: no cover - plugin import layout
    from config import is_database_write_enabled
    from paths import get_overstats_data_dir


SEARCH_CACHE_TABLE = "bnet_search_cache"
DEFAULT_MAX_AGE_SECONDS = 14 * 24 * 60 * 60

_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS {SEARCH_CACHE_TABLE} (
    battletag TEXT PRIMARY KEY COLLATE NOCASE,
    customer_token TEXT NOT NULL,
    bnet_id TEXT NOT NULL DEFAULT '',
    updated_at INTEGER NOT NULL
)
"""

_initialized_paths: set[str] = set()
_init_lock = threading.Lock()


def normalize_battletag(text: Any) -> str:
    return str(text or "").replace("＃", "#").strip()


def default_cache_path() -> Path:
    return get_overstats_data_dir() / "db" / "bnet_search_cache.sqlite3"


def _resolve_path(db_path: Optional[Any]) -> Path:
    if db_path:
        return Path(db_path)
    return default_cache_path()


def _ensure_schema(path: Path) -> None:
    key = str(path)
    if key in _initialized_paths:
        return
    with _init_lock:
        if key in _initialized_paths:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(path), timeout=5)
        try:
            connection.execute(_SCHEMA)
            connection.commit()
        finally:
            connection.close()
        _initialized_paths.add(key)


def _connect(path: Path) -> Optional[sqlite3.Connection]:
    try:
        _ensure_schema(path)
        return sqlite3.connect(str(path), timeout=5)
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[overstats] failed to open bnet search cache {path}: {exc}")
        return None


def record_search_result(
    battletag: Any,
    customer_token: Any,
    bnet_id: Any = "",
    *,
    db_path: Optional[Any] = None,
    now: Optional[float] = None,
) -> bool:
    """Store battletag -> customerToken so maintenance mode can reuse it."""
    if not is_database_write_enabled():
        return False
    tag = normalize_battletag(battletag)
    token = str(customer_token or "").strip()
    if not tag or not token:
        return False
    try:
        timestamp = int(now if now is not None else time.time())
    except (TypeError, ValueError):
        timestamp = int(time.time())

    connection = _connect(_resolve_path(db_path))
    if connection is None:
        return False
    try:
        connection.execute(
            f"""
            INSERT INTO {SEARCH_CACHE_TABLE} (battletag, customer_token, bnet_id, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(battletag) DO UPDATE SET
                customer_token = excluded.customer_token,
                bnet_id = excluded.bnet_id,
                updated_at = excluded.updated_at
            """,
            (tag, token, str(bnet_id or "").strip(), timestamp),
        )
        connection.commit()
        return True
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[overstats] failed to write bnet search cache: {exc}")
        return False
    finally:
        connection.close()


def lookup_search_result(
    battletag: Any,
    *,
    db_path: Optional[Any] = None,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
) -> Optional[Dict[str, Any]]:
    tag = normalize_battletag(battletag)
    if not tag:
        return None
    connection = _connect(_resolve_path(db_path))
    if connection is None:
        return None
    try:
        row = connection.execute(
            f"""
            SELECT battletag, customer_token, bnet_id, updated_at
            FROM {SEARCH_CACHE_TABLE}
            WHERE battletag = ?
            """,
            (tag,),
        ).fetchone()
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[overstats] failed to read bnet search cache: {exc}")
        return None
    finally:
        connection.close()
    if not row:
        return None
    result = {
        "battletag": str(row[0] or ""),
        "customer_token": str(row[1] or ""),
        "bnet_id": str(row[2] or ""),
        "updated_at": int(row[3] or 0),
    }
    if not result["customer_token"]:
        return None
    if max_age_seconds and max_age_seconds > 0:
        age = int(time.time()) - result["updated_at"]
        if age > max_age_seconds:
            return None
    return result


async def arecord_search_result(
    battletag: Any,
    customer_token: Any,
    bnet_id: Any = "",
    *,
    db_path: Optional[Any] = None,
) -> bool:
    return await asyncio.to_thread(record_search_result, battletag, customer_token, bnet_id, db_path=db_path)


async def alookup_search_result(
    battletag: Any,
    *,
    db_path: Optional[Any] = None,
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
) -> Optional[Dict[str, Any]]:
    return await asyncio.to_thread(
        lookup_search_result,
        battletag,
        db_path=db_path,
        max_age_seconds=max_age_seconds,
    )


__all__ = [
    "DEFAULT_MAX_AGE_SECONDS",
    "SEARCH_CACHE_TABLE",
    "alookup_search_result",
    "arecord_search_result",
    "default_cache_path",
    "lookup_search_result",
    "normalize_battletag",
    "record_search_result",
]
