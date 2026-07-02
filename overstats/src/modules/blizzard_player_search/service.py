from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

try:
    from overstats.src.client.apiclient import DashenAPIClient
    from overstats.src.modules.errors import ModuleError
except ModuleNotFoundError:
    from src.client.apiclient import DashenAPIClient
    from src.modules.errors import ModuleError

from .requests import (
    DEFAULT_BLIZZARD_LOCALE,
    BlizzardPlayerSearchEntry,
    BlizzardPlayerSearchRequests,
    build_search_entry,
    match_player_by_blizzard_id,
    normalize_player_search_name,
    validate_blizzard_locale,
)


@dataclass(frozen=True)
class BlizzardPlayerSearchQuery:
    name: str
    locale: str = DEFAULT_BLIZZARD_LOCALE
    order_by: str = "name:asc"
    offset: int = 0
    limit: int = 20
    blizzard_id: str = ""


@dataclass(frozen=True)
class BlizzardPlayerSearchOutput:
    query: BlizzardPlayerSearchQuery
    total: int
    results: tuple[BlizzardPlayerSearchEntry, ...]
    resolved: Optional[BlizzardPlayerSearchEntry] = None


class BlizzardPlayerSearchModule:
    def __init__(self, api_client: Optional[DashenAPIClient] = None) -> None:
        self.requests = BlizzardPlayerSearchRequests(api_client)

    async def search(self, query: BlizzardPlayerSearchQuery) -> BlizzardPlayerSearchOutput:
        normalized_name = normalize_player_search_name(query.name)
        if not normalized_name:
            raise ModuleError(
                error="missing_name",
                message="name is required for Blizzard player search.",
                status_code=400,
                hint='Example: {"name":"TeKrop-2217"}',
            )

        locale = self._validate_locale(query.locale)
        order_by = self._validate_order_by(query.order_by)
        offset = self._validate_offset(query.offset)
        limit = self._validate_limit(query.limit)
        raw_payload = await self.requests.search(normalized_name, locale=locale)
        if not isinstance(raw_payload, list):
            raise ModuleError(
                error="blizzard_player_invalid_payload",
                message="Unexpected Blizzard search payload: expected a JSON array.",
                status_code=502,
                details={"payload_type": type(raw_payload).__name__},
            )

        filtered_players = self._filter_players(raw_payload, normalized_name)
        entries = tuple(
            build_search_entry(
                player,
                query_name=normalized_name,
                locale=locale,
                result_count=len(filtered_players),
            )
            for player in filtered_players
        )
        ordered_entries = self._apply_ordering(entries, order_by)
        resolved = None
        normalized_blizzard_id = str(query.blizzard_id or "").strip()
        if normalized_blizzard_id:
            matched_player = match_player_by_blizzard_id(filtered_players, normalized_blizzard_id)
            if matched_player is not None:
                resolved = build_search_entry(
                    matched_player,
                    query_name=normalized_name,
                    locale=locale,
                    result_count=len(filtered_players),
                )

        paginated_entries = ordered_entries[offset : offset + limit]
        normalized_query = BlizzardPlayerSearchQuery(
            name=normalized_name,
            locale=locale,
            order_by=order_by,
            offset=offset,
            limit=limit,
            blizzard_id=normalized_blizzard_id,
        )
        return BlizzardPlayerSearchOutput(
            query=normalized_query,
            total=len(entries),
            results=paginated_entries,
            resolved=resolved,
        )

    def _validate_locale(self, locale: str) -> str:
        try:
            return validate_blizzard_locale(locale)
        except ValueError as exc:
            raise ModuleError(
                error="invalid_locale",
                message=str(exc),
                status_code=400,
                details={"locale": locale},
            ) from exc

    def _validate_order_by(self, order_by: str) -> str:
        normalized = str(order_by or "name:asc").strip().lower() or "name:asc"
        try:
            field, direction = normalized.split(":", 1)
        except ValueError as exc:
            raise ModuleError(
                error="invalid_order_by",
                message="order_by must use the format field:asc|desc.",
                status_code=400,
                details={"order_by": order_by},
            ) from exc
        if field not in {"player_id", "name", "last_updated_at", "blizzard_id"} or direction not in {"asc", "desc"}:
            raise ModuleError(
                error="invalid_order_by",
                message="order_by only supports player_id, name, last_updated_at, or blizzard_id with asc/desc.",
                status_code=400,
                details={"order_by": normalized},
            )
        return normalized

    def _validate_offset(self, offset: object) -> int:
        try:
            normalized = int(offset or 0)
        except (TypeError, ValueError) as exc:
            raise ModuleError(
                error="invalid_offset",
                message="offset must be an integer when provided.",
                status_code=400,
                details={"offset": offset},
            ) from exc
        if normalized < 0:
            raise ModuleError(
                error="invalid_offset",
                message="offset must be greater than or equal to 0.",
                status_code=400,
                details={"offset": normalized},
            )
        return normalized

    def _validate_limit(self, limit: object) -> int:
        try:
            normalized = int(limit or 20)
        except (TypeError, ValueError) as exc:
            raise ModuleError(
                error="invalid_limit",
                message="limit must be an integer when provided.",
                status_code=400,
                details={"limit": limit},
            ) from exc
        if normalized <= 0:
            raise ModuleError(
                error="invalid_limit",
                message="limit must be greater than 0.",
                status_code=400,
                details={"limit": normalized},
            )
        return min(normalized, 50)

    def _filter_players(
        self,
        payload: list[object],
        query_name: str,
    ) -> tuple[dict[str, object], ...]:
        search_name = query_name.split("-", 1)[0]
        filtered = []
        try:
            for item in payload:
                if not isinstance(item, dict):
                    raise TypeError(f"item is {type(item).__name__}")
                if item["name"] == search_name and item["isPublic"] is True:
                    filtered.append(item)
        except (KeyError, TypeError) as exc:
            raise ModuleError(
                error="blizzard_player_invalid_payload",
                message=f"Unexpected Blizzard search payload structure: {exc}",
                status_code=502,
            ) from exc
        return tuple(filtered)

    def _apply_ordering(
        self,
        entries: tuple[BlizzardPlayerSearchEntry, ...],
        order_by: str,
    ) -> tuple[BlizzardPlayerSearchEntry, ...]:
        field, direction = order_by.split(":", 1)
        return tuple(
            sorted(
                entries,
                key=lambda item: getattr(item, field),
                reverse=direction == "desc",
            )
        )


blizzard_player_search_module = BlizzardPlayerSearchModule()
