# xplademo — Demo Server

xplademo is a minimal LMS simulation that demonstrates how to integrate [xPLA](../xpla/) activities into a platform. It serves sample activities with a development toolbar for testing different users, permissions, and embedding modes.

## Running

From the project root:

```bash
make samples    # Build all sample activity WASM modules (required once)
make xplademo   # Start dev server on port 9752
```

Then open http://127.0.0.1:9752 in a browser.

## Sample Activities

The server loads activities from the [`samples/`](../../samples) directory. Each subdirectory with a `manifest.json` is listed on the home page. Examples include:

- [Markdown-formatted section](../../samples/section)
- [Multiple choice question (MCQ)](../../samples/mcq)
- [Python programming exercise](../../samples/python)
- [HTML5 video](../../samples/video)
- [YouTube video](../../samples/youtube)

## Simulation Features

The UI toolbar allows testing without redeploying:

- **User switching** (alice, bob, charlie) — simulates different learners via cookies
- **Permission levels** (view, play, edit) — controls what the activity can do
- **Embedding modes** — toggle between shadow DOM and iframe rendering

## Architecture

The server is a single FastAPI application. Key files:

- [app.py](./app.py) — routes: activity pages, action endpoint, WebSocket, asset serving
- [kv.py](./kv.py) — `KVFieldStore`: JSON-file-backed field persistence (stores at `dist/kv.json`)
- [templates/](./templates/) — Jinja2 templates (home page, activity page, iframe embed page)

For each request, the server creates an xPLA `ActivityContext` that loads the manifest, executes the WASM sandbox, and routes events through the `EventBus`.
