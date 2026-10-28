from __future__ import annotations

import json
import os
from dataclasses import dataclass
from threading import Lock
from typing import Any, Dict, List, Optional, Sequence

import httpx

try:
    from overstats.src.client.apiclient import (
        CLIENT_CONFIG,
        DashenAPIClient,
        DashenCredential,
        dashen_api_client,
    )
    from overstats.src.db.player_identity import search_identity_by_battletag
    from overstats.src.db.search_cache import (
        alookup_search_result,
        arecord_search_result,
        normalize_battletag,
    )
except ModuleNotFoundError:
    from src.client.apiclient import (
        CLIENT_CONFIG,
        DashenAPIClient,
        DashenCredential,
        dashen_api_client,
    )
    from src.db.player_identity import search_identity_by_battletag
    from src.db.search_cache import (
        alookup_search_result,
        arecord_search_result,
        normalize_battletag,
    )


# Search-only fallback credentials; deliberately independent of DASHEN_ACCOUNTS.
# They are borrowed from the upstream Overstats project and only used while the
# search endpoint is temporarily closed. Override them with the environment
# variable OVERSTATS_SEARCH_FALLBACK_ACCOUNTS='[{"name":..,"role_id":..,"token":..}]'.
_DEFAULT_FALLBACK_ACCOUNTS = (
    ("account-217943997", 217943997, "805ef05683a7bd5d4e86cf5370c37756"),
    ("account-207219421", 207219421, "0c0f007c41fa51a4cab819b06f62a3fc"),
)
_FALLBACK_ENV = "OVERSTATS_SEARCH_FALLBACK_ACCOUNTS"
_fallback_start = 0
_fallback_lock = Lock()


def _fallback_accounts() -> Sequence[tuple[str, int, str]]:
    raw = os.environ.get(_FALLBACK_ENV, "").strip()
    if not raw:
        return _DEFAULT_FALLBACK_ACCOUNTS
    try:
        parsed = json.loads(raw)
    except ValueError:
        print("[overstats] invalid OVERSTATS_SEARCH_FALLBACK_ACCOUNTS, value is not JSON")
        return _DEFAULT_FALLBACK_ACCOUNTS
    accounts: List[tuple[str, int, str]] = []
    for item in parsed if isinstance(parsed, list) else ():
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        token = str(item.get("token") or "").strip()
        try:
            role_id = int(item.get("role_id"))
        except (TypeError, ValueError):
            continue
        if name and token:
            accounts.append((name, role_id, token))
    return tuple(accounts) or _DEFAULT_FALLBACK_ACCOUNTS


def _search_unavailable(payload: Any) -> bool:
    """Return True when the payload is not a usable search result."""
    if not isinstance(payload, dict):
        return True
    if payload.get("success") is False or payload.get("ok") is False:
        return True
    code = payload.get("code")
    if code is not None and str(code) != "0":
        return True
    # A successful status without a usable token still becomes bnet_not_found
    # downstream, so try the fallback accounts before returning that result.
    data = payload.get("data")
    return not isinstance(data, dict) or not str(data.get("customerToken") or "").strip()


@dataclass(frozen=True)
class BnetSearchResult:
    query: str
    payload: Dict[str, Any]

    @property
    def data(self) -> Dict[str, Any]:
        data = self.payload.get("data")
        if isinstance(data, dict):
            return data

        # Legacy/local cache payloads may arrive wrapped in one of these keys.
        for wrapper_key in ("profile_card", "profileCard", "search_result", "searchResult"):
            wrapper = self.payload.get(wrapper_key)
            if not isinstance(wrapper, dict):
                continue
            wrapped_data = wrapper.get("data")
            if isinstance(wrapped_data, dict):
                return wrapped_data
        return {}

    @property
    def customer_token(self) -> str:
        return str(self.data.get("customerToken") or "").strip()

    @property
    def bnet_id(self) -> str:
        return str(self.data.get("bnetId") or "").strip()

    @property
    def full_id(self) -> str:
        return str(self.data.get("name") or self.query).strip()

    @property
    def icon_url(self) -> str:
        return str(self.data.get("icon") or "").strip()

    @property
    def from_cache(self) -> bool:
        return str(self.payload.get("source") or "") in {
            "local_search_cache",
            "local_identity_cache",
        }


