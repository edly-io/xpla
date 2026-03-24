REPO_ROOT := ../..
WIT := $(REPO_ROOT)/src/xpla/lib/sandbox/xpla.wit

build: server.component.wasm

server.component.wasm: $(WIT) server.py
	componentize-py --wit-path=$(WIT) --world=activity componentize --output server.component.wasm server

# Generate bindings to better integrate with the IDE.
bindings: $(WIT)
	rm -rf ./bindings
	componentize-py --wit-path=$(WIT) --world=activity bindings ./bindings
