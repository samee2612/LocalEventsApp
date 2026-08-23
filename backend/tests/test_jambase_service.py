from datetime import UTC, datetime, timedelta

from app.config import Settings
from app.models import EventSearchResponse, PaginationSummary, SearchLocation
from app.services.jambase import CachedResponse, JamBaseClient


def build_client() -> JamBaseClient:
    return JamBaseClient(
        Settings(
            JAMBASE_API_KEY="test-key",
            BACKEND_CORS_ORIGINS="http://localhost:5173,http://127.0.0.1:5173",
        )
    )


def test_normalize_event_extracts_genres_and_prices() -> None:
    client = build_client()

    event = {
        "identifier": "jambase:1",
        "name": "Test Event",
        "startDate": "2026-08-23T20:00:00",
        "location": {
            "name": "The Chapel",
            "address": {
                "addressLocality": "San Francisco",
                "addressRegion": "CA",
                "addressCountry": "US",
            },
        },
        "performer": [
            {"name": "Artist One", "genre": ["rock", "indie"]},
            {"name": "Artist Two", "genre": ["Rock", "pop"]},
        ],
        "offers": [
            {"price": 35, "url": "https://tickets.example.com"},
            {"price": 45},
        ],
        "image": {"url": "https://images.example.com/event.jpg"},
        "url": "https://events.example.com/test-event",
    }

    normalized = client._normalize_event(event)

    assert normalized.headliners == ["Artist One", "Artist Two"]
    assert normalized.genres == ["Rock", "Indie", "Pop"]
    assert normalized.min_price == 35
    assert normalized.max_price == 45
    assert normalized.ticket_url == "https://tickets.example.com"
    assert normalized.image_url == "https://images.example.com/event.jpg"


def test_search_results_are_sorted_by_start_date() -> None:
    client = build_client()

    later_event = client._normalize_event(
        {
            "identifier": "jambase:later",
            "name": "Later Event",
            "startDate": "2026-08-23T21:00:00",
            "location": {"name": "Venue", "address": {"addressLocality": "SF"}},
            "performer": [],
        }
    )
    earlier_event = client._normalize_event(
        {
            "identifier": "jambase:earlier",
            "name": "Earlier Event",
            "startDate": "2026-08-23T19:00:00",
            "location": {"name": "Venue", "address": {"addressLocality": "SF"}},
            "performer": [],
        }
    )
    undated_event = client._normalize_event(
        {
            "identifier": "jambase:undated",
            "name": "Undated Event",
            "location": {"name": "Venue", "address": {"addressLocality": "SF"}},
            "performer": [],
        }
    )

    events = sorted([later_event, undated_event, earlier_event], key=client._event_sort_key)

    assert [event.name for event in events] == [
        "Earlier Event",
        "Later Event",
        "Undated Event",
    ]


def test_parse_location_query_accepts_state_shorthand() -> None:
    client = build_client()

    city_name, state_iso, country_hint = client._parse_location_query("San Francisco, CA")

    assert city_name == "San Francisco"
    assert state_iso == "US-CA"
    assert country_hint is None


def test_city_match_score_prefers_exact_state_match() -> None:
    client = build_client()

    matching_city = {
        "name": "Portland",
        "stateIso": "US-OR",
        "countryIso2": "US",
    }
    non_matching_city = {
        "name": "Portland",
        "stateIso": "US-ME",
        "countryIso2": "US",
    }

    matching_score = client._city_match_score(
        city=matching_city,
        city_name="Portland",
        state_iso="US-OR",
        country_hint=None,
    )
    non_matching_score = client._city_match_score(
        city=non_matching_city,
        city_name="Portland",
        state_iso="US-OR",
        country_hint=None,
    )

    assert matching_score > non_matching_score


def test_cached_response_is_returned_when_fresh() -> None:
    client = build_client()
    response = EventSearchResponse(
        location=SearchLocation(display_name="San Francisco"),
        pagination=PaginationSummary(page=1, per_page=12, total_items=0, total_pages=0),
        events=[],
    )
    cache_key = ("san francisco", 1, 12)
    client._cache[cache_key] = CachedResponse(
        expires_at=datetime.now(UTC) + timedelta(seconds=30),
        value=response,
    )

    cached = client._get_cached_response(cache_key)

    assert cached == response


def test_expired_cached_response_is_ignored() -> None:
    client = build_client()
    response = EventSearchResponse(
        location=SearchLocation(display_name="San Francisco"),
        pagination=PaginationSummary(page=1, per_page=12, total_items=0, total_pages=0),
        events=[],
    )
    cache_key = ("san francisco", 1, 12)
    client._cache[cache_key] = CachedResponse(
        expires_at=datetime.now(UTC) - timedelta(seconds=1),
        value=response,
    )

    cached = client._get_cached_response(cache_key)

    assert cached is None
    assert cache_key not in client._cache
