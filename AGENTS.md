# PXC

This file provides guidance to AI agents working on the PXC codebase — runtime library, demo app, notebook app, tools, and manifest schema. For creating new sample activities, see the `pxc-build-activity` skill.

## What is PXC

Portable, SandboXed Components — a standard for portable, sandboxed online learning activities. Activities are self-contained packages with:

- **manifest.json** (required) — declares fields, actions, events, capabilities, assets
- **ui.js** (required) — exports `setup(activity)`, renders UI in the browser
- **sandbox.js → sandbox.wasm** (optional) — sandboxed backend logic via WASM Component Model, used for grading and state management

The runtime loads manifests, validates actions/events/fields at runtime, executes WASM sandboxes with capability-based permissions, and routes events between UIs and sandboxes via WebSocket.

## Codebase layout

```
src/pxc/
  lib/                    Core runtime library (Python)
    runtime.py            ActivityRuntime — central orchestrator
    sandbox.py            WASM Component Model executor (wasmtime)
    fields.py             Field type/scope validation (FieldChecker)
    actions.py            Client-to-server action validation (ActionChecker)
    events.py             Server-to-client event validation (EventChecker)
    capabilities.py       Capability enforcement (CapabilityChecker)
    event_bus.py          In-memory pub/sub for WebSocket events (EventBus)
    field_store.py        Abstract FieldStore + MemoryKVStore
    file_storage.py       Abstract FileStorage + LocalFileStorage + MemoryFileStorage
    permission.py         Permission enum (view, play, edit)
    manifest_types.py     Auto-generated Pydantic models from schema (DO NOT EDIT)
    sandbox/
      manifest.schema.json  JSON Schema for activity manifests
      pxc.wit              Canonical WIT: types + state/grading/http/storage/analytics interfaces
      index.js              JS sandbox helper lib
    tests/
      runtime/            Runtime integration tests
      samples/            Per-sample activity tests
        conftest.py       make_runtime() helper — creates ActivityRuntime with MemoryKVStore + MemoryFileStorage
      test_fields.py, test_actions.py, test_events.py, test_capabilities.py, etc.

  demo/                   Minimal demo FastAPI app (port 9752)
    app.py                Routes, WebSocket, asset serving
    kv.py                 KVStore (MemoryKVStore subclass with JSON file persistence)
    templates/            Jinja2 templates
    tests/

  notebook/               PXC notebook app (port 9753)
    app.py                FastAPI server — REST API + WebSocket + activity execution
    models.py             SQLModel: Course, Page, PageActivity
    db.py                 SQLite database setup + engine
    field_store.py        SQLiteFieldStore (FieldEntry, FieldLogEntry, FieldLogSeq tables)
    llms.py               LLM integration
    migrations/           Alembic migrations
    frontend/             Next.js static app (TypeScript, React)
    tests/

  lti/                    LTI 1.3 tool provider (port 9754)
    app.py                FastAPI server — OIDC, deep linking, resource link launches
    config.py             Env-driven configuration (LTI_BASE_URL, etc.)
    integration.py        Bridge between LTI launches and ActivityRuntime
    core/
      routes.py           LTI endpoints (login, launch, jwks, deep linking)
      oidc.py             OIDC authentication flow
      launch.py           JWT validation + launch handling
      deep_linking.py     Deep linking message construction
      keys.py             RSA keypair management / JWKS
      models.py           Platform registration models
      db.py               Platform storage
    templates/            Jinja2 templates (admin UI, activity render, launch error)

  static/js/pxc.js      <pxc-activity> web component (shared across apps)
  tools/
    validate_manifest.py  Manifest validation script

samples/                  Sample activities (mcq, quiz, chat, image, video, etc.)
.notes/                   Architecture notes
```

## Core runtime architecture

### ActivityRuntime (runtime.py)

Central orchestrator. Created per-request by both apps.

```python
ActivityRuntime(
    activity_dir: Path,       # directory containing manifest.json
    field_store: FieldStore,  # persistence backend
    file_storage: FileStorage,# file persistence backend
    activity_id: str,
    course_id: str,
    user_id: str,
    permission: Permission,
)
```

On construction:
1. Loads and validates `manifest.json` via `PxcActivityManifest.model_validate_json()`
2. Creates checkers: `CapabilityChecker`, `FieldChecker`, `ActionChecker`, `EventChecker`
3. If `manifest.sandbox` is declared, loads WASM via `get_sandbox_executor(wasm_path, host_functions)` where `host_functions()` returns a `dict[interface_name, dict[fn_name, callable]]` grouped by WIT interface

