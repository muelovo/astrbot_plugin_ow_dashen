from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

try:
    from overstats.src.client.apiclient import DashenAPIClient, dashen_api_client
    from overstats.src.db.player_identity import search_identity_by_battletag
except ModuleNotFoundError:
    from src.client.apiclient import DashenAPIClient, dashen_api_client
    from src.db.player_identity import search_identity_by_battletag


@dataclass(frozen=True)
class BnetSearchResult:
    query: str
    payload: Dict[str, Any]

    @property
    def data(self) -> Dict[str, Any]:
        data = self.payload.get("data")
        if isinstance(data, dict):
            return data

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


def normalize_bnet_id(bnet_id: str) -> str:
    return str(bnet_id or "").replace("\uff03", "#").strip()


class BnetSearchRequests:
    def __init__(self, api_client: Optional[DashenAPIClient] = None) -> None:
        self.api_client = api_client or dashen_api_client

    async def search(self, bnet_id: str) -> BnetSearchResult:
        query = normalize_bnet_id(bnet_id)
        try:
            payload = await self.api_client.search_bnet_account(query)
        except Exception:
            payload = await self._search_local_identity_cache(query)
            if not payload:
                raise
        if not BnetSearchResult(query=query, payload=payload).customer_token:
            cached_payload = await self._search_local_identity_cache(query)
            if cached_payload:
                payload = cached_payload
        return BnetSearchResult(query=query, payload=payload)

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
