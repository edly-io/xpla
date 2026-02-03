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
  activity.html
  activity.js
  src/
    sandbox.js
    sandbox.d.ts
```

#### `manifest.json` (required)

```json
{
  "name": "my-activity",
  "capabilities": {},
  "values": {}
}
```

- `name` (required): Activity slug, which will be used in quite a few places, including the key/value store, url, etc. Otherwise not user-visible.
- `capabilities` (optional, defaults to `{}`): Defines the capabilities that are granted to the sandboxed environment, including: key-value store access, HTTP host requests, LMS functions, AI agents, etc. For more details, check the [`src/server/activities/capabilities.py`](./src/server/activities/capabilities.py) module. At the moment capabilities are not truly enforced, so don't count on them too much...
- `values` (optional, defaults to `{}`): Declares per-user values that the activity tracks. Values are validated at runtime.

##### Values

Each value must have a `type` field. An optional `default` can be provided (must match the declared type). Example:

```json
{
  "values": {
    "correct_answers": { "type": "integer", "default": 0 },
    "completion_rate": { "type": "float" },
    "last_answer": { "type": "string" },
    "passed": { "type": "boolean", "default": false }
  }
}
```

Supported types: `integer`, `float`, `string`, `boolean`. If no `default` is provided, type-specific defaults are used: `0`, `0.0`, `""`, `false`.

#### `activity.html` (optional)

If present, the content of this file will be added to the `<gulps-activity>` DOM element inner HTML. This element has two sub-elements:

- `<activity-title>`: which will be displayed as the title of the activity.
- `<activity-content>`: the actual content of the activity.

At the moment, the GULPS activity is added as a [shadow DOM](https://developer.mozilla.org/en-US/docs/Web/API/Web_components/Using_shadow_DOM) element. This means that the rest of the page does not have access to the GULPS element -- but the shadow element does. In other words: we do not have true client-side sandboxing of GULPS activities. We expect to support iframe sandboxing in the future, but this is not the case yet; in addition, not all platforms may want to support iframe-embedded activities, because of the many issues typically associated with iframes.

#### `activity.js` (optional)

If present, this client-side scripting module will be loaded alongside the `<gulps-activity>` element. You can use it to add interactivity to your activity. This module must export a `setup` function which will be called at the moment the element is added to the shadow DOM.

```javascript
export function setup(activity) {
  // activity is the <gulps-activity> DOM element
  const form = activity.querySelector("form");
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    ...
  });
}
```

The `activity` object exposes the following properties and methods:

- `values`: An object containing the current user's values as declared in `manifest.json`. For example, if the manifest declares `correct_answers` and `wrong_answers`, you can access them as `activity.values.correct_answers` and `activity.values.wrong_answers`.
- `callSandboxFunction(name, body)`: Calls a function in the backend sandbox. This is particularly useful for submitting student responses to an assessment.

The `Gulps` class is implemented in [`gulps.js`](./src/server/static/js/gulps.js).

Note: this pattern is likely to evolve in the near future. We might trade arbitrary sandboxed function calling with a more classical event-driven architecture.

#### `sandbox.wasm` (optional)

If present, this is a [WebAssembly](https://webassembly.org/) module that will be called as a sandbox from the platform backend. In particular, it is useful for grading assessments: we don't want assessment code to run in the frontend, because it would be trivially vulnerable to cheating.

It is language-agnostic, as the original script can be written in any of the languages supported by WebAssembly. We use [Extism](https://extism.org/) both to build and call these modules. Since Extism supports a wide variety of host languages, sandboxes are portable and can be run from any platform ([Open edX](https://openedx.org/), [Moodle](https://moodle.org), [Canvas](https://canvas.instructure.com/)...).

Note that sandboxes do not persist state. Thus, to get access to configuration settings, user-specific values, etc. the sandbox should have the key-value store read/write capabilities (see `manifest.json` above).

Sandboxes have access to a standard list of host functions. See "host functions" below.

##### Exported functions

The sandbox script must export an `onEvent` function to receive events from the frontend:

```javascript
// Input: JSON { "name": "...", "value": "..." }
function onEvent() {
  const input = JSON.parse(Host.inputString());
  const eventName = input.name;
  const eventValue = input.value;

  // Process event...

  Host.outputString(JSON.stringify({ processed: true }));
}

module.exports = { onEvent };
```

The `onEvent` function is called whenever the frontend sends an event via `activity.sendEvent(name, value)`. The sandbox can send events back to the frontend using the `post_event` host function.

### Building sample activities

```bash
./src/tools/js2wasm.py samples/my-activity/src/sandbox.js --output samples/my-activity/sandbox.wasm
```

This produces `sandbox.wasm` in the specified output path.

Alternatively, build all samples with:

    make samples

## Project structure

### API endpoints

The server exposes several endpoints which are defined in [./src/server/app.py](./src/server/app.py). These endpoints do not need to be standardized. It is up to each platform to define its own endpoints for client <--> sandbox communication.

### Host Functions

Plugins can call host functions which are defined in [`src/server/activities/context.py`](./src/server/activities/context.py). In the future these host functions will be standardized and documented.

## Development

Install requirements:

    pip install -r requirements/dev.in

Run tests:

    make test