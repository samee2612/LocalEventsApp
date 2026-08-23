from app.api.routes import get_jambase_client
from app.models import EventSearchResponse, EventSummary, PaginationSummary, SearchLocation
from app.services.jambase import JamBaseError


class StubJamBaseClient:
    def __init__(self, response: EventSearchResponse | None = None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.calls: list[dict[str, object]] = []

    async def search_events(self, *, location_query: str, page: int, per_page: int) -> EventSearchResponse:
        self.calls.append(
            {"location_query": location_query, "page": page, "per_page": per_page}
        )
        if self.error:
            raise self.error
        assert self.response is not None
        return self.response


def test_events_route_returns_normalized_payload(client) -> None:
    stub = StubJamBaseClient(
        response=EventSearchResponse(
            location=SearchLocation(display_name="San Francisco"),
            pagination=PaginationSummary(page=1, per_page=12, total_items=1, total_pages=1),
            events=[
                EventSummary(
                    id="jambase:1",
                    name="Test Event",
                    start_date="2026-08-23T20:00:00",
                    venue_name="Venue",
                    venue_city="San Francisco",
                    headliners=["Artist One"],
                    genres=["Rock"],
                )
            ],
        )
    )
    client.app.dependency_overrides[get_jambase_client] = lambda: stub

    response = client.get("/api/events", params={"location": "San Francisco"})

    client.app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["location"]["display_name"] == "San Francisco"
    assert body["events"][0]["genres"] == ["Rock"]
    assert stub.calls == [{"location_query": "San Francisco", "page": 1, "per_page": 12}]


def test_events_route_caps_page_size(client) -> None:
    stub = StubJamBaseClient(
        response=EventSearchResponse(
            location=SearchLocation(display_name="San Francisco"),
            pagination=PaginationSummary(page=1, per_page=24, total_items=0, total_pages=0),
            events=[],
        )
    )
    client.app.dependency_overrides[get_jambase_client] = lambda: stub

    response = client.get("/api/events", params={"location": "San Francisco", "per_page": 100})

    client.app.dependency_overrides.clear()
    assert response.status_code == 200
    assert stub.calls == [{"location_query": "San Francisco", "page": 1, "per_page": 24}]


def test_events_route_maps_provider_errors(client) -> None:
    stub = StubJamBaseClient(error=JamBaseError("Upstream unavailable", status_code=502))
    client.app.dependency_overrides[get_jambase_client] = lambda: stub

    response = client.get("/api/events", params={"location": "San Francisco"})

    client.app.dependency_overrides.clear()
    assert response.status_code == 502
    assert response.json() == {"detail": "Upstream unavailable"}