Key methods:
- `get_state() -> dict` — calls sandbox `get-state` if exported, else returns `get_all_fields()`
- `on_action(name, value)` — validates action, calls sandbox `on-action`, buffers events
- `clear_pending_events() -> list[PendingEvent]` — returns and clears buffered events
- `get_all_fields() -> dict` — loads all non-log fields with scope resolution
- `load_field()` / `store_field()` — single field get/set with validation
- `get_asset_path(path) -> Path` — validates and resolves asset paths
- Host functions: `get_field`, `set_field`, `send_event`, `log_*`, `storage_*`, `http_request`, `submit_grade`

**Scope resolution**: `_scope_key_segments(scope, context)` maps field scope + optional context overrides to `(activity_id, course_id, user_id)` tuple. KV key pattern: `pxc.<activity_name>.<course_id>.<activity_id>.<user_id>.<key>`.

**Events flow**: sandbox calls `send_event()` → validated by `EventChecker` → appended to `_pending_events` → caller retrieves via `clear_pending_events()` → published through `EventBus`.

### SandboxComponentExecutor (sandbox.py)

Executes WASM Component Model modules via wasmtime.

- `call_function(name, *args)` — creates a fresh `Store` + `Instance` per call (no state reuse), registers host functions with one `linker.add_instance("pxc:sandbox/<interface>")` per declared interface (e.g. `state`, `grading`, `storage`), calls the exported function. A sandbox that imports an interface without the matching capability fails at instantiation.
- `load_component()` — caches compiled WASM as `.bin` file for faster subsequent loads
- `make_host_function()` — wraps Python functions for wasmtime (adds Store arg, converts Record ↔ dict)
- `call_sandbox_function()` — converts dict args to `RecordArg`, always calls `post_return()` to prevent memory leaks
- Memory limit: `MEMORY_LIMIT_BYTES = 20MB`

### Checkers

All checkers follow the same pattern: initialized from manifest declarations, expose a `validate()` method that raises a specific error.

- `FieldChecker(fields)` — validates field values via `jsonschema`, resolves defaults, scopes. Key methods: `validate()`, `get_default()`, `get_scope()`, `get_definition()`, `require_log_type()`, `validate_log_item()`. Uses `build_type_schema()` to convert Pydantic field models to JSON Schema fragments.
- `ActionChecker(actions)` — validates action name and payload schema. Raises `ActionValidationError`.
- `EventChecker(events)` — validates event name and payload schema. Raises `EventValidationError`.
- `CapabilityChecker(capabilities)` — single enum-driven gate `is_interface_requested(InterfaceName)` (`state` always True; `grading`, `http`, `storage` gated on manifest declarations). Also exposes `check_http_request(url)` (host allowlist), `check_storage(name)`, and `get_storage_scope(name)`. Raises `CapabilityError`.

### FieldStore (field_store.py)

Abstract base with methods: `get`, `set`, `delete`, `keys` (scalar), `log_get`, `log_get_range`, `log_append`, `log_delete`, `log_delete_range`. All methods take `(course_id, activity_name, activity_id, user_id, key, ...)`.

Implementations:
- `MemoryKVStore` — in-memory dict, composite key pattern `pxc.<name>.<course>.<activity>.<user>.<key>`. Log fields stored under `__log__.<key>` as `{"next_id": N, "entries": {"0": val, ...}}`.
- `KVStore` (demo/kv.py) — extends MemoryKVStore, persists to JSON file on every write
- `SQLiteFieldStore` (notebook/field_store.py) — three SQLModel tables: `FieldEntry` (scalar), `FieldLogEntry` (log entries), `FieldLogSeq` (auto-increment sequences). Bulk delete helpers: `delete_by_course()`, `delete_by_activity()`, `delete_by_activity_name()`.

### FileStorage (file_storage.py)

Abstract base: `mkdir`, `read`, `write`, `exists`, `list`, `delete` (recursive for directories).

- `LocalFileStorage(base_dir)` — filesystem-backed, validates path traversal via `resolve().relative_to(root)`
- `MemoryFileStorage` — dict-backed, for testing

Storage paths are scoped like fields. `_storage_path()` prepends `{activity_name}/{storage_name}` then appends scope segments from `_scope_key_segments()`: e.g. `{activity_name}/{storage_name}/{course_id}/{activity_id}/{path}` for activity scope. Prefix-based deletion: `file_storage.delete(activity_name)` removes all storage for an activity type.

### EventBus (event_bus.py)

Manages WebSocket subscribers. `subscribe()` creates a `Subscriber(websocket, user_id, permission, course_id, activity_id)`. `publish()` iterates subscribers, filters by context match and permission rank (view=0 < play=1 < edit=2).

