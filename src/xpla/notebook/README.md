# xPLN — Notebook Application

xPLN is a courseware management application built on top of the [xPLA](../xpla/) framework. It provides a web interface for organizing courses, pages, and learning activities, with real-time activity execution via WebSockets.

## Architecture

```
┌──────────────────────┐      proxy       ┌──────────────────────┐
│   Next.js frontend   │  ──────────────► │   FastAPI backend    │
│   (port 3000)        │  /api, /a,       │   (port 9753)        │
│                      │  /static         │                      │
│  React + shadcn/ui   │                  │  SQLite + Alembic    │
│  Tailwind CSS        │                  │  xPLA ActivityRuntime │
│  @dnd-kit            │                  │  WebSocket EventBus  │
└──────────────────────┘                  └──────────────────────┘
```

**Backend** ([app.py](./app.py)): FastAPI server handling CRUD operations, activity execution, and WebSocket connections.

**Frontend** ([frontend/](./frontend/)): Next.js app providing the UI — course/page/activity management with drag-and-drop reordering.

**Database** ([db.py](./db.py)): SQLite database at `dist/xpln.db`, with Alembic migrations in [migrations/](./migrations/). Migrations run automatically on startup.

## Data Model

Defined in [models.py](./models.py):

- **Course** — top-level container with title and position
- **Page** — belongs to a course, contains activities
- **PageActivity** — an instance of an activity type on a page

Field persistence (learner state, scores, etc.) is handled by [field_store.py](./field_store.py), which implements the xPLA `FieldStore` interface using three SQLite tables for scalar values, log entries, and sequence counters.

## API

The REST API and WebSocket endpoint are defined in [app.py](./app.py).

## Frontend

The Next.js app lives in [frontend/](./frontend/). Key areas:

- **Routes** ([frontend/src/app/](./frontend/src/app/)): home (courses list), course detail (pages), page detail (activities)
- **Components** ([frontend/src/components/](./frontend/src/components/)): course/page/activity lists, sidebar navigation, `<xpl-activity>` web component wrapper
- **API client** ([frontend/src/lib/api.ts](./frontend/src/lib/api.ts)): typed fetch wrappers for all backend endpoints

The frontend proxies API requests to the backend via Next.js rewrites configured in [next.config.ts](./frontend/next.config.ts).

## Running

From the project root:

```bash
make notebook-server              # Backend: FastAPI dev server on port 9753
make notebook-server-frontend     # Frontend: Next.js dev server on port 3000
```

Then open the frontend server at http://localhost:3000.

Both servers must be running. The frontend proxies `/api/*`, `/a/*`, and `/static/*` to the backend.

## How Activities Work

1. Activity types are discovered by scanning `samples/` for directories containing a `manifest.json`
2. When a user opens an activity, the backend creates an xPLA `ActivityRuntime` that loads the manifest and manages sandbox execution
3. The frontend renders a `<xpl-activity>` custom element (defined in [src/xpla/static/js/xpla.js](../static/js/xpla.js)) which connects via WebSocket
4. Actions and events flow between the client script and the WASM sandbox through the WebSocket, with permission-based filtering via the `EventBus`

Permission levels: **view** (read-only), **play** (interactive, for learners), **edit** (authoring).
