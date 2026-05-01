# PXC — Core Library

This is the core runtime library for the PXC (Portable, sandboXed Components, "pixie") standard. It handles activity loading, manifest validation, sandboxed WebAssembly execution, field storage, and event routing. It is platform-agnostic and can be integrated into any LMS.

## Architecture

Key modules:

- [runtime.py](./runtime.py) — `ActivityRuntime`: central orchestrator that loads manifests, executes sandboxed code, and provides host functions
- [sandbox.py](./sandbox.py) — `SandboxComponentExecutor`: WASM Component Model execution via wasmtime
- [fields.py](./fields.py) — `FieldChecker`: validates field types and scopes against the manifest
- [actions.py](./actions.py) — `ActionChecker`: validates client-to-server actions
- [events.py](./events.py) — `EventChecker`: validates server-to-client events
- [capabilities.py](./capabilities.py) — `CapabilityChecker`: enforces declared capabilities (HTTP, AI, storage)
- [event_bus.py](./event_bus.py) — `EventBus`: in-memory pub/sub for WebSocket event broadcasting with context/permission filtering
- [field_store.py](./field_store.py) — `FieldStore`: abstract base class for field persistence (scalar and log fields)
- [file_storage.py](./file_storage.py) — `FileStorage`: abstract base class for file persistence; `LocalFileStorage`: local filesystem implementation; `MemoryFileStorage`: in-memory implementation for testing
- [kv.py](./kv.py) — `KVFieldStore`: simple JSON-file-backed `FieldStore` implementation
- [permission.py](./permission.py) — `Permission` enum: `view`, `play`, `edit`

## Execution Flow

1. `ActivityRuntime(activity_dir, field_store, ...)` loads `manifest.json` from the activity directory
2. If `manifest.server` is declared, the WASM module is loaded and host functions are registered
3. On page load, the sandbox's `get-state` is called (or all declared fields are returned)
4. When the client sends an action, `on_action()` validates it against the manifest, then calls the sandbox's `on-action()`. Events emitted by the sandbox are buffered and published via `EventBus`

## Comparison with Existing Standards

| Feature | SCORM | LTI | XBlock | H5P | PXC |
|---------|-------|-----|--------|-----|-------|
| **Portability** | ✅ Excellent – self-contained packages work across any compliant LMS | ⚠️ Limited – protocol connects external tools, but tools aren't packaged or transferable | ❌ None – tightly coupled to Open edX | ✅ Good – `.h5p` packages work across compatible platforms (Moodle, WordPress, Drupal) | ✅ Excellent – self-contained packages with explicit capability declarations |
| **Graded assessments** | ❌ Available – but cheating is trivial | ✅ Yes – grade passback via Assignment and Grades Service (LTI 1.3) | ✅ Yes – full grading integration within Open edX | ⚠️ Available – grade passback via xAPI, but grading logic runs client-side | ✅ Yes – sandboxed backend handles grading securely |
| **Sandboxed backend code execution** | ❌ No – client-side JavaScript only | ⚠️ Depends – possible in theory, but servers typically run code unsafely | ⚠️ Unsafe – arbitrary Python with full server access | ❌ No – client-side JavaScript only | ✅ Sandboxed – WebAssembly with capability-based permissions |
| **Offline access** | ⚠️ Partial – modules can be downloaded but may require network access at runtime | ❌ No – HTTP server required | ❌ No – connection to an Open edX platform is assumed | ⚠️ Partial – possible via Lumi desktop app, not in standard LMS integrations | ✅ Yes – thanks to event-driven client-to-server communication |

## Limitations

### Unsafe client code

