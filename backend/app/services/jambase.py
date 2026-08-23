from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

import httpx

from app.config import Settings
from app.models import EventSearchResponse, EventSummary, PaginationSummary, SearchLocation


class JamBaseError(Exception):
    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class JamBaseConfigurationError(JamBaseError):
    def __init__(self) -> None:
        super().__init__("JamBase API key is not configured.", status_code=503)


class JamBaseLocationNotFoundError(JamBaseError):
    def __init__(self, location: str) -> None:
        super().__init__(f"No JamBase location match found for '{location}'.", status_code=404)


@dataclass
class ResolvedLocation:
    display_name: str
    city: str | None
    region: str | None
    country: str | None
    geo_city_id: str | None
    geo_metro_id: str | None


class JamBaseClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def search_events(
        self,
        *,
        location_query: str,
        page: int,
        per_page: int,
    ) -> EventSearchResponse:
        if not self.settings.jambase_api_key:
            raise JamBaseConfigurationError()

        location = await self._resolve_location(location_query)
        events_payload = await self._fetch_events(location=location, page=page, per_page=per_page)

        raw_events = events_payload.get("events", [])
        pagination = events_payload.get("pagination", {})
        normalized_events = [self._normalize_event(event) for event in raw_events]
        sorted_events = sorted(normalized_events, key=self._event_sort_key)

        return EventSearchResponse(
            location=SearchLocation(
                display_name=location.display_name,
                city=location.city,
                region=location.region,
                country=location.country,
                geo_city_id=location.geo_city_id,
                geo_metro_id=location.geo_metro_id,
            ),
            pagination=PaginationSummary(
                page=int(pagination.get("page", page)),
                per_page=int(pagination.get("perPage", per_page)),
                total_items=int(pagination.get("totalItems", len(raw_events))),
                total_pages=int(pagination.get("totalPages", 1)),
            ),
            events=sorted_events,
        )

    async def _resolve_location(self, location_query: str) -> ResolvedLocation:
        city_name, state_iso = self._parse_location_query(location_query)
        params: dict[str, Any] = {"geoCityName": city_name, "perPage": 5}
        if state_iso:
            params["geoStateIso"] = state_iso

        raw_location = await self._request(
            "/geographies/cities",
            params=params,
        )
        cities = raw_location.get("cities", [])
        if not cities:
            raise JamBaseLocationNotFoundError(location_query)

        best_match = cities[0]
        return ResolvedLocation(
            display_name=self._build_location_label(best_match, location_query),
            city=self._first_string(best_match, "name", "city", "geoCityName"),
            region=self._first_string(best_match, "stateIso", "region", "geoStateIso"),
            country=self._first_string(best_match, "countryIso2", "country", "geoCountryIso2"),
            geo_city_id=self._first_string(best_match, "geoCityId", "cityId", "id", "identifier"),
            geo_metro_id=self._first_string(best_match, "geoMetroId", "metroId"),
        )

    async def _fetch_events(
        self,
        *,
        location: ResolvedLocation,
        page: int,
        per_page: int,
    ) -> dict[str, Any]:
        start_date = date.today()
        end_date = start_date + timedelta(days=self.settings.event_window_days)
        params: dict[str, Any] = {
            "page": page,
            "perPage": per_page,
            "eventDateFrom": start_date.isoformat(),
            "eventDateTo": end_date.isoformat(),
        }

        if location.geo_metro_id:
            params["geoMetroId"] = location.geo_metro_id
        elif location.geo_city_id:
            params["geoCityId"] = location.geo_city_id
        else:
            raise JamBaseLocationNotFoundError(location.display_name)

        return await self._request("/events", params=params)

    async def _request(self, path: str, *, params: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.settings.jambase_api_key}",
            "Accept": "application/json",
            "User-Agent": self.settings.jambase_user_agent,
        }
        timeout = httpx.Timeout(self.settings.jambase_timeout_seconds)
        url = f"{self.settings.jambase_base_url.rstrip('/')}{path}"

        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(url, params=params, headers=headers)
            except httpx.TimeoutException as exc:
                if attempt == 2:
                    raise JamBaseError("JamBase request timed out.", status_code=504) from exc
                await asyncio.sleep(0.25 * (2**attempt))
                continue
            except httpx.HTTPError as exc:
                raise JamBaseError("JamBase request failed before reaching the API.") from exc

            if response.status_code == 429 and attempt < 2:
                retry_after = float(response.headers.get("Retry-After", "1"))
                await asyncio.sleep(retry_after)
                continue

            if response.status_code in {500, 502, 504} and attempt < 2:
                await asyncio.sleep(0.5 * (2**attempt))
                continue

            if response.is_success:
                return response.json()

            if response.status_code == 401:
                raise JamBaseError(
                    "JamBase rejected the API key. Check JAMBASE_API_KEY.",
                    status_code=502,
                )

            if response.status_code == 404 and path == "/geographies/cities":
                raise JamBaseError(
                    "JamBase city search endpoint was not found. Verify the configured API version.",
                    status_code=502,
                )

            detail = self._extract_error_detail(response)
            raise JamBaseError(detail, status_code=502)

        raise JamBaseError("JamBase request failed after retries.")

    def _normalize_event(self, event: dict[str, Any]) -> EventSummary:
        location = event.get("location") or {}
        address = location.get("address") or {}
        offers = event.get("offers") or []
        performers = event.get("performer", [])

        headliners = [
            performer.get("name")
            for performer in performers
            if isinstance(performer, dict) and performer.get("name")
        ]
        genres = self._extract_genres(performers)

        prices = [
            offer.get("price")
            for offer in offers
            if isinstance(offer, dict) and isinstance(offer.get("price"), (int, float))
        ]
        ticket_url = next(
            (
                offer.get("url")
                for offer in offers
                if isinstance(offer, dict) and isinstance(offer.get("url"), str)
            ),
            None,
        )

        city = self._first_string(address, "addressLocality", "city")
        region = self._first_string(address, "addressRegion", "region")
        country = self._first_string(address, "addressCountry", "country")

        return EventSummary(
            id=str(event.get("identifier") or event.get("id") or ""),
            name=str(event.get("name") or "Untitled event"),
            start_date=self._first_string(event, "startDate", "date"),
            end_date=self._first_string(event, "endDate"),
            venue_name=self._first_string(location, "name"),
            venue_city=city,
            venue_region=region,
            venue_country=country,
            headliners=headliners,
            genres=genres,
            image_url=self._pick_image(event.get("image")),
            event_url=self._first_string(event, "url"),
            ticket_url=ticket_url,
            min_price=min(prices) if prices else None,
            max_price=max(prices) if prices else None,
        )

    def _build_location_label(self, city: dict[str, Any], fallback: str) -> str:
        parts = [
            self._first_string(city, "name", "city", "geoCityName"),
            self._first_string(city, "stateIso", "region", "geoStateIso"),
            self._first_string(city, "countryIso2", "country", "geoCountryIso2"),
        ]
        compact = ", ".join(part for part in parts if part)
        return compact or fallback

    def _extract_error_detail(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return f"JamBase request failed with status {response.status_code}."

        if isinstance(payload, dict):
            return str(payload.get("detail") or payload.get("title") or payload)
        return f"JamBase request failed with status {response.status_code}."

    def _pick_image(self, value: Any) -> str | None:
        if isinstance(value, str):
            return value
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    return item
                if isinstance(item, dict):
                    candidate = self._first_string(item, "url", "src")
                    if candidate:
                        return candidate
        if isinstance(value, dict):
            return self._first_string(value, "url", "src")
        return None

    def _first_string(self, payload: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    def _extract_genres(self, performers: list[Any]) -> list[str]:
        seen: set[str] = set()
        genres: list[str] = []

        for performer in performers:
            if not isinstance(performer, dict):
                continue

            raw_genres = performer.get("genre")
            if not isinstance(raw_genres, list):
                continue

            for genre in raw_genres:
                if not isinstance(genre, str):
                    continue

                normalized = genre.strip()
                if not normalized:
                    continue

                key = normalized.lower()
                if key in seen:
                    continue

                seen.add(key)
                genres.append(normalized.title())

        return genres[:4]

    def _event_sort_key(self, event: EventSummary) -> tuple[datetime, str]:
        parsed_start = self._parse_event_datetime(event.start_date)
        if parsed_start is None:
            return (datetime.max, event.name.lower())
        return (parsed_start, event.name.lower())

    def _parse_event_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None

        normalized = value.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None

    def _parse_location_query(self, location_query: str) -> tuple[str, str | None]:
        parts = [part.strip() for part in location_query.split(",") if part.strip()]
        if not parts:
            return location_query.strip(), None

        city_name = parts[0]
        if len(parts) == 1:
            return city_name, None

        state_part = parts[1].upper()
        if len(state_part) == 2:
            return city_name, f"US-{state_part}"
        if state_part.startswith("US-"):
            return city_name, state_part
        return city_name, None
