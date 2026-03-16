# Cross-Platform Learning Activities (xPLA)

This is a proof-of-concept for xPLA (temporary name), an upcoming standard which aims at being an improvement over other similar standards such as [SCORM](https://en.wikipedia.org/wiki/Sharable_Content_Object_Reference_Model), [LTI](https://en.wikipedia.org/wiki/Learning_Tools_Interoperability) or [XBlock](https://github.com/openedx/xblock).

This project includes a Python server that serves a few sample xPLA activities, along with the documentation for their implementation (right here in this document).

As a high-level overview: the xPLA standard supports running arbitrary code both on the client (for the learner UI) _and_ the server. Server code is sandboxed in WebAssembly. Activities are portable, which means that they can be transferred from one LMS to another. Activities are also secure, as unsafe xPLA capabilities (such as network access) are granted by platform administrators on a case-by-case basis.

Offline mode is supported, with two possible options:

1. Sandboxed code is shipped to the offline device (typically a mobile phone) and runs there. If the client decompiles the wasm binaries, they have access to the grading logic. This is acceptable when the client is trusted and the sandboxed code does not need network access.
2. Communication between the frontend and the backend is performed in an event-driven architecture  (see [event sourcing](https://martinfowler.com/eaaDev/EventSourcing.html)). When offline, events are delayed until the client comes back online. Conflicts might happen and must be resolved, for instance when users attempt to connect from multiple devices.

## Comparison with existing standards

| Feature | SCORM | LTI | XBlock | H5P | xPLA |
|---------|-------|-----|--------|-----|-------|
| **Portability** | ✅ Excellent – self-contained packages work across any compliant LMS | ⚠️ Limited – protocol connects external tools, but tools aren't packaged or transferable | ❌ None – tightly coupled to Open edX | ✅ Good – `.h5p` packages work across compatible platforms (Moodle, WordPress, Drupal) | ✅ Excellent – self-contained packages with explicit capability declarations |
| **Graded assessments** | ❌ Available – but cheating is trivial | ✅ Yes – grade passback via Assignment and Grades Service (LTI 1.3) | ✅ Yes – full grading integration within Open edX | ⚠️ Available – grade passback via xAPI, but grading logic runs client-side | ✅ Yes – sandboxed backend handles grading securely |
| **Sandboxed backend code execution** | ❌ No – client-side JavaScript only | ⚠️ Depends – possible in theory, but servers typically run code unsafely | ⚠️ Unsafe – arbitrary Python with full server access | ❌ No – client-side JavaScript only | ✅ Sandboxed – WebAssembly with capability-based permissions |
| **Offline access** | ⚠️ Partial – modules can be downloaded but may require network access at runtime | ❌ No – HTTP server required | ❌ No – connection to an Open edX platform is assumed | ⚠️ Partial – possible via Lumi desktop app, not in standard LMS integrations | ✅ Yes – thanks to event-driven client-to-server communication |

## Limitations

What follows is a list of limitations of the current implementation. In some cases we are actively working to address them.

### Unsafe client code

The preferred mode for running xPLA on the client is using [shadow DOM](https://developer.mozilla.org/en-US/docs/Web/API/Web_components/Using_shadow_DOM). This prevents access to the xPLA from the rest of the DOM, but the reverse is not true: the xPLA can access the rest of the DOM and break it. To avoid this situation, platform administrators can decide to embed xPLA within iframes, which is the only safe mechanism to sandbox HTML (at the moment). But iframes come with their own set of limitations. See [Recommendations](#recommendations-1) in the Frontend API section below.

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

## Installation

Make sure to install the following requirements:

- Python 3.11+
- [extism-js](https://github.com/extism/js-pdk): for building JS plugins to WebAssembly (remember to also install [binaryen](https://github.com/WebAssembly/binaryen))

Then install the project with:

    npm install
    pip install -e .

## Usage

Build all sample activities with sandboxes:

    make samples

Launch a development server:

    make server

Then open http://127.0.0.1:9752 in a browser.

The server is a demo of a few sample activities, including, among others:

- [Markdown-formatted section](./samples/mcq)
- [Python programming graded exercise](./samples/python)
- [HTML5 video module](./samples/video)
- [YouTube video module](./samples/youtube)
- [Multiple choice question (MCQ) graded exercise](./samples/mcq)

The UI allows users to switch between student and teacher interfaces (with different permissions: view = anonymous user, play = student, edit = author), native and iframe embedding modes.

## Development

Install requirements:

    pip install -e .[dev]

Run tests:

    make test

## Reference

⚠️ This is a work-in-progress. The exact xPLA specifications are currently being defined and are expected to evolve a lot in the very near future.

This section covers the Activity API (for course authors and activity developers) and the Platform API (for LMS platform developers).

### Activity API

This reference is aimed at course authors to create new xPLA packages. We suggest to leverage generative AI to create new packages: when this documentation and sample activities are provided as context, coding LLM typically generate working xPLA in a single shot.

Activities are stored as static files. The [`samples`](./samples) directory contains a few activities that you can use as reference for your own.

The typical file hierarchy of an activity is the following:

```
my-activity/
  manifest.json
  client.js
  server.js
```

#### `manifest.json` (required)

```json
{
  "name": "my-activity",
  "client": "client.js",
  "server": "server.wasm",
  "capabilities": {},
  "fields": {},
  "actions": {},
  "events": {}
}
```

- `name` (required): Activity slug, which will be used in quite a few places, including the key/value store, url, etc. Otherwise not user-visible.
- `client` (required): Path to the client-side JavaScript module, relative to `manifest.json`.
- `server` (optional): Path to the server-side WebAssembly sandbox, relative to `manifest.json`. If omitted, the activity has no backend logic.
- `capabilities` (optional, defaults to `{}`): Defines the capabilities that are granted to the sandboxed environment, including: key-value store access, HTTP host requests, LMS functions, AI agents, etc. For more details, check the [`src/xpla/capabilities.py`](./src/xpla/capabilities.py) module. At the moment capabilities are not truly enforced, so don't count on them too much...
- `fields` (optional, defaults to `{}`): Declares activity fields with type and scope. Fields are validated at runtime.
- `actions` (optional, defaults to `{}`): Declares actions the client can send to the server sandbox. Each action maps a name to a payload type schema. Validated at runtime.
- `events` (optional, defaults to `{}`): Declares events the server sandbox can emit to the client. Validated at runtime.
- `static` (optional): An array of explicit file paths that can be served as static assets. Only listed files (plus `client` and `manifest.json`) are accessible. Paths must be relative (no leading `/`) and cannot contain `..`.

The manifest format is defined by a JSON Schema at [`src/sandbox-lib/manifest.schema.json`](./src/sandbox-lib/manifest.schema.json). To validate a manifest:

```bash
./src/tools/validate_manifest.py samples/my-activity/manifest.json
```

##### Fields

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

**Types:** `integer`, `number`, `string`, `boolean`, `array`, `object`, `log`. For `array` and `log`, specify an `items` field with a type schema. For `object`, specify a `properties` field. If no `default` is provided, type-specific defaults are used: `0`, `0.0`, `""`, `false`, `[]`, `{}`. Log fields have no default and are not included in `get_field`/`set_field` or `get_all_fields` — they are accessed exclusively via the [log host functions](#log-fields).

**Scopes:**

| Scope | Description | Example |
|---|---|---|
| `"activity"` | Shared across users, scoped to this activity instance. | Question text configured by an instructor. |
| `"user,activity"` | Per-user, scoped to this activity instance. | A student's score. |
| `"course"` | Shared across users, scoped to the course. | Course-wide leaderboard. |
| `"user,course"` | Per-user, scoped to the course. | Cumulative course grade. |
| `"global"` | Shared across users, global to the platform. | Internal API key. |
| `"user,global"` | Per-user, global to the platform. | User language preference. |

##### Permissions

Access control is handled at runtime through **permissions** rather than per-field declarations. The platform sets a permission level for each request:

- `"view"`: Read-only / anonymous access. Can see the activity but not interact.
- `"play"`: Active participant (student). Can submit answers.
- `"edit"`: Course author. Can configure the activity.

The sandbox controls what state to expose to the client via an exported `getState()` function, which receives the current permission level as input. Similarly, the sandbox can guard actions using the `permission` value included in the `onAction` input (e.g. reject submissions when permission is `"view"`).

##### Actions & Events

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

#### Client module (declared via `client` field)

This client-side scripting module will be loaded alongside the `<xpl-activity>` element. This module must export a `setup` function which will be called once the element is ready. The `setup` function receives the `<xpl-activity>` element as its argument, which you can use to inject HTML and add interactivity to your activity.

```javascript
export function setup(activity) {
  // activity is the <xpl-activity> DOM element
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
- `state`: An object containing the activity state. Populated by the sandbox's `getState()` function (or all declared fields if `getState` is not exported).
- `permission`: The current permission level (`"view"`, `"play"`, or `"edit"`). Use this to adapt the UI (e.g. hide submit buttons for `"view"`).
- `sendAction(name, value)`: Sends an action to the backend sandbox. Returns the list of events emitted by the sandbox in response. The action name must be declared in `manifest.json`.
- `getAssetUrl(path)`: Returns the URL for a static file in the activity directory (served by the `activity_asset` endpoint).
- `onEvent(name, value)`: Override this callback to handle events from the server. Called for every event with the parsed value.

The `XPLA` class is implemented in [`xpla.js`](./src/static/js/xpla.js).


#### Server sandbox (declared via `server` field)

When declared in the manifest, this [WebAssembly](https://webassembly.org/) module will be called as a sandbox from the platform backend. In particular, it is useful for grading assessments: we don't want assessment code to run in the frontend, because it would be trivially vulnerable to cheating.

It is language-agnostic, as the original script can be written in any of the languages supported by WebAssembly. We use [Extism](https://extism.org/) both to build and call these modules. Since Extism supports a wide variety of host languages, sandboxes are portable and can be run from any platform ([Open edX](https://openedx.org/), [Moodle](https://moodle.org), [Canvas](https://canvas.instructure.com/)...).

Note that sandboxes do not persist state. Thus, to get access to configuration settings, user-specific fields, etc. the sandbox should have the key-value store read/write capabilities (see `manifest.json` above).

Sandboxes have access to a standard list of host functions. See [Host functions](#host-functions) in the Platform API section below.

##### Sandbox library

A shared library is available at [`src/sandbox-lib/index.js`](./src/sandbox-lib/index.js) with helper functions for common host function interactions. This library is here for convenience and is not part of the xPLA standard, though it implements good practices. It makes it easier for Javascript authors to avoid dealing with inconvenient WebAssembly data types.

```javascript
import {
  sendEvent,
  getField, setField,
  logAppend, logGet, logGetRange, logDelete, logDeleteRange,
} from "../../src/sandbox-lib";

// Send an event to all connected clients in the current activity
// sendEvent(name, value, scope, permission)
//   scope: {} = current activity (default), or e.g. { user_id: "alice" } to target a specific user
//   permission: minimum permission to receive the event ("view", "play", or "edit")
sendEvent("answer.result", { correct: true }, {}, "play");

// Get/set fields (scope is resolved automatically from manifest)
const score = getField("correct_answers");
setField("correct_answers", score + 1);

const question = getField("question");
setField("question", "What is 2+2?");

// Get/set fields for a different user via scope overrides
const studentScore = getField("score", { user_id: "student123" });
setField("score", studentScore + 1, { user_id: "student123" });

// Log field operations (append-only ordered data)
const id = logAppend("messages", { user: "alice", text: "hello" });
const entry = logGet("messages", id);       // { user: "alice", text: "hello" }
const all = logGetRange("messages", 0, 100); // [{ id: 0, value: {...} }, ...]
logDelete("messages", id);                   // true
logDeleteRange("messages", 0, 50);           // returns count deleted
```

##### Exported functions

The sandbox script can export the following functions:

- `onAction()`: Called when the frontend sends an action via `activity.sendAction(name, value)`. The input is a JSON object with four keys: `name` (the action name), `value` (the action payload), `scope` (a dict with `user_id`, `course_id`, `activity_id` identifying the current context), and `permission` (the current permission level: `"view"`, `"play"`, or `"edit"`).
- `getState()`: Called when the activity page loads. The input is a JSON object with two keys: `scope` (a dict with `user_id`, `course_id`, `activity_id`) and `permission` (the current permission level). Returns a JSON string of fields to send to the client. Use this to filter fields based on permission (e.g., hide correct answers from students). If not exported, the server falls back to sending all declared fields.

```javascript
import { getField } from "../../src/sandbox-lib";

function getState() {
  const { permission } = JSON.parse(Host.inputString());
  const state = { question: getField("question") };
  if (permission === "edit") {
    state.correct_answers = getField("correct_answers");
  }
  Host.outputString(JSON.stringify(state));
}

function onAction() {
  const { name, value, scope, permission } = JSON.parse(Host.inputString());
  // name: action name (e.g. "answer.submit")
  // value: action payload
  // scope.user_id: current user ID
  // scope.course_id: current course ID
  // scope.activity_id: current activity instance ID
  // permission: "view", "play", or "edit"
}

module.exports = { onAction, getState };
```

The `onAction` function is called whenever the frontend sends an action via `activity.sendAction(name, value)`. The sandbox can send events back to connected clients using `sendEvent(name, value, scope, permission)` (which calls the `send_event` host function). The `scope` argument controls which clients receive the event (e.g. `{}` for the whole activity, `{user_id: "alice"}` for a specific user), and `permission` sets the minimum permission level required to receive it.

#### Building

We provide here a convenience script that makes it easy to build server-side code to WebAssembly.

```bash
./src/tools/js2wasm.py samples/my-activity/server.js --output samples/my-activity/server.wasm
```

This produces `server.wasm` in the specified output path.

Alternatively, build all samples with:

    make samples

### Platform API

This section is aimed at LMS platform developers who want to integrate xPLA activities into their platform.

#### Backend API

The backend is responsible for loading activities, executing sandboxed code, providing host functions, and mediating communication between the frontend and the sandbox.

##### Core responsibilities

1. **Manifest validation.** Parse and validate each activity's `manifest.json` against the [JSON Schema](./src/sandbox-lib/manifest.schema.json). This includes validating the declared fields, actions, events, capabilities, and static assets.

2. **Sandbox execution.** Load the WebAssembly module declared in `manifest.server` and execute its exported functions (`getState`, `onAction`). We recommend using [Extism](https://extism.org/), which provides plugin runtimes for many host languages (Python, Go, Rust, Java, etc.).

3. **Host functions.** The sandbox runtime must inject a set of host functions that sandboxed code can call. These are documented in the [Host functions](#host-functions) section below. Our implementation is in [`src/xpla/context.py`](./src/xpla/context.py).

4. **Runtime validation.** Actions sent by the frontend and events emitted by the sandbox must be validated against the manifest declarations. Our implementation: [`src/xpla/actions.py`](./src/xpla/actions.py) (actions), [`src/xpla/events.py`](./src/xpla/events.py) (events), [`src/xpla/fields.py`](./src/xpla/fields.py) (fields).

5. **Key-value store.** Activity fields are persisted in a key-value store, scoped by activity name and (for user-scoped fields) user ID. The store must support `get` and `set` operations. Our implementation: [`src/xpla/kv.py`](./src/xpla/kv.py).

6. **Static asset serving.** Serve files declared in the manifest's `static` array (plus `client` and `manifest.json`). Paths must be validated to prevent directory traversal.

##### Endpoints

The exact API is platform-specific and does not need to follow a standard. The platform must support:

- **Get state**: called on page load. The backend calls the sandbox's `getState()` function and returns the result as JSON. If `getState` is not exported, all declared fields are returned.
- **Send action**: called when the frontend sends an action via `sendAction(name, value)`. The backend validates the action, then calls the sandbox's `onAction()` function with a JSON input containing `name`, `value`, `scope` (a dict with `user_id`, `course_id`, `activity_id`), and `permission` (the current permission level).
- **Event delivery**: events emitted by the sandbox (via `send_event`) are broadcast to connected clients via WebSocket, filtered by scope and permission. The platform maintains a WebSocket connection per client and routes events to matching subscribers.

Our implementation exposes these as FastAPI endpoints in [`src/xplademo/app.py`](./src/xplademo/app.py). Event routing is handled by the [`EventBus`](./src/xpla/event_bus.py).

##### Host functions

Plugins can call host functions which are defined in [`src/xpla/context.py`](./src/xpla/context.py):

- `send_event(name: str, value: str, scope: str, permission: str)`: `scope` is a JSON-encoded dict controlling broadcast audience (e.g. `'{"activity_id": "..."}'` or `'{}'` for defaults). `permission` is the minimum permission level to receive the event (`"view"`, `"play"`, or `"edit"`)
- `get_field(name: str, scope: str)` / `set_field(name: str, value: str, scope: str)`: scope resolved from manifest; the `scope` parameter is a JSON-encoded dict of dimension overrides, with the following optional keys: `user_id`, `course_id`, `activity_id`. E.g. `{"user_id": "bob"}`. Pass `{}` for default behavior. Raises `FieldValidationError` on `log` fields — use the log functions below instead
- `log_append(name: str, value: any, scope: str) -> int`: append to a log field, returns the assigned entry ID
- `log_get(name: str, entry_id: int, scope: str) -> any | null`: get a single log entry by ID
- `log_get_range(name: str, from_id: int, to_id: int, scope: str) -> [{id, value}, ...]`: get entries in range `[from_id, to_id)`
- `log_delete(name: str, entry_id: int, scope: str) -> bool`: delete a single entry, returns whether it existed
- `log_delete_range(name: str, from_id: int, to_id: int, scope: str) -> int`: delete entries in range, returns count deleted
- `http_request(url: str, method: str, body: bytes, headers: tuple[tuple[str, str], ...])` → `{"status": int, "headers": [[k,v],...], "body": str}`
- `submit_grade(score: float)`

##### Log fields

The `log` type provides append-only ordered storage with auto-incrementing IDs, suitable for chat messages, event histories, and similar use cases. Unlike other field types, log fields are not accessible via `get_field`/`set_field` and are not included in `get_all_fields` — they have dedicated host functions (`log_append`, `log_get`, `log_get_range`, `log_delete`, `log_delete_range`).

Log fields cannot be nested: the `items` type schema uses the same types as other fields (`integer`, `number`, `string`, `boolean`, `array`, `object`) but not `log`.

**Internal storage format.** The reference implementation stores each log as a single KV entry with the structure `{"next_id": N, "entries": {"0": val, "1": val, ...}}`. This is adequate for small to medium logs.

**SQL implementation guidance.** For production platforms, logs should be backed by a SQL table rather than a single KV blob. A suggested schema:

```sql
CREATE TABLE xpla_log_entries (
    field_key  TEXT NOT NULL,   -- same scoped key as other fields
    entry_id   INTEGER NOT NULL,
    value      JSONB NOT NULL,
    PRIMARY KEY (field_key, entry_id)
);
```

With this table, `log_append` becomes an `INSERT` with a `SELECT max(entry_id) + 1`, `log_get` is a simple `SELECT ... WHERE entry_id = ?`, `log_get_range` is `SELECT ... WHERE entry_id >= ? AND entry_id < ? ORDER BY entry_id`, and `log_delete`/`log_delete_range` are `DELETE` statements. A separate sequence or `max + 1` query provides the next ID. This representation scales well and supports efficient range queries via the primary key index.

See the [`samples/chat`](./samples/chat) activity for a working example.

##### Recommendations

- **Use Extism for sandbox execution.** Extism provides a consistent plugin API across many host languages and handles WebAssembly loading, memory management, and host function binding. See [`src/xpla/sandbox.py`](./src/xpla/sandbox.py).
- **Validate everything at runtime.** Don't trust that activity code will send well-formed actions or events. Validate action names and payloads against the manifest before calling the sandbox, and validate events before forwarding them to the frontend.
- **Scope KV keys carefully.** We use the pattern `xpla.<activity_name>.<course_id>.<activity_id>.<user_id>.<value_name>` to prevent activities from interfering with each other's state. Depending on the scope, some segments are empty (e.g., for platform-scoped values, course_id and activity_id are empty).

#### Frontend API

This section is aimed at LMS platform developers who want to render xPLA activities in their frontend. The platform must provide a runtime component that loads the activity's client script and exposes a standard API to it.

##### Activity component API

The runtime must provide an `activity` object to each activity's `setup(activity)` function. This object is the sole interface between the activity client code and the platform. It must expose:

| Property / Method | Type | Description |
|---|---|---|
| `element` | DOM element | The root DOM element where the activity renders its UI. |
| `state` | `object` | The activity state, populated by the backend's `getState()` response. |
| `permission` | `string` | Current permission level: `"view"`, `"play"`, or `"edit"`. |
| `sendAction(name, value)` | `(string, any) => void` | Sends an action to the backend sandbox via WebSocket. Fire-and-forget: events are delivered asynchronously through the `onEvent` callback. |
| `getAssetUrl(path)` | `(string) => string` | Returns the URL for a static asset declared in the activity's manifest. |
| `onEvent(name, value)` | `(string, any) => void` | Callback invoked for every event emitted by the server. Default is a no-op; activity code overrides it. |

##### Loading flow

1. The backend calls the sandbox's `getState()` function (if exported) to obtain the initial state for the current user and permission level. If `getState` is not exported, all declared values are returned.
2. The platform renders the activity component, passing it the initial state and permission level.
3. The runtime loads the activity's client script (declared in `manifest.client`) and calls its exported `setup(activity)` function.

##### Event processing

Events are delivered in real time via a WebSocket connection established on page load. When the server broadcasts an event (filtered by scope and permission), the runtime calls `activity.onEvent(name, parsedValue)`. All events are treated uniformly — the activity's `onEvent` handler is responsible for updating `activity.state` or performing any other side effects as needed. This enables multi-user scenarios (e.g. chat) where actions by one user produce events visible to all connected clients.

##### Recommendations

- **Use a custom element.** Our implementation uses a [Web Component](https://developer.mozilla.org/en-US/docs/Web/API/Web_components) (`<xpl-activity>`), which provides a clean encapsulation boundary and works with any framework. See [`src/static/js/xpla.js`](./src/static/js/xpla.js).
- **Pass initial state as a data attribute.** We serialize the state JSON into a `data-state` attribute and the permission into `data-permission`. This avoids extra round-trips. See [`src/xplademo/templates/activity.html`](./src/xplademo/templates/activity.html).
- **Support both shadow DOM and iframe embedding.** Shadow DOM provides style encapsulation with lower overhead; iframes provide full isolation. The `<xpl-activity>` element supports an `embed` attribute that controls how the activity is rendered:
  - **`shadow`** (default): The activity runs inside a closed shadow DOM. This provides style encapsulation — activity CSS won't leak into the host page and vice versa — but doesn't fully isolate the activity from the parent document.
  - **`native`**: No shadow DOM. The activity renders directly into a wrapper `<div>`. Intended for use inside iframes, where the iframe boundary provides full isolation. In this mode, `adoptedStyleSheets` on `activity.element` is shimmed to delegate to `document.adoptedStyleSheets`, so activity code (e.g. Plyr CSS injection) works without changes.

In native/iframe mode, the element sends `postMessage` events to the parent window:

- `{ type: "xpla:ready" }`: sent after setup completes.
- `{ type: "xpla:resize", height: <number> }`: sent whenever the wrapper div resizes (via `ResizeObserver`), so the parent can auto-size the iframe.

Each activity has a standalone embed page at `/a/{name}/embed` that uses `<xpl-activity embed="native" ...>`. To embed an activity in an iframe:

```html
<iframe src="/a/math/embed" style="width: 100%; border: none;"></iframe>
```

The development server toolbar includes an "Embed" dropdown to toggle between shadow DOM and iframe modes for testing.
