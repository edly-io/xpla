# Python Server PoC for Learning Activity

A FastAPI server simulating an LMS, serving a single learning activity with Extism plugin support.

## Target Structure

```
learning-activity/
  server.py              # Main entry point (PEP 723, runnable with ./server.py)
  runtime.py             # Extism plugin wrapper
  host_functions.py      # Host functions (kv, http, lms)
  lms.py                 # LMS simulation (user, grades)
  capabilities.py        # Manifest enforcement (Phase 6)
  learningactivity.js    # Existing web component
  samples/
    quiz-demo/
      manifest.json      # Activity metadata
      index.html         # Activity page
      activity.js        # Frontend script
      plugin.wasm        # Backend logic (optional)
```

## Implementation Phases

### Phase 1: Static File Server
**Files:** `server.py`

- PEP 723 header with `fastapi`, `uvicorn` dependencies
- Serve static files from project root
- **Validate:** `./server.py` → browse `http://127.0.0.1:8000/` → existing demo works

### Phase 2: Activity Directory Loading
**Files:** `server.py` (modify), `samples/quiz-demo/*` (create)

- Add CLI args: `./server.py [activity_dir]`
- Load `manifest.json` from activity directory
- Serve `./src/lib/learningactivity.js` from project root
- Serve activity files from activity directory
- Add `/api/manifest` endpoint
- **Validate:** `./server.py samples/quiz-demo/` → quiz works, manifest endpoint returns JSON

### Phase 3: Extism Plugin Integration
**Files:** `runtime.py` (create), `server.py` (modify), `build_plugin.py` (create)

- `PluginRuntime` class: load WASM, call functions, context manager
- Add `/api/plugin/{function}` endpoint
- `build_plugin.py`: utility script to compile scripts to WASM
  - Uses Extism PDK (likely Python or JS PDK depending on source language)
  - Accepts source file, outputs `.wasm` in activity directory
- **Validate:** Build a simple plugin from source, POST to endpoint, get result

### Phase 4: Host Functions
**Files:** `host_functions.py` (create), `runtime.py` (modify)

**4a: KV Storage**
- `KVStore` class with disk persistence (JSON file in activity directory)
- `kv_get(key)`, `kv_set(key, value)` host functions
- Register with Extism plugin

**4b: HTTP Requests**
- `http_request(method, url, headers, body)` using `urllib.request`
- No host validation yet (Phase 6)

**Validate:** Create plugin using host functions, verify they work

### Phase 5: LMS Simulation
**Files:** `lms.py` (create), `host_functions.py` (modify), `server.py` (modify)

- `LMSSimulator` class: current user, grade records
- HTTP endpoints: `/api/lms/user`, `/api/lms/grade`, `/api/lms/grades`
- Host functions: `lms_get_user()`, `lms_submit_grade(score, ...)`
- **Validate:** curl endpoints, verify grades persist

### Phase 6: Manifest Enforcement
**Files:** `capabilities.py` (create), `host_functions.py` (modify)

- Parse capabilities from manifest
- `CapabilityChecker` validates: KV namespace/size, HTTP allowed hosts, LMS functions
- Inject checker into host functions
- **Validate:** Restricted manifest rejects unauthorized operations

## Dependencies (PEP 723)

```python
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "fastapi>=0.115.0",
#     "uvicorn[standard]>=0.32.0",
#     "extism>=1.0.0",
# ]
# ///
```

## Key Files to Modify/Create

| File | Phase | Purpose |
|------|-------|---------|
| `server.py` | 1-5 | Main entry, routes, static serving |
| `runtime.py` | 3-4 | Extism plugin wrapper |
| `build_plugin.py` | 3 | Compile scripts to WASM |
| `host_functions.py` | 4-6 | Host function definitions |
| `lms.py` | 5 | LMS simulation |
| `capabilities.py` | 6 | Manifest enforcement |
| `samples/quiz-demo/*` | 2 | Example activity |
