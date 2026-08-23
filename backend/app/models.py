from pydantic import BaseModel, Field


class EventSummary(BaseModel):
    id: str
    name: str
    start_date: str | None = None
    end_date: str | None = None
    venue_name: str | None = None
    venue_city: str | None = None
    venue_region: str | None = None
    venue_country: str | None = None
    headliners: list[str] = Field(default_factory=list)
    image_url: str | None = None
    event_url: str | None = None
    ticket_url: str | None = None
    min_price: float | None = None
    max_price: float | None = None


class SearchLocation(BaseModel):
    display_name: str
    city: str | None = None
    region: str | None = None
    country: str | None = None
    geo_city_id: str | None = None
    geo_metro_id: str | None = None


class PaginationSummary(BaseModel):
    page: int
    per_page: int
    total_items: int
    total_pages: int


class EventSearchResponse(BaseModel):
    location: SearchLocation
    pagination: PaginationSummary
    events: list[EventSummary]
