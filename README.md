# Learning Activity Server

A Python server for developing and testing interactive learning activities with WebAssembly plugin support.

# Installation

Make sure to install the following requirements:

- Python 3.11+
- [extism-js](https://github.com/extism/js-pdk): for building JS plugins to WebAssembly (remember to also install [binaryen](https://github.com/WebAssembly/binaryen))

Then install the project with:

    pip install -e .

# Usage

## Viewing sample activities

Build all sample activities with sandboxes:

    make samples

Launch a development server:

    make server

## Creating a new activity

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

### `manifest.json` (required)

```json
{
  "name": "my-activity",
  "capabilities": {}
}
```

- `name` (required): Activity slug, which will be used in quite a few places, including the key/value store, url, etc. Otherwise not user-visible.
- `capabilities` (optional, defaults to `{}`): Defines the capabilities that are granted to the sandboxed environment, incuding: key-value store access, HTTP host requests, LMS functions, AI agents, etc. For more details, check the [`src/server/activities/capabilities.py`](./src/server/activities/capabilities.py) module.

### `activity.html` (optional)

If present, the content of this file will be added to the `<learning-activity>` DOM element inner HTML. This element has two sub-elements:

- `<activity-title>`: which will be displayed as the title of the activity.
- `<activity-content>`: the actual content of the activity.

At the moment, the learning activity is added as a [shadow DOM](https://developer.mozilla.org/en-US/docs/Web/API/Web_components/Using_shadow_DOM) element. This means that the rest of the page does not have access to the learning activity element -- but the shadow element does. In other words: we do not have true client-side sandboxing of learning activities. We expect to support iframe sandboxing in the future, but this is not the case yet; in addition, not all platforms might want to support iframe-embedded activities, because of the many issues typically associated with iframes. 

### `activity.js` (optional)

If present, this client-side scripting module will be loaded alongside the `<learning-activity>` element. You can use it to add interactivity to your activity. This module must export a `setup` function which will be called at the moment the element is added to the shadow DOM.

```javascript
export function setup(activity) {
  // activity is the <learning-activity> DOM element
  const form = activity.querySelector("form");
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    ...
  });
}
```

The `Activity` class is implemented in [`learningactivity.js`](./src/server/static/js/learningactivity.js). Note in particular the presence of a `callSandboxFunction` method which allows arbitrary calling of backend, sandboxed functions from the frontend. This is particularly useful to submit student responses to an assessment. 

Note: this pattern is likely to evolve in the near future. We might trade arbitrary sandboxed function calling with a more classical event-driven architecture.

### `sandbox.wasm` (optional)

If present, this is a [WebAssembly](https://webassembly.org/) module that will be called as a sandbox from the platform backend. In particular, it is particularly useful for submission assessments: we don't want assessment code to run in the frontend, because it would then be trivially vulnerable to cheating. 

It is language-agnostic, as the original script can be written in any of the languages supported by WebAssembly. We use [Extism](https://extism.org/) both to build and call these modules. Since Extism supports a wide variety of host languages, that sandboxes are portable and can be run from any platform ([Open edX](https://openedx.org/), [Moodle](https://moodle.org), [Canvas](https://canvas.instructure.com/)...).

Note that sandboxes do not persist state. Thus, to get access to configuration settings, user-specific values, etc. the sandbox should have the key-value store read/write capabilities (see `manifest.json` above).

Sandboxes have access to a standard list of host functions. See "host functions" below.

## Building sample activities

```bash
./src/tools/js2wasm.py samples/my-activity/src/sandbox.js --output samples/my-activity/sandbox.wasm
```

This produces `plugin.wasm` in the same directory.

Alternatively, build all samples with:

    make samples

# Project structure

## API endpoints

The server exposes several endpoints which are defined in [./src/server/app.py](./src/server/app.py). These endpoints do not need to be standardized. It is up to each platform to define its own endpoints for client <--> sandbox communication.

## Host Functions

Plugins can call host functions which are defined in [`src/server/activities/context.py`](./src/server/activities/context.py). In the future these host functions will be standardized and documented.

# Development

Install requirements:

    pip install -r requirements/dev.in

Run tests:

    make test