REPO_ROOT := ../..


build: sandbox.wasm

sandbox.wasm: xpla.wit server.py
	componentize-py --wit-path=xpla.wit --world=activity componentize --output sandbox.wasm server

# Generate bindings to better integrate with the IDE.
bindings: xpla.wit
	rm -rf ./bindings
	componentize-py --wit-path=xpla.wit --world=activity bindings ./bindings
