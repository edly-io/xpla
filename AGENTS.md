# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is xPLA

Cross-Platform Learning Activities — a standard for portable, secure online learning activities. Server-side logic runs in WebAssembly sandboxes with capability-based permissions. Activities declare their capabilities, fields, actions, and events in a `manifest.json`.

## Common Commands

```bash
npm install                  # Install JS build tools (esbuild, componentize-js)
pip install -e .[dev]        # Install Python package with dev dependencies

make samples                 # Build all sample sandbox.wasm files
make demo-server             # Run demo FastAPI server (port 9752)
make notebook-server         # Run notebook server (port 9753)
make notebook-frontend-build # Build notebook Next.js frontend

make test                    # Run all tests (lint, unit, types, format, manifests, codegen)
make test-unit               # pytest src/
make test-lint               # pylint src/
make test-types              # mypy src/
make test-format             # black --check src/
make format                  # Format code with black

# Run a single test file or test
pytest src/xpla/lib/tests/test_fields.py
pytest src/xpla/lib/tests/test_fields.py -k test_name

# Regenerate manifest types after schema changes
make manifest-types
```

## Architecture

### Three-layer structure

1. **`src/xpla/lib/`** — Platform-agnostic core library. Contains the `ActivityRuntime`, sandbox execution, field storage, capability checking, and manifest validation. This is the xPLA standard implementation.
2. **`src/xpla/demo/`** — Minimal FastAPI demo app for testing activities with simulated users and permissions.
3. **`src/xpla/notebook/`** — Full courseware app (FastAPI + Next.js) with SQLite persistence (Alembic migrations), course/page/activity management.

### Sandbox execution flow

Activities optionally include server-side logic compiled to WASM Component Model format:

- `samples/*/server.js` → bundled with esbuild → compiled to `server.component.wasm` via `componentize-js`
- WASM components are loaded by `SandboxComponentExecutor` (`src/xpla/lib/sandbox.py`) using the `wasmtime` Python bindings
- Components import host functions from `xpla:sandbox/host` (defined in `xpla.wit`) and export `on-action` and `get-state`
- Host functions (field access, events, HTTP, storage) are provided by `ActivityRuntime` (`src/xpla/lib/runtime.py`)

### Capability system

Activities declare needed capabilities in `manifest.json`. The runtime only exposes host functions for granted capabilities (e.g., `http-request` is only available if `capabilities.http` is declared). Capabilities are validated by `CapabilityChecker` (`src/xpla/lib/capabilities.py`).

### Field system

Fields are typed state declared in `manifest.json`. Each field has a scope (e.g., `user+activity`, `activity`, `course`) that determines its storage key segments. Two field categories: scalar fields (get/set) and log fields (append-only with range queries). `FieldChecker` (`src/xpla/lib/fields.py`) validates field operations. `FieldStore` is the abstract storage backend.

### Manifest types codegen

`src/xpla/lib/manifest_types.py` is auto-generated from `src/xpla/lib/sandbox/manifest.schema.json` via `datamodel-codegen`. Run `make manifest-types` after schema changes. `make test-codegen` verifies types are in sync.

## Code Quality

- Format: `black src/`
- Types: `mypy src/` (strict mode, pydantic plugin)
- Lint: `pylint src/`
- All three must pass — `make test` runs them all
