import "./style.css";

const app = document.querySelector("#app");
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

app.innerHTML = `
  <main class="shell">
    <section class="hero">
      <div class="hero-copy">
        <p class="eyebrow">Local Events App</p>
        <h1>Find something good before the weekend picks itself for you.</h1>
        <p class="lede">
          Search a city to see upcoming shows, venues, and headliners pulled live
          from JamBase. The list is tuned for quick decisions, not endless browsing.
        </p>
      </div>
      <form class="search-panel" data-search-form>
        <label class="field">
          <span class="field-label">Where are you looking?</span>
          <input
            class="field-input"
            type="text"
            name="location"
            placeholder="San Francisco, CA"
            value="San Francisco, CA"
            autocomplete="off"
          />
        </label>
        <button class="search-button" type="submit">Find events</button>
      </form>
    </section>

    <section class="results-shell">
      <div class="results-header">
        <div>
          <p class="section-label">Upcoming picks</p>
          <h2 class="section-title">What’s on near you</h2>
        </div>
        <p class="results-meta" data-results-meta>Search a city to get started.</p>
      </div>
      <section class="filter-bar" data-filters hidden>
        <label class="filter-field">
          <span class="field-label">Genre</span>
          <select class="field-select" name="genre">
            <option value="">All genres</option>
          </select>
        </label>
        <label class="filter-field">
          <span class="field-label">When</span>
          <select class="field-select" name="timeWindow">
            <option value="all">Any time</option>
            <option value="today">Today</option>
            <option value="week">Next 7 days</option>
          </select>
        </label>
      </section>
      <section class="featured-pick" data-featured hidden></section>
      <div class="status-card" data-status>
        Enter a city to load upcoming events.
      </div>
      <section class="results-grid" data-results hidden></section>
    </section>
  </main>
`;

const form = app.querySelector("[data-search-form]");
const locationInput = form.querySelector('input[name="location"]');
const statusCard = app.querySelector("[data-status]");
const resultsGrid = app.querySelector("[data-results]");
const resultsMeta = app.querySelector("[data-results-meta]");
const featuredPick = app.querySelector("[data-featured]");
const filtersBar = app.querySelector("[data-filters]");
const genreSelect = filtersBar.querySelector('select[name="genre"]');
const timeWindowSelect = filtersBar.querySelector('select[name="timeWindow"]');
const submitButton = form.querySelector("button");

let activeRequestId = 0;
let latestPayload = null;

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const location = locationInput.value.trim();

  if (!location) {
    renderError("Add a city or metro area to search for events.");
    return;
  }

  const requestId = ++activeRequestId;
  setLoadingState(location);

  try {
    const response = await fetch(
      `${apiBaseUrl}/events?location=${encodeURIComponent(location)}&per_page=12`,
    );
    const payload = await response.json();

    if (requestId !== activeRequestId) {
      return;
    }

    if (!response.ok) {
      throw new Error(payload.detail || "Unable to load events right now.");
    }

    latestPayload = payload;
    populateFilters(payload.events);
    applyFilters();
  } catch (error) {
    if (requestId !== activeRequestId) {
      return;
    }

    const message =
      error instanceof Error ? error.message : "Unable to load events right now.";
    renderError(message);
  }
});

form.requestSubmit();
genreSelect.addEventListener("change", applyFilters);
timeWindowSelect.addEventListener("change", applyFilters);

function setLoadingState(location) {
  submitButton.disabled = true;
  submitButton.textContent = "Searching...";
  statusCard.hidden = false;
  statusCard.className = "status-card";
  statusCard.textContent = `Looking for upcoming events in ${location}...`;
  resultsGrid.hidden = true;
  resultsGrid.innerHTML = "";
  featuredPick.hidden = true;
  featuredPick.innerHTML = "";
  filtersBar.hidden = true;
  resultsMeta.textContent = "Loading live data from JamBase.";
}

