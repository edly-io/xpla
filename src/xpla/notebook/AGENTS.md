# xPLA Notebook application

This file provides guidance to AI agents when working with code in this directory.

See [README.md](./README.md) for the full architecture, data model, and API documentation.

## Commands

```bash
# Backend
make notebook-server              # FastAPI dev server on port 9753

# Frontend (from project root)
make notebook-frontend-build      # Static export to frontend/out/
# Or with HMR during frontend development:
cd src/xpla/notebook/frontend && npm run dev

# Tests
pytest src/xpla/notebook/         # Unit tests
```

The frontend must be built before the backend can serve it (SPA fallback serves `frontend/out/index.html`).

## Database Migrations

SQLite database lives at `dist/xpln.db`. Migrations run automatically on server startup via `db.run_migrations()`.

To create a new migration after changing models in `models.py` or `field_store.py`:

```bash
cd src/xpla/notebook && alembic revision -m "description"
```

Migration env imports models from both `models.py` and `field_store.py` — add imports to `migrations/env.py` if you create new SQLModel tables elsewhere. Migrations use `render_as_batch=True` (required for SQLite ALTER TABLE support).

## Key Patterns

- **Activity type namespacing**: built-in samples use plain names (`quiz`); user-uploaded activities use `@student/{name}`. `find_activity_dir()` in `app.py` resolves both.
- **Field store composite key**: `(course_id, activity_name, activity_id, user_id, key)` — all five segments are needed to locate a value. Three backing tables: `FieldEntry` (scalars), `FieldLogEntry` (append-only logs), `FieldLogSeq` (sequence counters).
- **Frontend static export**: Next.js builds to `frontend/out/`. FastAPI serves it and falls back to `index.html` for client-side routing. The catch-all route `[[...path]]` with `ClientRouter` handles all navigation client-side.
- **WebSocket events**: the `EventBus` routes sandbox events to connected clients filtered by permission level.

## Development guidelines

- Always run `make notebook-frontend-build` after changes to the frontend code.
- Update this `AGENTS.md` file after any change that affect the project structure.
- After major changes, check `README.md` and update the information if needed.
