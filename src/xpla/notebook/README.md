# xPLN — Notebook Application

xPLN is a courseware management application built on top of the [xPLA](../xpla/) framework. It provides a web interface for organizing courses, pages, and learning activities, with real-time activity execution via WebSockets.

## Architecture

```
┌──────────────────────────────────────────────┐
│            FastAPI server (port 9753)         │
│                                              │
│  /api/*          REST + WebSocket endpoints  │
│  /a/*            Activity asset serving      │
│  /static/*       Shared static files         │
│  /_next/*        Built frontend assets       │
│  /*              SPA fallback (index.html)   │
│                                              │
│  SQLite + Alembic   │  xPLA ActivityRuntime  │
│  React (static)     │  WebSocket EventBus    │
└──────────────────────────────────────────────┘
```

**Backend** ([app.py](./app.py)): FastAPI server handling CRUD operations, activity execution, WebSocket connections, and serving the built frontend.

**Frontend** ([frontend/](./frontend/)): Next.js app (static export) providing the UI — course/page/activity management with drag-and-drop reordering. Built to `frontend/out/` and served by FastAPI.

**Database** ([db.py](./db.py)): SQLite database at `dist/xpln.db`, with Alembic migrations in [migrations/](./migrations/). Migrations run automatically on startup.

## Data Model

Defined in [models.py](./models.py):

- **User** — account with email + pbkdf2-hashed password
- **UserSession** — opaque session token backing the `xpln_session` cookie
- **Course** — top-level container owned by a single user (`owner_id`); private to its owner
- **Page** — belongs to a course, contains activities
- **PageActivity** / **CourseActivity** — instances of an activity type on a page or on the course dashboard
- **ActivityStatement** — report statements (completed, passed, failed, progressed, scored) emitted by activity sandboxes, with optional score and timestamp

Field persistence (learner state, scores, etc.) is handled by [field_store.py](./field_store.py), which implements the xPLA `FieldStore` interface using three SQLite tables for scalar values, log entries, and sequence counters.

## Authentication

Email/password auth with a DB-backed session token. See [auth.py](./auth.py) and [views/auth.py](./views/auth.py) for the endpoints (`/api/auth/signup`, `/api/auth/login`, `/api/auth/logout`, `/api/me`). All course/page/activity routes require an authenticated user, and each course is private to its `owner_id`.

## API

The REST API and WebSocket endpoint are defined in [app.py](./app.py).

## Frontend

The Next.js app lives in [frontend/](./frontend/). Key areas:

- **Routes** ([frontend/src/app/](./frontend/src/app/)): single catch-all route with client-side routing to home (courses list), course detail (pages), page detail (activities), and activities management
- **Components** ([frontend/src/components/](./frontend/src/components/)): course/page/activity lists, sidebar navigation, `<xpl-activity>` web component wrapper
- **API client** ([frontend/src/lib/api.ts](./frontend/src/lib/api.ts)): typed fetch wrappers for all backend endpoints

## Running

From the project root:

```bash
npm install src/xpla/notebook/frontend/
make notebook-frontend-build   # Build the frontend static export
make notebook-server            # FastAPI server on port 9753
```

Then open http://localhost:9753.

For active frontend development with HMR, you can run `cd src/xpla/notebook/frontend && npm run dev` alongside the FastAPI server.

## How Activities Work

1. Activity types are discovered by scanning `samples/` for directories containing a `manifest.json`
2. When a user opens an activity, the backend creates an xPLA `ActivityRuntime` that loads the manifest and manages sandbox execution
3. The frontend renders a `<xpl-activity>` custom element (defined in [src/xpla/static/js/xpla.js](../static/js/xpla.js)) which connects via WebSocket
4. Actions and events flow between the client script and the WASM sandbox through the WebSocket, with permission-based filtering via the `EventBus`

Permission levels: **view** (read-only), **play** (interactive, for learners), **edit** (authoring).