### Permission (permission.py)

```python
class Permission(Enum):
    view = "view"   # read-only
    play = "play"   # student interaction
    edit = "edit"   # author configuration
```

## WIT interfaces

The canonical WIT lives in `src/pxc/lib/sandbox/pxc.wit`. It defines `types` plus one interface per functional area. Samples copy this file and declare a `world activity` that imports only the interfaces they use.

| Interface | Gating | Functions |
|---|---|---|
| `state` | Always wired | `send-event`, `get-field`, `set-field`, `log-get`, `log-get-range`, `log-append`, `log-delete`, `log-delete-range` |
| `grading` | `capabilities.grading: {}` | `submit-grade`, `report-completed`, `report-passed`, `report-failed`, `report-progressed`, `report-scored` |
| `http` | `capabilities.http` | `http-request` |
| `storage` | `capabilities.storage` | `storage-read`, `storage-exists`, `storage-url`, `storage-list`, `storage-write`, `storage-delete` |
| `analytics` | notebook-only (`capabilities.analytics: {}`) | `report-query` |

`state` is always available; other interfaces are opt-in via the matching `capabilities` entry. Downstream apps (e.g. the notebook) register their own interfaces by overriding `ActivityRuntime.host_functions()`.

A sample world importing only what it needs:

```wit
world activity {
    use types.{context, permission};
    import state;
    import grading;           // only if capabilities.grading
    import storage;           // only if capabilities.storage
    export on-action: func(name: string, value: string, context: context, permission: permission) -> string;
    export get-state: func(context: context, permission: permission) -> string;
}
```

Corresponding sandbox imports in JS: `import { getField } from "pxc:sandbox/state"`, `import { submitGrade } from "pxc:sandbox/grading"`, etc.

**Critical**: all values cross the WASM boundary as JSON strings. Host functions in `runtime.py` do `json.dumps()`/`json.loads()` at the boundary.

## Manifest schema

Defined in `manifest.schema.json`. Required fields: `name` (string), `ui` (string, relative path). Optional: `sandbox`, `fields`, `actions`, `events`, `capabilities`, `assets`.

**Field types**: `integer`, `number`, `string`, `boolean`, `array` (requires `items`), `object` (requires `properties`), `log` (requires `items`, append-only).

**Scopes**: `activity`, `user,activity`, `course`, `user,course`, `global`, `user,global`.

**Capabilities**: `http` (with `allowed_hosts` array), `storage` (object mapping storage names to `{"scope": "<scope>"}`), `grading` (empty-object marker that unlocks the grading WIT interface). The `capabilities` object does not `additionalProperties: false` — downstream apps (notebook) add their own entries such as `analytics: {}`.

**Codegen pipeline**: `manifest.schema.json` → `datamodel-codegen` → `manifest_types.py` (Pydantic v2 models). Run `make manifest-types` after schema changes, then `make test-codegen` to verify.

## App integration patterns

### Demo app (demo/app.py)

Minimal LMS simulation. Module-level singletons: `field_store` (KVStore), `file_storage` (LocalFileStorage), `event_bus` (EventBus).

`load_activity()` creates a new `ActivityRuntime` per request, reads user/permission from cookies. Fixed `course_id="democourse"`, `activity_id=activity_type`.

Routes:
- `GET /` — list activities
- `GET /a/{type}` — render activity page
- `GET /a/{type}/embed` — iframe embed page
- `GET /a/{type}/{path}` — static asset serving (validated by `get_asset_path()`)
- `GET /activity/{type}/storage/{name}/{path}` — storage file serving (supports `?user_id=`, `?course_id=`, `?activity_id=` query params)
- `POST /api/activity/{type}/actions/{name}` — send action, publish events
- `WS /api/activity/{type}/ws` — WebSocket for real-time events

### Notebook app (notebook/app.py)

Full courseware app. Uses `SQLiteFieldStore`, `LocalFileStorage`, `EventBus`. SQLite database with Course/Page/PageActivity models. Alembic migrations run on startup.

Frontend is a Next.js static export served by FastAPI. The `<pxc-activity>` web component connects via WebSocket.

### LTI app (lti/app.py)

LTI 1.3 tool provider for integrating PXC activities into LMS platforms (Canvas, Moodle, Open edX, etc.). Implements OIDC authentication, JWT validation, nonce replay protection, deep linking (instructor selects activities to embed), and resource link launches (students launch with identity + context). Multi-tenant: multiple platforms registered via an admin UI at `/admin/platforms`. Configured via `LTI_BASE_URL` env var. Launched activities run through the same `ActivityRuntime`; user/course context comes from the validated LTI launch claims. See `src/pxc/lti/README.md` for platform registration and endpoint details.