The preferred mode for running PXC on the client is using [shadow DOM](https://developer.mozilla.org/en-US/docs/Web/API/Web_components/Using_shadow_DOM). This prevents access to the PXC from the rest of the DOM, but the reverse is not true: the PXC can access the rest of the DOM and break it. To avoid this situation, platform administrators can decide to embed PXC within iframes, which is the only safe mechanism to sandbox HTML (at the moment). But iframes come with their own set of limitations. See [Recommendations](#recommendations-1) in the Frontend API section below.

Note that most LMS support a "raw HTML" activity that is usually completely unsandboxed and is free to break the DOM and run arbitrary client code. Thus we are not sure whether the lack of client-side isolation is an actual issue.

### No versioning or migration mechanism

Currently, activity types do not have an associated version. In particular, this means that when we modify the types of activity fields, existing data must be migrated manually, at runtime, by the activity itself. We need a mechanism to facilitate upgrading activities to a new version and migrate existing data. We could draw inspiration from the [content upgrade](https://h5p.org/documentation/developers/content-upgrade) API in H5P.

### WASM Performance

Server-side WASM activity loading has not been battle-tested yet, and we do not know how it will behave under heavy load. In particular, is it practical to run the WASM module once for every event? There are frameworks, such as [WASM Cloud](https://wasmcloud.com) to address this. In any case, even if the performance is not state of the art, we are confident that the performance of WASM modules is better than, say, Python XBlocks.

### File storage

WASM modules are stored as files, which are typically difficult to distribute across cloud-native applications. Maybe we can solve this issue in Kubernetes with simple read-only persistent volumes?

In addition, WASM modules built with Javascript take around 2 MB of space each. This might be an issue, or not: is it sustainable to require ~2 GB of disk space for 1000 activity types? The size of modules can be reduced by using [AssemblyScript](https://www.assemblyscript.org/), but we haven't tried this out just yet.

### No import/export standard

We have not yet defined a standard to import and export activity instances. We would need to export all activity fields, with the exception of fields that are scoped to users or the platform. Actually, it would be up to the platform to decide whether to export activity fields that are scoped to the course, depending on whether we export a single instance or an entire course.

## Activity API Reference

This reference is aimed at course authors to create new PXC packages. We suggest to leverage generative AI to create new packages: when this documentation and sample activities are provided as context, coding LLM typically generate working PXC in a single shot.

Activities are stored as static files. The [`samples`](../../samples) directory contains a few activities that you can use as reference for your own.

The typical file hierarchy of an activity is the following:

```
my-activity/
  manifest.json
  ui.js
  sandbox.js
```

### `manifest.json` (required)

```json
{
  "name": "my-activity",
  "ui": "ui.js",
  "sandbox": "sandbox.wasm",
  "capabilities": {},
  "fields": {},
  "actions": {},
  "events": {}
}
```

- `name` (required): Activity slug, which will be used in quite a few places, including the key/value store, url, etc. Otherwise not user-visible.
- `ui` (required): Path to the client-side JavaScript user interface module, relative to `manifest.json`.
- `sandbox` (optional): Path to the server-side WebAssembly component sandbox, relative to `manifest.json`. If omitted, the activity has no backend logic.
- `capabilities` (optional, defaults to `{}`): Defines the capabilities that are granted to the sandboxed environment, including: HTTP host requests and file storage. For more details, check the [`capabilities.py`](./capabilities.py) module. Capabilities are enforced at runtime. See [Storage](#storage) below for the storage capability.
- `fields` (optional, defaults to `{}`): Declares activity fields with type and scope. Fields are validated at runtime.
- `actions` (optional, defaults to `{}`): Declares actions the client can send to the server sandbox. Each action maps a name to a payload type schema. Validated at runtime.
- `events` (optional, defaults to `{}`): Declares events the server sandbox can emit to the client. Validated at runtime.
- `assets` (optional): An array of explicit file paths that can be served as static assets. Only listed files (plus `client` and `manifest.json`) are accessible. Paths must be relative (no leading `/`) and cannot contain `..`.

The manifest format is defined by a JSON Schema at [`src/pxc/lib/sandbox/manifest.schema.json`](./sandbox/manifest.schema.json). To validate a manifest:

```bash
./src/pxc/tools/validate_manifest.py samples/my-activity/manifest.json
```

#### Fields

Each field must have a `type` and `scope`. An optional `default` can be provided (must match the declared type). Type names follow [JSON Schema](https://json-schema.org/) vocabulary. Example:

```json
{
  "fields": {
    "score": { "type": "integer", "scope": "user,activity", "default": 0 },
    "question": { "type": "string", "scope": "activity", "default": "" },
    "answers": { "type": "array", "items": { "type": "string" }, "scope": "activity", "default": [] },
    "correct_answers": { "type": "array", "items": { "type": "integer" }, "scope": "activity", "default": [] }
  }
}
```

**Types:** `integer`, `number`, `string`, `boolean`, `array`, `object`, `log`. For `array` and `log`, specify an `items` field with a type schema. For `object`, specify a `properties` field. If no `default` is provided, type-specific defaults are used: `0`, `0.0`, `""`, `false`, `[]`, `{}`. Log fields have no default and are not included in `getField`/`setField` or `get_all_fields` — they are accessed exclusively via the [log host functions](#log-fields).

**Scopes:**

| Scope | Description | Example |
|---|---|---|
| `"activity"` | Shared across users, scoped to this activity instance. | Question text configured by an instructor. |
| `"user,activity"` | Per-user, scoped to this activity instance. | A student's score. |
| `"course"` | Shared across users, scoped to the course. | Course-wide leaderboard. |
| `"user,course"` | Per-user, scoped to the course. | Cumulative course grade. |
| `"global"` | Shared across users, global to the platform. | Internal API key. |
| `"user,global"` | Per-user, global to the platform. | User language preference. |

#### Permissions

Access control is handled at runtime through **permissions** rather than per-field declarations. The platform sets a permission level for each request:

- `"view"`: Read-only / anonymous access. Can see the activity but not send any actions. Intended for anonymous users for whom the platform may not provide a stable `user_id`. Activities can still receive events in view mode.
- `"play"`: Active participant (student). Can submit answers.
- `"edit"`: Course author. Can configure the activity.

**`view` mode is read-only.** The runtime rejects any action sent with `permission === "view"` — `on_action` raises `ActionValidationError` before the sandbox is called, and the client's `sendAction` silently drops the call. Activity scripts are responsible for not rendering interactive controls (buttons, forms, etc.) when `activity.permission === "view"`.

The sandbox's `on-action` function will therefore never be called with `permission === "view"`. Sandbox scripts do not need to guard against it.

The sandbox controls what state to expose to the client via an exported `getState()` function, which receives the current permission level as input.

#### Actions & Events

Activities communicate between client and server using **actions** (client→server) and **events** (server→client). Both are declared in the manifest with a payload type schema:

```json
{
  "actions": {
    "answer.submit": {
      "type": "object",
      "properties": {
        "question": { "type": "string" },
        "answer": { "type": "string" }
      }
    }
  },
  "events": {
    "answer.result": {
      "type": "object",
      "properties": {
        "correct": { "type": "boolean" },
        "feedback": { "type": "string" }
      }
    }
  }
}
```

Payloads are validated at runtime: sending an undeclared action or emitting an undeclared event raises a validation error.

#### Storage

Activities that need to read or write files at runtime (e.g. user uploads) must declare a `storage` capability. Each storage entry has a **name** and a **scope** (same scope values as fields):

```json
{
  "capabilities": {
    "storage": {
      "media": { "scope": "activity" },
      "user_uploads": { "scope": "user,activity" }
    }
  }
}
```

Storage is for **runtime-generated files** only. Bundled static files (CSS, JS, images shipped with the activity) should be declared in the `assets` field instead and served via `getAssetUrl()` on the client.

Each storage host function takes a storage `name`, a relative `path`, and an optional `context` as arguments. The runtime validates that the name is declared in the manifest. The scope determines how files are partitioned across context dimensions (activity, course, user), just like fields. When `context` is `null`, the current context is used. Stored files are served at `/activity/{activity_id}/storage/{name}/{path}`.

The platform provides a `FileStorage` backend to the `ActivityRuntime`. The reference implementation uses `LocalFileStorage`, which stores files on the local filesystem. For cloud deployments, a custom `FileStorage` subclass (e.g. backed by S3) can be used instead. `MemoryFileStorage` is provided for unit testing.

When an activity type is deleted, the platform should call `FileStorage.delete(activity_name)` to clean up all stored files for that activity type.

### Client module (declared via `client` field)

This client-side scripting module will be loaded alongside the `<pxc-activity>` element. This module must export a `setup` function which will be called once the element is ready. The `setup` function receives the `<pxc-activity>` element as its argument, which you can use to inject HTML and add interactivity to your activity.

```javascript
export function setup(activity) {
  // activity is the <pxc-activity> DOM element
  // Inject HTML into the activity
  activity.element.innerHTML = `
    <h2>Welcome to my activity!</h2>
    <form>
      <input type="text" name="answer">
      <button type="submit">Submit</button>
    </form>
  `;

  // Add event listeners
  const form = activity.element.querySelector("form");
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    ...
  });
}
```

The `activity` object exposes the following properties and methods:

- `element`: the DOM element to which this activity is attached.
- `context`: An object with `user_id`, `course_id`, and `activity_id` identifying the current context. Parsed from the `data-context` attribute.
- `state`: An object containing the activity state. Populated by the sandbox's `get-state` function (or all declared fields if `get-state` is not exported).
- `permission`: The current permission level (`"view"`, `"play"`, or `"edit"`). Use this to adapt the UI (e.g. hide submit buttons for `"view"`).
- `sendAction(name, value)`: Sends an action to the backend sandbox. The current `permission` is included in the payload. The action name must be declared in `manifest.json`.
- `getAssetUrl(path)`: Returns the URL for an asset in the activity directory (served by the `activity_asset` endpoint).
- `onEvent(name, value)`: Override this callback to handle events from the server. Called for every event with the parsed value.

The `PXC` class is implemented in [`pxc.js`](../static/js/pxc.js).


### Server sandbox (declared via `server` field)

When declared in the manifest, this [WebAssembly](https://webassembly.org/) module will be called as a sandbox from the platform backend. In particular, it is useful for grading assessments: we don't want assessment code to run in the frontend, because it would be trivially vulnerable to cheating.

It is language-agnostic, as the original script can be written in any of the languages supported by WebAssembly. We use the [WASM Component Model](https://github.com/WebAssembly/component-model) to build and call these modules. Since the Component Model is a W3C standard, sandboxes are portable and can be run from any platform ([Open edX](https://openedx.org/), [Moodle](https://moodle.org), [Canvas](https://canvas.instructure.com/)...) using any compliant runtime (wasmtime, wasmer, etc.).

Note that sandboxes do not persist state. Thus, to get access to configuration settings, user-specific fields, etc. the sandbox should have the key-value store read/write capabilities (see `manifest.json` above).

Sandboxes have access to a standard list of host functions. See [Host interfaces](#host-interfaces) in the Platform API section below.

#### Host functions in JavaScript

Host functions are grouped into one WIT interface per functional area (see [Host interfaces](#host-interfaces) below). Activities import only the interfaces they use. Field values and event payloads are exchanged as JSON strings, so activities must `JSON.stringify` before writing and `JSON.parse` after reading.

```javascript
// Always available
import {
  sendEvent,
  getField, setField,
  logAppend, logGet, logGetRange, logDelete, logDeleteRange,
} from "pxc:sandbox/state";

// Opt-in: declare the matching capability in manifest.json
import { submitGrade, reportCompleted, reportPassed, reportFailed, reportProgressed, reportScored } from "pxc:sandbox/grading";
import { httpRequest } from "pxc:sandbox/http";
import { storageRead, storageWrite, storageExists, storageUrl, storageList, storageDelete } from "pxc:sandbox/storage";

// Send an event to all connected clients in the current activity
// sendEvent(name, value, context, permission)
//   context: null = current activity (default), or e.g. { userId: "alice" } to target a specific user
//   permission: minimum permission to receive the event ("view", "play", or "edit")
sendEvent("answer.result", JSON.stringify({ correct: true }), null, "play");

// Get/set fields (scope is resolved automatically from manifest)
const score = JSON.parse(getField("correct_answers"));
setField("correct_answers", JSON.stringify(score + 1));

const question = JSON.parse(getField("question"));
setField("question", JSON.stringify("What is 2+2?"));

// Log field operations (append-only ordered data)
const id = logAppend("messages", JSON.stringify({ user: "alice", text: "hello" }));
const entry = JSON.parse(logGet("messages", id));       // { user: "alice", text: "hello" }
const all = JSON.parse(logGetRange("messages", 0, 100)); // [{ id: 0, value: {...} }, ...]
logDelete("messages", id);                               // true
logDeleteRange("messages", 0, 50);                       // returns count deleted

// Storage operations (name + path + optional context, where name is declared in manifest capabilities)
storageWrite("media", "photo.png", imageBytes, null);           // write a file (Uint8Array)
const data = storageRead("media", "photo.png", null);           // read file contents (Uint8Array)
const exists = storageExists("media", "photo.png", null);       // true
const url = storageUrl("media", "photo.png", null);             // "/activity/{id}/storage/media/photo.png"
const [ directories, files ] = storageList("media", "", null);  // list stored files
storageDelete("media", "photo.png", null);                      // delete a file
```

#### Exported functions

The sandbox script can export the following functions:

- `on-action(input)`: Called when the frontend sends an action via `activity.sendAction(name, value)`. The `input` parameter is a JSON string with four keys: `name` (the action name), `value` (the action payload), `context` (a dict with `user_id`, `course_id`, `activity_id` identifying the current context), and `permission` (the current permission level: `"play"` or `"edit"` — `"view"` is never passed here because the runtime rejects all actions in view mode before reaching the sandbox). Returns a string (typically empty).
- `get-state(input)`: Called when the activity page loads. The `input` parameter is a JSON string with two keys: `context` (a dict with `user_id`, `course_id`, `activity_id`) and `permission` (the current permission level). Returns a JSON string of fields to send to the client. Use this to filter fields based on permission (e.g., hide correct answers from students). If not exported, the server falls back to sending all declared fields.

```javascript
import { getField } from "pxc:sandbox/state";

export function getState(context, permission) {
  const state = { question: JSON.parse(getField("question")) };
  if (permission === "edit") {
    state.correct_answers = JSON.parse(getField("correct_answers"));
  }
  return JSON.stringify(state);
}

export function onAction(name, data, context, permission) {
  const value = JSON.parse(data);
  // name: action name (e.g. "answer.submit")
  // value: action payload
  // context.userId: current user ID
  // context.courseId: current course ID
  // context.activityId: current activity instance ID
  // permission: "play" or "edit" (never "view" — runtime rejects view-mode actions)
  return "";
}
```

The `onAction` function is called whenever the frontend sends an action via `activity.sendAction(name, value)`. The sandbox can send events back to connected clients using `sendEvent(name, JSON.stringify(value), context, permission)` (which calls the `sendEvent` host function). The `context` argument controls which clients receive the event (e.g. `null` for the whole activity, `{userId: "alice"}` for a specific user), and `permission` sets the minimum permission level required to receive it.

### Building

Each sample has its own Makefile with a `build` target:

```bash
make -C samples/my-activity build
```

This produces `sandbox.wasm` in the sample directory.

To build all samples at once:

    make samples

## Platform API Reference

This section is aimed at LMS platform developers who want to integrate PXC activities into their platform.

### Backend API

The backend is responsible for loading activities, executing sandboxed code, providing host functions, and mediating communication between the frontend and the sandbox.

#### Core responsibilities

1. **Manifest validation.** Parse and validate each activity's `manifest.json` against the [JSON Schema](../sandbox-lib/manifest.schema.json). This includes validating the declared fields, actions, events, capabilities, and static assets.

2. **Sandbox execution.** Load the WebAssembly component declared in `manifest.server` and execute its exported functions (`get-state`, `on-action`). We use the [WASM Component Model](https://github.com/WebAssembly/component-model) standard, which is supported by runtimes in many host languages (Python, Go, Rust, Java, etc.) via [wasmtime](https://wasmtime.dev/) and other implementations.

3. **Host functions.** The sandbox runtime must inject a set of host functions that sandboxed code can call. These are documented in the [Host interfaces](#host-interfaces) section below. Our implementation is in [`runtime.py`](./runtime.py).

4. **Runtime validation.** Actions sent by the frontend and events emitted by the sandbox must be validated against the manifest declarations. Our implementation: [`actions.py`](./actions.py) (actions), [`events.py`](./events.py) (events), [`fields.py`](./fields.py) (fields).

5. **Key-value store.** Activity fields are persisted in a key-value store, scoped by activity name and (for user-scoped fields) user ID. The store must support `get` and `set` operations. Our implementation: [`kv.py`](./kv.py).

6. **Static asset serving.** Serve files declared in the manifest's `assets` array (plus `client` and `manifest.json`). Paths must be validated to prevent directory traversal.

#### Endpoints

The exact API is platform-specific and does not need to follow a standard. The platform must support:

- **Get state**: called on page load. The backend calls the sandbox's `get-state()` function and returns the result as JSON. If `get-state` is not exported, all declared fields are returned.
- **Send action**: called when the frontend sends an action via `sendAction(name, value)`. The backend rejects any action sent in `"view"` mode with a validation error. For other permission levels it validates the action against the manifest, then calls the sandbox's `onAction()` function with `name`, `value`, `context` (a dict with `user-id`, `course-id`, `activity-id`), and `permission`.
- **Event delivery**: events emitted by the sandbox (via `sendEvent`) are broadcast to connected clients via WebSocket, filtered by context and permission. The platform maintains a WebSocket connection per client and routes events to matching subscribers.

Our reference implementation exposes these as FastAPI endpoints in [the demo application](../demo/app.py). Event routing is handled by the [`EventBus`](./event_bus.py).

#### Host interfaces

The host surface is split into one WIT interface per functional area, defined in the canonical [`pxc.wit`](./sandbox/pxc.wit). Sandboxes import only the interfaces they need; the runtime only wires up interfaces declared via manifest capabilities (`state` is always wired). Implementation: [`runtime.py`](./runtime.py), [`capabilities.py`](./capabilities.py).

| Interface | Gating | Functions |
|---|---|---|
| `state` | Always available | `sendEvent`, `getField`, `setField`, `logGet`, `logGetRange`, `logAppend`, `logDelete`, `logDeleteRange` |
| `grading` | `capabilities.grading: {}` | `submitGrade`, `reportCompleted`, `reportPassed`, `reportFailed`, `reportProgressed`, `reportScored` |
| `http` | `capabilities.http` | `httpRequest` |
| `storage` | `capabilities.storage` | `storageRead`, `storageWrite`, `storageExists`, `storageUrl`, `storageList`, `storageDelete` |

Downstream apps may register additional interfaces (e.g. the notebook app registers `analytics` for course-level reporting). These are not part of the core schema.

**`state` (always available):**

- `sendEvent(name: str, value: str, context: str, permission: str)`: `context` is a JSON-encoded dict controlling broadcast audience (e.g. `'{"activity_id": "..."}'` or `'{}'` for defaults). `permission` is the minimum permission level to receive the event (`"view"`, `"play"`, or `"edit"`)
- `getField(name: str, context: str)` / `setField(name: str, value: str, context: str)`: scope resolved from manifest; the `context` parameter is a JSON-encoded dict of dimension overrides, with the following optional keys: `user_id`, `course_id`, `activity_id`. E.g. `{"user_id": "bob"}`. Pass `{}` for default behavior. Raises `FieldValidationError` on `log` fields — use the log functions below instead
- `logAppend(name: str, value: any, context: str) -> int`: append to a log field, returns the assigned entry ID
- `logGet(name: str, entry_id: int, context: str) -> any | null`: get a single log entry by ID
- `logGetRange(name: str, from_id: int, to_id: int, context: str) -> [{id, value}, ...]`: get entries in range `[from_id, to_id)`
- `logDelete(name: str, entry_id: int, context: str) -> bool`: delete a single entry, returns whether it existed
- `logDeleteRange(name: str, from_id: int, to_id: int, context: str) -> int`: delete entries in range, returns count deleted

**`grading` (requires `capabilities.grading: {}`)** — used to track learner progress (inspired by xAPI/cmi5 verbs):

- `submitGrade(score: float) -> bool`: submit a final grade.
- `reportCompleted() -> bool`: the learner completed the activity.
- `reportPassed(score: option<f64>) -> bool`: the learner passed. `score` is optional, in the range [0.0, 1.0].
- `reportFailed(score: option<f64>) -> bool`: the learner failed. `score` is optional, in the range [0.0, 1.0].
- `reportProgressed(progress: f64) -> bool`: progress update. `progress` is in the range [0.0, 1.0].
- `reportScored(score: f64) -> bool`: score without pass/fail judgment. `score` is in the range [0.0, 1.0].

The base `ActivityRuntime` logs report statements to stdout. Platform implementations should override these methods to persist statements (e.g. to a database).

**`http` (requires `capabilities.http`):**

- `httpRequest(url: str, method: str, body: str, headers: str)` → `{"status": int, "headers": [[k,v],...], "body": str}` (headers is a JSON-encoded list of `[key, value]` pairs).

**`storage` (requires `capabilities.storage`)** — each function takes the storage `name`, a relative `path`, and an optional `context` (pass `null` to use the current context):

- `storageRead(name: str, path: str, context) -> bytes`: read a file from the named storage.
- `storageWrite(name: str, path: str, content: bytes, context) -> bool`: write a file. Creates parent directories as needed.
- `storageExists(name: str, path: str, context) -> bool`: check whether a file exists.
- `storageUrl(name: str, path: str, context) -> str`: return the HTTP URL for a storage file (e.g. `"/activity/{activity_id}/storage/media/img.png"`). Context overrides are encoded as query parameters.
- `storageList(name: str, path: str, context) -> {files: [str], directories: [str]}`: list files and directories.
- `storageDelete(name: str, path: str, context) -> bool`: delete a file. Returns `true` if the file existed.

#### Log fields

The `log` type provides append-only ordered storage with auto-incrementing IDs, suitable for chat messages, event histories, and similar use cases. Unlike other field types, log fields are not accessible via `getField`/`setField` and are not included in `get_all_fields` — they have dedicated host functions (`logAppend`, `log_get`, `logGetRange`, `logDelete`, `logDeleteRange`).

Log fields cannot be nested: the `items` type schema uses the same types as other fields (`integer`, `number`, `string`, `boolean`, `array`, `object`) but not `log`.

**Internal storage format.** The reference implementation stores each log as a single KV entry with the structure `{"next_id": N, "entries": {"0": val, "1": val, ...}}`. This is adequate for small to medium logs.

**SQL implementation guidance.** For production platforms, logs should be backed by a SQL table rather than a single KV blob. A suggested schema:

```sql
CREATE TABLE pxc_log_entries (
    field_key  TEXT NOT NULL,   -- same scoped key as other fields
    entry_id   INTEGER NOT NULL,
    value      JSONB NOT NULL,
    PRIMARY KEY (field_key, entry_id)
);
```

With this table, `logAppend` becomes an `INSERT` with a `SELECT max(entry_id) + 1`, `log_get` is a simple `SELECT ... WHERE entry_id = ?`, `logGetRange` is `SELECT ... WHERE entry_id >= ? AND entry_id < ? ORDER BY entry_id`, and `logDelete`/`logDeleteRange` are `DELETE` statements. A separate sequence or `max + 1` query provides the next ID. This representation scales well and supports efficient range queries via the primary key index.

See the [`samples/chat`](../../samples/chat) activity for a working example.

#### Recommendations

- **Use the WASM Component Model for sandbox execution.** The Component Model provides a standardised plugin API across many host languages and handles WebAssembly loading, memory management, and host function binding. See [`sandbox.py`](./sandbox.py).
- **Validate everything at runtime.** Don't trust that activity code will send well-formed actions or events. Validate action names and payloads against the manifest before calling the sandbox, and validate events before forwarding them to the frontend.
- **Scope KV keys carefully.** We use the pattern `pxc.<activity_name>.<course_id>.<activity_id>.<user_id>.<value_name>` to prevent activities from interfering with each other's state. Depending on the scope, some segments are empty (e.g., for platform-scoped values, course_id and activity_id are empty).

### Frontend API

This section is aimed at LMS platform developers who want to render PXC activities in their frontend. The platform must provide a runtime component that loads the activity's client script and exposes a standard API to it.

#### Activity component API

The runtime must provide an `activity` object to each activity's `setup(activity)` function. This object is the sole interface between the activity client code and the platform. It must expose:

| Property / Method | Type | Description |
|---|---|---|
| `element` | DOM element | The root DOM element where the activity renders its UI. |
| `context` | `object` | Context identifying the activity instance: `{ user_id, course_id, activity_id }`. Parsed from the `data-context` attribute. |
| `state` | `object` | The activity state, populated by the backend's `get-state()` response. |
| `permission` | `string` | Current permission level: `"view"`, `"play"`, or `"edit"`. |
| `sendAction(name, value)` | `(string, any) => Promise<void>` | Sends an action to the backend sandbox via WebSocket. No-op in `"view"` mode (logs a warning). Fire-and-forget: callers are not required to `await` the returned promise. Events are delivered asynchronously through the `onEvent` callback. Activity scripts must not render interactive controls that call `sendAction` when `activity.permission === "view"`. |
| `getAssetUrl(path)` | `(string) => string` | Returns the URL for a static asset declared in the activity's manifest. |
| `onEvent(name, value)` | `(string, any) => void` | Callback invoked for every event emitted by the server. Default is a no-op; activity code overrides it. |

#### Loading flow

1. The backend calls the sandbox's `get-state()` function (if exported) to obtain the initial state for the current user and permission level. If `get-state` is not exported, all instance-level fields are returned.
2. The platform renders the activity component, passing it the initial state and permission level.
3. The runtime loads the activity's client script (declared in `manifest.client`) and calls its exported `setup(activity)` function.

#### Event processing

Events are delivered in real time via a WebSocket connection established on page load. When the server broadcasts an event (filtered by context and permission), the runtime calls `activity.onEvent(name, parsedValue)`. All events are treated uniformly — the activity's `onEvent` handler is responsible for updating `activity.state` or performing any other side effects as needed. This enables multi-user scenarios (e.g. chat) where actions by one user produce events visible to all connected clients.

#### Recommendations

- **Use a custom element.** Our implementation uses a [Web Component](https://developer.mozilla.org/en-US/docs/Web/API/Web_components) (`<pxc-activity>`), which provides a clean encapsulation boundary and works with any framework. See [`pxc.js`](../static/js/pxc.js).
- **Pass initial state as data attributes.** We serialize the context into `data-context` (a JSON object with `user_id`, `course_id`, `activity_id`), the state into `data-state`, the permission into `data-permission`, and the client script path into `data-src`. This avoids extra round-trips. See [`activity.html`](../demo/templates/activity.html).
- **Support both shadow DOM and iframe embedding.** Shadow DOM provides style encapsulation with lower overhead; iframes provide full isolation. The `<pxc-activity>` element supports an `embed` attribute that controls how the activity is rendered:
  - **`shadow`** (default): The activity runs inside a closed shadow DOM. This provides style encapsulation — activity CSS won't leak into the host page and vice versa — but doesn't fully isolate the activity from the parent document.
  - **`native`**: No shadow DOM. The activity renders directly into a wrapper `<div>`. Intended for use inside iframes, where the iframe boundary provides full isolation. In this mode, `adoptedStyleSheets` on `activity.element` is shimmed to delegate to `document.adoptedStyleSheets`, so activity code (e.g. Plyr CSS injection) works without changes.

In native/iframe mode, the element sends `postMessage` events to the parent window:

- `{ type: "pxc:ready" }`: sent after setup completes.
- `{ type: "pxc:resize", height: <number> }`: sent whenever the wrapper div resizes (via `ResizeObserver`), so the parent can auto-size the iframe.

Each activity has a standalone embed page at `/a/{name}/embed` that uses `<pxc-activity embed="native" ...>`. To embed an activity in an iframe:

```html
<iframe src="/a/math/embed" style="width: 100%; border: none;"></iframe>
```

The development server toolbar includes an "Embed" dropdown to toggle between shadow DOM and iframe modes for testing.
