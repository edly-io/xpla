REPO_ROOT := ../..


build: server.component.wasm

server.component.wasm: xpla.wit server.py
	componentize-py --wit-path=xpla.wit --world=activity componentize --output server.component.wasm server

# Generate bindings to better integrate with the IDE.
bindings: xpla.wit
	rm -rf ./bindings
	componentize-py --wit-path=xpla.wit --world=activity bindings ./bindings
