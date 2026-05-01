REPO_ROOT := ../..


build: sandbox.wasm

sandbox.wasm: pxc.wit server.py
	componentize-py --wit-path=pxc.wit --world=activity componentize --output sandbox.wasm server

# Generate bindings to better integrate with the IDE.
bindings: pxc.wit
	rm -rf ./bindings
	componentize-py --wit-path=pxc.wit --world=activity bindings ./bindings
