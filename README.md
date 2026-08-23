# Local Events App

A small app for discovering upcoming local events using a FastAPI backend and a simple frontend.

## Tech Stack

- Backend: Python, FastAPI, HTTPX
- Frontend: Vite, vanilla JavaScript

## What It Does

- Search for upcoming live events by city or metro-style location input
- Fetch live event data from the JamBase API
- Show event cards with date, venue, lineup, image, genre tags, and relevant outbound links
- Highlight a featured “Top pick” to help users decide faster
- Let users narrow results with quick genre and time-window filters
- Handle loading, empty, and error states cleanly
- Cache recent event searches to reduce repeated provider calls
- Use smarter city matching when JamBase returns multiple location candidates
- Include backend tests for normalization, caching, location matching, and route behavior

## Local Development

### Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Tests

```bash
source .venv/bin/activate
pytest backend/tests
```

## Environment Variables

Copy `.env.example` to `.env` and provide a valid `JAMBASE_API_KEY`.

Defaults assume:

- backend runs at `http://127.0.0.1:8000`
- frontend runs at `http://127.0.0.1:5173`
- cache TTL defaults to `300` seconds

## API

### `GET /api/events`

Search for upcoming events in a city or metro area.

Example:

```bash
curl "http://localhost:8000/api/events?location=San%20Francisco"
```

Query parameters:

- `location`: free-text city or metro name
- `page`: page number, defaults to `1`
- `per_page`: page size, capped server-side

## How To Test

### 1. Run the app locally

Backend:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload
```

Frontend in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Then open `http://127.0.0.1:5173`.

### 2. Test the backend automatically

From the repo root:

```bash
source .venv/bin/activate
pytest backend/tests
```

Current expected result:

- `9 passed`

### 3. Smoke test the user flow manually

- Search for `San Francisco, CA`
- Confirm events load and the featured `Top pick` appears
- Change the `When` filter to `Today` and verify the result count drops
- Change the `Genre` filter and verify the result list narrows further
- Open an event details or ticket link from a card

### 4. Check caching quickly

- Search for the same city twice in a row
- The second request should reuse the recent cached backend result for up to `300` seconds
- If you want to shorten that for testing, change `CACHE_TTL_SECONDS` in `.env`

### 5. Check smarter location matching

- Try searches with state hints such as `Portland, OR` or `San Francisco, CA`
- The backend should prefer the city candidate that matches the provided state hint instead of blindly taking the first result

## Smoke Test

Verified locally on **Sunday, August 23, 2026** with:

- FastAPI backend running on `127.0.0.1:8000`
- Vite frontend running on `127.0.0.1:5173`
- End-to-end browser flow returning live JamBase results for `San Francisco, CA`
- Featured “Top pick” rendering correctly in the live UI
- Genre and time-window filters working in the live UI
- Backend test suite passing: `9 passed`

## Deliverables Checklist

- [x] Working FastAPI backend
- [x] Working event search UI
- [x] JamBase integration
- [x] README with setup instructions
- [x] Time spent summary
- [x] Short assessment writeup

## Assessment Writeup

### Time Spent

About 1 hour 45 minutes total.

### Technology Choices

- **FastAPI** for a small but well-structured Python backend with strong typing and clear request validation.
- **HTTPX** for JamBase API integration because it keeps the external client layer simple and testable.
- **Vanilla JS + Vite** for the frontend to keep scope tight and avoid spending assessment time on framework setup overhead.

### Backend/API Design

- Exposed a single focused endpoint: `GET /api/events`
- Kept JamBase integration behind a dedicated service layer so provider-specific logic is not mixed into the route handler.
- Normalized JamBase data into a frontend-friendly response shape to reduce coupling to raw provider payloads.
- Added defensive handling for missing API keys, invalid locations, timeouts, rate limits, and upstream failures.
- Added a small in-memory cache for repeated searches to reduce unnecessary provider calls.
- Added smarter location scoring so state-qualified searches make a more intentional city selection.
- Added backend tests for normalization, sorting, cache behavior, location matching, provider error mapping, and route behavior.

### UI Design Decisions

- Used a single search box because the prompt prioritized usefulness over feature breadth.
- Chose card-based results instead of a raw list or table so users can quickly scan event name, date, venue, lineup, and links.
- Added a lightweight “Why go” note, genre tags, quick filters, and a featured “Top pick” block to make the UI more decision-oriented.
- Focused on loading, error, and empty states rather than visual polish.

### Tradeoffs Made

- Limited search to a free-text location input rather than building filters for genre, date, or distance.
- Added only a simple in-memory cache rather than a persistent or distributed cache layer.
- Kept the frontend framework-free to stay within the timebox.
- Chose a single provider integration path instead of building a full multi-provider abstraction up front.

### Improvements With More Time

- Improve location resolution with better handling for ambiguous city names.
- Add richer filters such as price, venue type, and custom date ranges.
- Replace the in-memory cache with a persistent store or distributed cache.
- Refine the featured ranking heuristic so it feels more curated than simply “earliest upcoming.”

### How AI Was Used

- Used AI to accelerate scaffolding, backend integration structure, frontend UI implementation, and iteration on README/writeup content.
- Used AI as a debugging partner during live integration testing, especially around JamBase endpoint assumptions and local CORS issues.
- Still validated key assumptions manually by running the app, checking JamBase’s current documentation, and doing a browser smoke test.

### One AI Suggestion I Changed Or Rejected

- An early integration approach assumed the city lookup endpoint was `/v3/cities`, which was wrong. I corrected it after checking JamBase’s current docs and switched to `/v3/geographies/cities`.

### Biggest Technical Limitation

- The app still depends on live provider calls at request time and only uses a simple in-memory cache, so performance and reliability are still tightly coupled to JamBase availability and latency.

### Evolving To 10 Event Providers

- Introduce a provider interface such as `search_events(location, page, per_page) -> normalized response`.
- Move each provider into its own adapter with shared normalized domain models.
- Add a provider orchestration layer for fan-out, deduplication, source ranking, and partial-failure handling.
- Cache normalized event records and resolve conflicts across providers instead of serving directly from upstream responses.
- Separate ingestion from read APIs so the user-facing app reads from a local store rather than from live provider calls.

### Self-Grade

- Code quality: A
- Work product: A
- Extensibility: A-
