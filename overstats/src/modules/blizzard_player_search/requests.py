from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Optional, Sequence

try:
    from overstats.src.client.apiclient import (
        DEFAULT_BLIZZARD_LOCALE,
        DashenAPIClient,
        dashen_api_client,
    )
except ModuleNotFoundError:
    from src.client.apiclient import DEFAULT_BLIZZARD_LOCALE, DashenAPIClient, dashen_api_client


_LOCALE_PATTERN = re.compile(r"^[a-z]{2}-[a-z]{2}$")


def normalize_player_search_name(name: str) -> str:
    return str(name or "").replace("#", "-").strip()


def normalize_blizzard_locale(locale: str) -> str:
    normalized = str(locale or "").strip().lower().replace("_", "-")
    return normalized or DEFAULT_BLIZZARD_LOCALE


def validate_blizzard_locale(locale: str) -> str:
    normalized = normalize_blizzard_locale(locale)
    if not _LOCALE_PATTERN.fullmatch(normalized):
        raise ValueError("locale must use Blizzard format like zh-tw or en-us.")
    return normalized


def normalize_blizzard_id(blizzard_id: str) -> str:
    return str(blizzard_id or "").strip().replace("|", "%7C")


def match_player_by_blizzard_id(
    search_results: Sequence[dict[str, Any]],
    blizzard_id: str,
) -> Optional[dict[str, Any]]:
    normalized_blizzard_id = normalize_blizzard_id(blizzard_id)
    if not normalized_blizzard_id:
        return None
    for player in search_results:
        if str(player.get("url") or "").strip() == normalized_blizzard_id:
            return player
    return None


def extract_player_title(title: Any, *, locale: str) -> Optional[str]:
    if not title:
        return None
    if isinstance(title, str):
        normalized = title.strip()
        if not normalized or normalized.lower() == "no title":
            return None
        return normalized
    if isinstance(title, dict):
        locale_key = locale.replace("-", "_")
        preferred_keys = (
            locale_key,
            locale_key.lower(),
            locale_key.upper(),
            "en_US",
            "en_us",
        )
        for key in preferred_keys:
            value = title.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for value in title.values():
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _clean_optional_string(value: Any) -> Optional[str]:
    normalized = str(value or "").strip()
    return normalized or None


@dataclass(frozen=True)
class BlizzardPlayerSearchEntry:
    player_id: str
    name: str
    avatar: Optional[str]
    namecard: Optional[str]
    title: Optional[str]
    career_url: str
    blizzard_id: str
    last_updated_at: int
    is_public: bool
    portrait: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "name": self.name,
            "avatar": self.avatar,
            "namecard": self.namecard,
            "title": self.title,
            "career_url": self.career_url,
            "blizzard_id": self.blizzard_id,
            "last_updated_at": self.last_updated_at,
            "is_public": self.is_public,
            "portrait": self.portrait,
        }


def build_search_entry(
    player: dict[str, Any],
    *,
    query_name: str,
    locale: str,
    result_count: int,
) -> BlizzardPlayerSearchEntry:
    blizzard_id = str(player["url"]).strip()
    portrait = _clean_optional_string(player.get("portrait"))
    avatar = None if portrait else _clean_optional_string(player.get("avatar"))
    namecard = None if portrait else _clean_optional_string(player.get("namecard"))
    title = None if portrait else extract_player_title(player.get("title"), locale=locale)
    player_id = query_name if result_count == 1 and "-" in query_name else blizzard_id
    return BlizzardPlayerSearchEntry(
        player_id=player_id,
        name=str(player["name"]).strip(),
        avatar=avatar,
        namecard=namecard,
        title=title,
        career_url=f"https://overwatch.blizzard.com/{locale}/career/{blizzard_id}/",
        blizzard_id=blizzard_id,
        last_updated_at=int(player.get("lastUpdated") or 0),
        is_public=bool(player.get("isPublic")),
        portrait=portrait,
    )


class BlizzardPlayerSearchRequests:
    def __init__(self, api_client: Optional[DashenAPIClient] = None) -> None:
        self.api_client = api_client or dashen_api_client

    async def search(self, name: str, *, locale: str = DEFAULT_BLIZZARD_LOCALE) -> Any:
        return await self.api_client.search_blizzard_accounts(
            normalize_player_search_name(name),
            locale=validate_blizzard_locale(locale),
        )
