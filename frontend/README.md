# Spotify Rec — Frontend (Next.js)

A minimal UI to search songs, pick seed tracks, and fetch recommendations from the backend.

## Stack
- Next.js (App Router, TS)
- React Query (data fetching)
- Jotai (lightweight global state for seeds)
- Tailwind CSS

## Getting started
```bash
npm install
npm run dev
# http://localhost:3000
```
### Environment
Create `.env.local`:
```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Project structure
```bash
src/
  app/
    page.tsx                 # Home
    search/page.tsx          # Song search -> pick seeds
    recommend/page.tsx       # Recommendations from selected seeds
    layout.tsx               # Providers + global layout
  components/
    TrackCard.tsx            # Text-only track card
    SearchBox.tsx            # Input + submit (with loading)
    Spinner.tsx              # Tiny spinner
    BackLink.tsx             # Back to Home button
  lib/
    api.ts                   # API client + response mappers
    ui.ts                    # Reusable classnames for buttons etc.
  state/
    seeds.ts                 # Jotai atoms for selected seeds (persist)
  types/
    api.ts                   # Track type aligned to backend
```
## API contracts (current)
- `GET /health -> { status: "ok" }`
- `GET /search?title|q|query=<song title>&limit=&offset= -> [{ id, title, artists[], year, pop_bucket }]`
- `GET /recommend?track_id=<id>&track_id=<id>&limit= -> [{ id, title, artists[], year, pop_bucket }]`

Tip: The client sends all three title aliases (`title`, `q`, `query`) to avoid 422s.

### Common workflows
1. Search a song title → select one or more results (can search multiple titles).
2. Click **Use N seeds** → to open the recommendations page.
3. Adjust **limit**, refresh, and (optionally) create a playlist once the backend supports it.

## Scripts
- `npm run dev` — start dev server
- `npm run build` — production build
- `npm run start` — run prod server