function renderResults(payload, events) {
  submitButton.disabled = false;
  submitButton.textContent = "Find events";

  const locationLabel = payload.location?.display_name || "your area";
  const totalItems = events.length;

  resultsMeta.textContent = `${totalItems} matching events for ${locationLabel}.`;
  filtersBar.hidden = false;

  if (!events.length) {
    statusCard.hidden = false;
    statusCard.className = "status-card";
    statusCard.textContent = `No events match the current filters for ${locationLabel}.`;
    resultsGrid.hidden = true;
    resultsGrid.innerHTML = "";
    featuredPick.hidden = true;
    featuredPick.innerHTML = "";
    return;
  }

  statusCard.hidden = true;
  renderFeaturedPick(events[0], locationLabel);
  resultsGrid.hidden = false;
  resultsGrid.innerHTML = events.map(renderEventCard).join("");
}

function renderError(message) {
  submitButton.disabled = false;
  submitButton.textContent = "Find events";
  resultsMeta.textContent = "Search unavailable.";
  resultsGrid.hidden = true;
  resultsGrid.innerHTML = "";
  featuredPick.hidden = true;
  featuredPick.innerHTML = "";
  filtersBar.hidden = true;
  statusCard.hidden = false;
  statusCard.className = "status-card status-card-error";
  statusCard.textContent = message;
}

function populateFilters(events = []) {
  const genres = Array.from(
    new Set(
      events.flatMap((event) => (Array.isArray(event.genres) ? event.genres : [])),
    ),
  ).sort((left, right) => left.localeCompare(right));

  const selectedGenre = genreSelect.value;
  genreSelect.innerHTML = `
    <option value="">All genres</option>
    ${genres
      .map(
        (genre) =>
          `<option value="${escapeHtml(genre)}">${escapeHtml(genre)}</option>`,
      )
      .join("")}
  `;

  if (genres.includes(selectedGenre)) {
    genreSelect.value = selectedGenre;
  }
}

function applyFilters() {
  if (!latestPayload) {
    return;
  }

  const filteredEvents = filterEvents(latestPayload.events ?? []);
  renderResults(latestPayload, filteredEvents);
}

function filterEvents(events = []) {
  const selectedGenre = genreSelect.value;
  const selectedTimeWindow = timeWindowSelect.value;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const weekFromNow = new Date(today);
  weekFromNow.setDate(weekFromNow.getDate() + 7);

  return events.filter((event) => {
    const matchesGenre =
      !selectedGenre ||
      (Array.isArray(event.genres) && event.genres.includes(selectedGenre));

    if (!matchesGenre) {
      return false;
    }

    if (selectedTimeWindow === "all") {
      return true;
    }

    const parsed = event.start_date ? new Date(event.start_date) : null;
    if (!parsed || Number.isNaN(parsed.getTime())) {
      return false;
    }

    if (selectedTimeWindow === "today") {
      return parsed.toDateString() === today.toDateString();
    }

    if (selectedTimeWindow === "week") {
      return parsed >= today && parsed < weekFromNow;
    }

    return true;
  });
}

function renderFeaturedPick(event, locationLabel) {
  if (!event) {
    featuredPick.hidden = true;
    featuredPick.innerHTML = "";
    return;
  }

  const when = formatDate(event.start_date);
  const genres = Array.isArray(event.genres) && event.genres.length
    ? event.genres.join(", ")
    : "live music";
  const hook = buildFeaturedHook(event);

  featuredPick.hidden = false;
  featuredPick.innerHTML = `
    <div class="featured-copy">
      <p class="section-label">Top pick in ${escapeHtml(locationLabel)}</p>
      <h3 class="featured-title">${escapeHtml(event.name)}</h3>
      <p class="featured-summary">
        ${escapeHtml(hook)} Happening ${escapeHtml(when)} at ${escapeHtml(formatVenue(event))}.
      </p>
      <p class="featured-genres">Best for: ${escapeHtml(genres)}</p>
    </div>
    <div class="featured-actions">
      ${
        event.event_url
          ? `<a class="event-link" href="${escapeHtml(event.event_url)}" target="_blank" rel="noreferrer">See details</a>`
          : ""
      }
      ${
        event.ticket_url
          ? `<a class="event-link event-link-accent" href="${escapeHtml(event.ticket_url)}" target="_blank" rel="noreferrer">Get tickets</a>`
          : ""
      }
    </div>
  `;
}

