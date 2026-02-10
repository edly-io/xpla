# GULPS Server

This is a proof-of-concept for an upcoming standard (GULPS): similar to standards such as [SCORM](https://en.wikipedia.org/wiki/Sharable_Content_Object_Reference_Model), [LTI](https://en.wikipedia.org/wiki/Learning_Tools_Interoperability) or [XBlock](https://github.com/openedx/xblock).

This project includes a Python server that serves a few sample GULPS activities, along with the documentation for their implementation (right here in this document).

As a high-level overview: the GULPS standard supports running arbitrary code both on the client (for the learner UI) _and_ the server. Server code is sandboxed in WebAssembly. Activities are portable, which means that they can be transferred from one LMS to another. Activities are also secure, as unsafe GULPS capabilities (such as network access) are granted by platform administrators on a case-by-case basis.

Offline portability is also one of the goals of this project, though it is yet unclear how this will be achieved. At this point there are two options:

1. Sandboxed code is shipped to the offline device (typically a mobile phone) and runs there. If the client decompiles the wasm binaries, they have access to the grading logic. This is acceptable when the client is trusted and the sandboxed code does not need network access.
2. Communication between the frontend and the backend is performed in an event-driven architecture  (see [event sourcing](https://martinfowler.com/eaaDev/EventSourcing.html)). When offline, events are delayed until the client comes back online. Conflicts might happen and must be resolved, for instance when users attempt to connect from multiple devices.

At the moment, a limitation of the current approach is the unsafe client code: arbitrary client code can be executed with full access to the DOM, cookies and browser features. This is a strong limitation of HTML which can (at the moment) be bypassed only by using iframes -- which come with their own set of limitations, including in terms of user experience. We intend to give the possibility to platform administrators to sandbox client code in iframes, though this is not implemented yet.

## Comparison with existing standards

| Feature | SCORM | LTI | XBlock | GULPS |
|---------|-------|-----|--------|-------|
| **Portability** | ✅ Excellent – self-contained packages work across any compliant LMS | ⚠️ Limited – protocol connects external tools, but tools aren't packaged or transferable | ❌ None – tightly coupled to Open edX | ✅ Excellent – self-contained packages with explicit capability declarations |
| **Graded assessments** | ❌ Available – but cheating is trivial | ✅ Yes – grade passback via Assignment and Grades Service (LTI 1.3) | ✅ Yes – full grading integration within Open edX | ✅ Yes – sandboxed backend handles grading securely |
| **Sandboxed backend code execution** | ❌ No – client-side JavaScript only | ⚠️ Depends – possible in theory, but servers typically run code unsafely | ⚠️ Unsafe – arbitrary Python with full server access | ✅ Sandboxed – WebAssembly with capability-based permissions |
| **Offline access** | ⚠️ Partial – modules can be downloaded but may require network access at runtime | ❌ No – HTTP server required | ❌ No – connection to an Open edX platform is assumed | ✅ Yes – thanks to event-driven client-to-server communication |

## Installation

Make sure to install the following requirements:

- Python 3.11+
- [extism-js](https://github.com/extism/js-pdk): for building JS plugins to WebAssembly (remember to also install [binaryen](https://github.com/WebAssembly/binaryen))
Then install the project with:

    npm install
    pip install -e .

## Usage

### Viewing sample activities

Build all sample activities with sandboxes:

    make samples

Launch a development server:

    make server

### Creating a new activity

Activities are stored as static files. The [`samples`](./samples) directory contains a few activities that you can use as reference for your own.

NOTE: the exact specifications of activities are currently being defined and are expected to evolve a lot in the very near future.

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
  "values": {},
  "actions": {},
  "events": {}
}
```

- `name` (required): Activity slug, which will be used in quite a few places, including the key/value store, url, etc. Otherwise not user-visible.
- `client` (required): Path to the client-side JavaScript module, relative to `manifest.json`.
- `server` (optional): Path to the server-side WebAssembly sandbox, relative to `manifest.json`. If omitted, the activity has no backend logic.
- `capabilities` (optional, defaults to `{}`): Defines the capabilities that are granted to the sandboxed environment, including: key-value store access, HTTP host requests, LMS functions, AI agents, etc. For more details, check the [`src/server/activities/capabilities.py`](./src/server/activities/capabilities.py) module. At the moment capabilities are not truly enforced, so don't count on them too much...
- `values` (optional, defaults to `{}`): Declares per-user values that the activity tracks. Values are validated at runtime.
- `actions` (optional, defaults to `{}`): Declares actions the client can send to the server sandbox. Each action maps a name to a payload type schema. Validated at runtime.
- `events` (optional, defaults to `{}`): Declares events the server sandbox can emit to the client. `values.change.*` events are implicit and don't need to be declared. Validated at runtime.

The manifest format is defined by a JSON Schema at [`src/sandbox-lib/manifest.schema.json`](./src/sandbox-lib/manifest.schema.json). To validate a manifest:

```bash
./src/tools/validate_manifest.py samples/my-activity/manifest.json
```

##### Values

Each value must have a `type` and `scope` field. An optional `default` can be provided (must match the declared type). Type names follow [JSON Schema](https://json-schema.org/) vocabulary. Example:

```json
{
  "values": {
    "score": { "type": "integer", "scope": "user,unit", "default": 0 },
    "question": { "type": "string", "scope": "unit", "default": "" },
    "answers": { "type": "array", "items": { "type": "string" }, "scope": "unit", "default": [] },
    "correct_answers": { "type": "array", "items": { "type": "integer" }, "scope": "unit", "default": [] }
  }
}
```

**Types:** `integer`, `number`, `string`, `boolean`, `array`, `object`. For `array`, specify an `items` field with a type schema. For `object`, specify a `properties` field. If no `default` is provided, type-specific defaults are used: `0`, `0.0`, `""`, `false`, `[]`, `{}`.

**Scopes:**
- `"user,unit"`: Per-user value, specific to this activity instance. Example: a student's score.
- `"unit"`: Shared value for all users of this activity instance. Example: the question text configured by an instructor.

##### Permissions

Access control is handled at runtime through **permissions** rather than per-value declarations. The platform sets a permission level for each request:

- `"view"`: Read-only / anonymous access. Can see the activity but not interact.
- `"play"`: Active participant (student). Can submit answers.
- `"edit"`: Course author. Can configure the activity.

The sandbox controls what state to expose to the client via an exported `getState()` function, which can check the current permission level using `getPermission()` from the sandbox library. Similarly, the sandbox can guard actions (e.g. reject submissions when permission is `"view"`).

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

Payloads are validated at runtime: sending an undeclared action or emitting an undeclared event raises a validation error. `values.change.*` events are implicit (auto-derived from `values` declarations) and don't need to be declared.

#### Client module (declared via `client` field)

This client-side scripting module will be loaded alongside the `<gulps-activity>` element. This module must export a `setup` function which will be called once the element is ready. The `setup` function receives the `<gulps-activity>` element as its argument, which you can use to inject HTML and add interactivity to your activity.

```javascript
export function setup(activity) {
  // activity is the <gulps-activity> DOM element
  // Inject HTML into the activity
  activity.shadow.innerHTML = `
    <h2>Welcome to my activity!</h2>
    <form>
      <input type="text" name="answer">
      <button type="submit">Submit</button>
    </form>
  `;

  // Add event listeners
  const form = activity.shadow.querySelector("form");
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    ...
  });
}
```

The `activity` object exposes the following properties and methods:

- `values`: An object containing the activity state. Populated by the sandbox's `getState()` function (or all declared values if `getState` is not exported). Updated in-place when `values.change.*` events arrive.
- `permission`: The current permission level (`"view"`, `"play"`, or `"edit"`). Use this to adapt the UI (e.g. hide submit buttons for `"view"`).
- `sendAction(name, value)`: Sends an action to the backend sandbox. Returns the list of events emitted by the sandbox in response. The action name must be declared in `manifest.json`.
- `onValueChange(name, value)`: Override this callback to react to `values.change.*` events from the server.

The `Gulps` class is implemented in [`gulps.js`](./src/server/static/js/gulps.js).

#### Server sandbox (declared via `server` field)

When declared in the manifest, this [WebAssembly](https://webassembly.org/) module will be called as a sandbox from the platform backend. In particular, it is useful for grading assessments: we don't want assessment code to run in the frontend, because it would be trivially vulnerable to cheating.

It is language-agnostic, as the original script can be written in any of the languages supported by WebAssembly. We use [Extism](https://extism.org/) both to build and call these modules. Since Extism supports a wide variety of host languages, sandboxes are portable and can be run from any platform ([Open edX](https://openedx.org/), [Moodle](https://moodle.org), [Canvas](https://canvas.instructure.com/)...).

Note that sandboxes do not persist state. Thus, to get access to configuration settings, user-specific values, etc. the sandbox should have the key-value store read/write capabilities (see `manifest.json` above).

Sandboxes have access to a standard list of host functions. See "host functions" below.

##### Sandbox library

A shared library is available at [`src/sandbox-lib/index.js`](./src/sandbox-lib/index.js) with helper functions for common host function interactions. This library is here for convenience and is not part of the GULPS standard, though it implements good practices. It makes it easier for Javascript authors to avoid dealing with inconvenient WebAssembly data types.

```javascript
import {
  postEvent,
  getPermission,
  getUserId,
  getValue,
  setValue,
  getUserValue,
  setUserValue
} from "../../src/sandbox-lib";

// Post an event to the frontend
postEvent("answer.result", { correct: true });

// Get the current permission level ("view", "play", or "edit")
const permission = getPermission();

// Get current user ID
const userId = getUserId();

// Get/set user-scoped values (scope: "user,unit")
const score = getUserValue("correct_answers");
setUserValue("correct_answers", score + 1);

// Get/set shared values (scope: "unit")
const question = getValue("question");
setValue("question", "What is 2+2?");
```

##### Exported functions

The sandbox script can export the following functions:

- `onAction()`: Called when the frontend sends an action via `activity.sendAction(name, value)`.
- `getState()`: Called when the activity page loads. Returns a JSON string of values to send to the client. Use this to filter values based on the current permission level (e.g., hide correct answers from students). If not exported, the server falls back to sending all declared values.

```javascript
import { getPermission, getValue } from "../../src/sandbox-lib";

function getState() {
  const state = { question: getValue("question") };
  if (getPermission() === "edit") {
    state.correct_answers = getValue("correct_answers");
  }
  Host.outputString(JSON.stringify(state));
}

function onAction() {
  const input = JSON.parse(Host.inputString());
  // Process action...
}

module.exports = { onAction, getState };
```

The `onAction` function is called whenever the frontend sends an action via `activity.sendAction(name, value)`. The sandbox can send events back to the frontend using the `postEvent` helper (which calls the `post_event` host function).

### Building sample activities

```bash
./src/tools/js2wasm.py samples/my-activity/server.js --output samples/my-activity/server.wasm
```

This produces `server.wasm` in the specified output path.

Alternatively, build all samples with:

    make samples

## Project structure

### API endpoints

The server exposes several endpoints which are defined in [./src/server/app.py](./src/server/app.py). These endpoints do not need to be standardized. It is up to each platform to define its own endpoints for client <--> sandbox communication.

### Host Functions

Plugins can call host functions which are defined in [`src/server/activities/context.py`](./src/server/activities/context.py):

<!-- TODO are we actually exposing get_user_id? Should we? -->

- `get_user_id() -> str`
- `get_permission() -> str`
- `post_event(name: str, value: str)`
- `get_value(user_id: str, name: str)`
- `set_value(user_id: str, name: str, value: str)`
- `http_request(url: str, method: str, body: bytes, headers: tuple[tuple[str, str], ...])`

In the future these host functions will be standardized and documented.

## Development

Install requirements:

    pip install -r requirements/dev.in

Run tests:

    make test