def normalize_bnet_id(bnet_id: str) -> str:
    return str(bnet_id or "").replace("\uff03", "#").strip()


def _build_fallback_credential(name: str, role_id: int, token: str) -> DashenCredential:
    defaults = CLIENT_CONFIG.accounts[0]
    return DashenCredential(
        name=name,
        role_id=role_id,
        token=token,
        dts=defaults.dts,
        server=defaults.server,
    )


class BnetSearchRequests:
    def __init__(self, api_client: Optional[DashenAPIClient] = None) -> None:
        self.api_client = api_client or dashen_api_client

    async def search(self, bnet_id: str) -> BnetSearchResult:
        query = normalize_bnet_id(bnet_id)
        payload, error = await self._search_via_accounts(query)
        if not _search_unavailable(payload):
            await self._record_success(query, payload)
            return BnetSearchResult(query=query, payload=payload)

        cached_payload = await self._search_local_cache(query)
        if cached_payload:
            return BnetSearchResult(query=query, payload=cached_payload)

        if error is not None:
            raise error
        return BnetSearchResult(query=query, payload=payload or {})

    async def _search_via_accounts(
        self, query: str
    ) -> tuple[Optional[Dict[str, Any]], Optional[Exception]]:
        """Search with the configured accounts, then the whitelist accounts."""
        payload: Optional[Dict[str, Any]] = None
        last_error: Optional[Exception] = None
        try:
            payload = await self.api_client.search_bnet_account(query)
            if not _search_unavailable(payload):
                return payload, None
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            last_error = exc

        accounts = _fallback_accounts()
        global _fallback_start
        with _fallback_lock:
            start = _fallback_start % len(accounts)
            _fallback_start = (start + 1) % len(accounts)

        for offset in range(len(accounts)):
            name, role_id, token = accounts[(start + offset) % len(accounts)]
            try:
                credential = _build_fallback_credential(name, role_id, token)
            except Exception as exc:  # pragma: no cover - defensive
                last_error = exc
                continue
            try:
                payload = await self.api_client.search_bnet_account(query, credential=credential)
                if not _search_unavailable(payload):
                    return payload, None
                last_error = None
            except (httpx.HTTPError, ValueError, TypeError) as exc:
                last_error = exc
        return payload, last_error

    async def _record_success(self, query: str, payload: Dict[str, Any]) -> None:
        """Cache the successful search so it survives a closed endpoint."""
        result = BnetSearchResult(query=query, payload=payload)
        token = result.customer_token
        battletag = normalize_battletag(result.data.get("name") or query)
        if not token or not battletag:
            return
        try:
            await arecord_search_result(battletag, token, result.bnet_id)
        except Exception as exc:  # pragma: no cover - cache must never break search
            print(f"[overstats] failed to cache bnet search result: {exc}")

    async def _search_local_cache(self, query: str) -> Dict[str, Any]:
        cached = await alookup_search_result(query)
        if cached:
            return {
                "code": 0,
                "data": {
                    "customerToken": cached["customer_token"],
                    "bnetId": cached.get("bnet_id") or "",
                    "name": cached.get("battletag") or query,
                },
                "source": "local_search_cache",
            }
        return await self._search_local_identity_cache(query)

    async def _search_local_identity_cache(self, query: str) -> Dict[str, Any]:
        rows = await search_identity_by_battletag(query, limit=1, exact_only=True)
        if not rows:
            return {}
        row = rows[0]
        token = str(row.get("bnetid") or "").strip()
        battletag = str(row.get("battletag") or query).strip()
        if not token or not battletag:
            return {}
        return {
            "code": 0,
            "data": {
                "customerToken": token,
                "bnetId": token,
                "name": battletag,
            },
            "source": "local_identity_cache",
        }