function renderEventCard(event) {
  const performers = formatPerformers(event.headliners);
  const when = formatDate(event.start_date);
  const where = formatVenue(event);
  const price = formatPrice(event.min_price, event.max_price);
  const genres = formatGenres(event.genres);
  const image = event.image_url
    ? `<img class="event-image" src="${escapeHtml(event.image_url)}" alt="${escapeHtml(event.name)}" />`
    : `<div class="event-image event-image-placeholder">Live music</div>`;

  return `
    <article class="event-card">
      ${image}
      <div class="event-body">
        <div class="event-topline">
          <p class="event-date">${escapeHtml(when)}</p>
          ${price ? `<p class="event-price">${escapeHtml(price)}</p>` : ""}
        </div>
        <h3 class="event-title">${escapeHtml(event.name)}</h3>
        <p class="event-performers">${escapeHtml(performers)}</p>
        ${genres}
        <dl class="event-facts">
          <div>
            <dt>Venue</dt>
            <dd>${escapeHtml(where)}</dd>
          </div>
          <div>
            <dt>Why go</dt>
            <dd>${escapeHtml(buildRecommendation(event))}</dd>
          </div>
        </dl>
        <div class="event-actions">
          ${
            event.event_url
              ? `<a class="event-link" href="${escapeHtml(event.event_url)}" target="_blank" rel="noreferrer">Event details</a>`
              : ""
          }
          ${
            event.ticket_url
              ? `<a class="event-link event-link-accent" href="${escapeHtml(event.ticket_url)}" target="_blank" rel="noreferrer">Tickets</a>`
              : ""
          }
        </div>
      </div>
    </article>
  `;
}

function formatPerformers(headliners = []) {
  if (!Array.isArray(headliners) || !headliners.length) {
    return "Lineup details coming soon";
  }

  if (headliners.length === 1) {
    return headliners[0];
  }

  return `${headliners[0]} with ${headliners.slice(1).join(", ")}`;
}

function formatDate(value) {
  if (!value) {
    return "Date TBA";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(parsed);
}

function formatVenue(event) {
  const parts = [event.venue_name, event.venue_city].filter(Boolean);
  return parts.join(" · ") || "Venue details unavailable";
}

function formatPrice(minPrice, maxPrice) {
  const hasMin = typeof minPrice === "number";
  const hasMax = typeof maxPrice === "number";

  if (!hasMin && !hasMax) {
    return "";
  }

  const formatter = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });

  if (hasMin && hasMax && minPrice !== maxPrice) {
    return `${formatter.format(minPrice)}-${formatter.format(maxPrice)}`;
  }

  return formatter.format(minPrice ?? maxPrice);
}

function formatGenres(genres = []) {
  if (!Array.isArray(genres) || !genres.length) {
    return "";
  }

  return `
    <ul class="genre-list" aria-label="Genres">
      ${genres.map((genre) => `<li class="genre-tag">${escapeHtml(genre)}</li>`).join("")}
    </ul>
  `;
}

function buildRecommendation(event) {
  if (Array.isArray(event.genres) && event.genres.length) {
    return `Strong fit if you're in the mood for ${event.genres[0].toLowerCase()} tonight.`;
  }

  if (Array.isArray(event.headliners) && event.headliners.length > 1) {
    return `Multiple billed acts make this a stronger value night.`;
  }

  if (event.venue_name) {
    return `Useful if you already like catching shows at ${event.venue_name}.`;
  }

  return "Worth a closer look if the artist is already on your radar.";
}

function buildFeaturedHook(event) {
  if (Array.isArray(event.headliners) && event.headliners.length > 1) {
    return `${event.headliners[0]} leads a multi-act bill that feels worth planning around.`;
  }

  if (Array.isArray(event.genres) && event.genres.length) {
    return `The earliest strong option in the lineup leans ${event.genres[0].toLowerCase()}.`;
  }

  return "This is the earliest upcoming option in the current results.";
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
