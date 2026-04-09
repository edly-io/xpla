# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this directory.

See [README.md](./README.md) for the full architecture and simulation features.

## Commands

```bash
make samples       # Build sample WASM modules (required once before running)
make demo-server   # FastAPI dev server on port 9752

pytest src/xpla/demo/   # Unit tests
```

## Key Patterns

- **Simulated users**: alice, bob, charlie — selected via `xpla_user` cookie. Permission level via `xpla_permission` cookie. Both read in `get_simulation_params()`.
- **Field persistence**: `KVStore` in `kv.py` extends `MemoryKVStore` with JSON-file backing (`dist/kv.json`). Every write flushes to disk.
- **No database**: unlike the notebook app, the demo has no DB or migrations. All state lives in the JSON file.
- **Activity loading**: each request creates a fresh `ActivityRuntime` from `samples/{activity_type}/manifest.json`. The `activity_id` and `course_id` are hardcoded (`activity_type` and `"democourse"`).
- **Test isolation**: the `conftest.py` fixture patches `field_store` with a temp `KVStore` per test.
