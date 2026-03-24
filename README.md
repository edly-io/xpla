# Cross-Platform Learning Activities (xPLA)

xPLA is an upcoming standard for online learning activities. It aims at improving other standards such as [SCORM](https://en.wikipedia.org/wiki/Sharable_Content_Object_Reference_Model), [LTI](https://en.wikipedia.org/wiki/Learning_Tools_Interoperability), [H5P](https://h5p.org) or [XBlock](https://github.com/openedx/xblock).

As a high-level overview: the xPLA standard supports running arbitrary code both on the client (for the learner UI) _and_ the server. Server code is sandboxed in WebAssembly. Activities are portable, which means that they can be transferred from one LMS to another. Activities are also secure, as unsafe xPLA capabilities (such as network access) are granted by platform administrators on a case-by-case basis.

Offline mode is supported, with two possible options:

1. Sandboxed code is shipped to the offline device (typically a mobile phone) and runs there. If the client decompiles the wasm binaries, they have access to the grading logic. This is acceptable when the client is trusted and the sandboxed code does not need network access.
2. Communication between the frontend and the backend is performed in an event-driven architecture  (see [event sourcing](https://martinfowler.com/eaaDev/EventSourcing.html)). When offline, events are delayed until the client comes back online. Conflicts might happen and must be resolved, for instance when users attempt to connect from multiple devices.

## Sub-projects

| Directory | Description |
|-----------|-------------|
| [src/xpla/lib/](./src/xpla/lib/) | **Core library.** Platform-agnostic runtime for loading activities, validating manifests, executing WebAssembly sandboxes, and managing field storage. Also contains the full [Activity API](./src/xpla/lib/README.md#activity-api-reference) and [Platform API](./src/xpla/lib/README.md#platform-api-reference) reference documentation. Refer to this project for more information about the standard. |
| [src/xpla/demo/](./src/xpla/demo/) | **Demo server.** Minimal FastAPI app that serves sample activities with a toolbar for switching users, permissions, and embedding modes. Useful for development and testing. |
| [src/xpla/notebook/](./src/xpla/notebook/) | **Notebook application.** Full courseware management app (FastAPI + Next.js) for organizing courses, pages, and activities with drag-and-drop, real-time execution, and SQLite persistence. |
| [samples/](./samples/) | **Sample activities.** Reference xPLA activities (MCQ, quiz, video, chat, etc.) that demonstrate the standard. |
| [src/xpla/lib/sandbox/](./src/xpla/lib/sandbox/) | **Sandbox definition.** WIT interface and JSON Schema for the WASM Component Model sandbox. |
| [src/xpla/static/](./src/xpla/static/) | **Shared static files.** The `XPLA` base class ([xpla.js](./src/xpla/static/js/xpla.js)) that powers the `<xpl-activity>` web component. |

## Installation

Make sure to install the following requirements:

- Python 3.11+
- [jco](https://github.com/bytecodealliance/jco): for building JS plugins to WebAssembly components (`npm install -g @anthropic-ai/jco` or use via `npx jco`)

Then install the project with:

    npm install
    pip install -e .

## Quick Start

Build all sample activities with sandboxes:

    make samples

Launch the demo server:

    make demo-server

Then open http://127.0.0.1:9752 in a browser.

## Development

Install requirements:

    pip install -e .[dev]

Run tests:

    make test
