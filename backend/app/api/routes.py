from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import Settings, get_settings
from app.models import EventSearchResponse
from app.services.jambase import JamBaseClient, JamBaseError

router = APIRouter()


@router.get("/health")
def api_health_check() -> dict[str, str]:
    return {"status": "ok"}


def get_jambase_client(settings: Settings = Depends(get_settings)) -> JamBaseClient:
    return JamBaseClient(settings)


@router.get("/events", response_model=EventSearchResponse)
async def get_events(
    location: str = Query(..., min_length=2, description="City or metro area to search"),
    page: int = Query(1, ge=1),
    per_page: int | None = Query(default=None, ge=1),
    client: JamBaseClient = Depends(get_jambase_client),
    settings: Settings = Depends(get_settings),
) -> EventSearchResponse:
    requested_page_size = per_page or settings.default_results_per_page
    bounded_page_size = min(requested_page_size, settings.max_results_per_page)

    try:
        return await client.search_events(
            location_query=location.strip(),
            page=page,
            per_page=bounded_page_size,
        )
    except JamBaseError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