### Client web component (static/js/pxc.js)

`PXC extends HTMLElement`. On `connectedCallback()`: parses data attributes (`data-context`, `data-state`, `data-permission`, `data-src`), sets up shadow DOM or native mode, connects WebSocket, loads activity script.

Key API exposed to activity UI scripts:
- `element` — DOM element to render into
- `context` — `{user_id, course_id, activity_id}`
- `state` — initial state from `get-state`
- `permission` — "view" | "play" | "edit"
- `sendAction(name, value)` — queues action in IndexedDB, sends via WebSocket
- `getAssetUrl(path)` — returns asset URL
- `onEvent(name, value)` — callback, overridden by activity

Offline support: actions queued in IndexedDB (`pending-actions` store), flushed when WebSocket reconnects.

## Testing patterns

### Test fixtures (lib/tests/samples/conftest.py)

```python
def make_runtime(
    sample_name: str,
    permission: Permission = Permission.play,
    activity_id: str = "a1", course_id: str = "c1", user_id: str = "u1",
) -> ActivityRuntime:
    """Create an ActivityRuntime pointing at a real sample directory."""
    return ActivityRuntime(
        SAMPLES_DIR / sample_name, MemoryKVStore(), MemoryFileStorage(),
        activity_id, course_id, user_id, permission,
    )
```

### Typical sample test pattern

```python
def test_answer_correct() -> None:
    rt = make_runtime("mcq", permission=Permission.edit)
    rt.on_action("config.save", {...})
    rt.clear_pending_events()  # discard config events
    rt.permission = Permission.play
    rt.on_action("answer.submit", [0])
    events = rt.clear_pending_events()
    result = json.loads([e for e in events if e["name"] == "answer.result"][0]["value"])
    assert result["correct"] is True
```

Key patterns:
- Use `make_runtime(sample, permission=...)` to create runtime against real sample directories
- Set permission to `edit` for config, then switch to `play` for student actions
- Call `clear_pending_events()` to discard intermediate events before asserting
- Event values are JSON strings — `json.loads()` to inspect
- Tests exercise the full stack: manifest loading → action validation → WASM execution → event emission

## Common commands

```bash
npm install                  # Install JS build tools (esbuild, componentize-js)
pip install -e .[dev]        # Install Python package with dev dependencies

make samples                 # Build all sample sandbox.wasm files
make demo-server             # Run demo app (port 9752)
make notebook-server         # Run notebook app (port 9753)
make notebook-frontend-build # Build notebook Next.js frontend
make lti-server              # Run LTI tool provider (port 9754)

make test                    # Full suite: pylint, pytest, mypy, black, manifests, codegen
make test-unit               # pytest only
make test-lint               # pylint
make test-types              # mypy --strict
make test-format             # black --check
make test-manifests          # Validate all sample manifests
make test-codegen            # Check manifest_types.py is up to date
make format                  # Format code with black

pytest src/pxc/lib/tests/test_fields.py                 # Single file
pytest src/pxc/lib/tests/test_fields.py -k test_name    # Single test

make manifest-types          # Regenerate manifest_types.py after schema changes
```

## Code conventions

**Python:**
- Type-annotate everything for `mypy --strict --ignore-missing-imports`
- Use modern types: `list`, `dict`, `set`, `X | None` (not `typing.List`, `typing.Optional`)
- Format with `black`
- Catch specific exceptions, smallest possible `try` blocks
- Prefer standard library over 3rd-party packages
- Use `col()` wrapper for SQLModel column references in `order_by()` / `desc()` (mypy requirement)

**Manifest schema:**
- `manifest_types.py` is auto-generated — never edit directly
- After changing `manifest.schema.json`, run `make manifest-types` then `make test-codegen`

**WIT interface:**
- `pxc.wit` must NOT have a version suffix on the package name (jco fails with versions)

**Makefile:**
- Do not use automatic variables (`$<`, `$@`, etc.) in recipes

**General:**
- Don't add unnecessary features, boilerplate, or comments
- Don't duplicate documentation
- Prefer editing existing files over creating new ones

## Development guidelines

- Always run `make samples` after changes to `manifest.schema.json` or sample activities
- Always create unit tests when implementing a feature, fixing a bug, or changing behaviour. Tests live in `tests/` folders of each application
- Always update `src/pxc/lib/README.md` when making feature changes to the core library

## Workflow

1. Read relevant source files before making changes
2. Make the change
3. Run the relevant tests: `make test` (or a targeted subset)
4. Fix any failures (pylint, mypy, black, pytest)
5. Report what was done and test results
