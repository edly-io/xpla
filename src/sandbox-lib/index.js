// Shared library for xPLA sandbox modules
//
// Provides helper functions for common host function interactions.
// Only includes functions available to ALL activities.

const {
  send_event,
  get_field,
  set_field,
  get_permission,
} = Host.getFunctions();

export function sendEvent(name, value) {
  const nameMem = Memory.fromString(name);
  const valueMem = Memory.fromString(JSON.stringify(value));
  send_event(nameMem.offset, valueMem.offset);
}

// Get the current permission level ("view", "play", or "edit").
export function getPermission() {
  const resultOffset = get_permission();
  return Memory.find(resultOffset).readString();
}

// Get a field (scope resolved from manifest).
export function getField(name) {
  const nameMem = Memory.fromString(name);
  const resultOffset = get_field(nameMem.offset);
  const result = Memory.find(resultOffset).readString();
  return JSON.parse(result);
}

// Set a field (scope resolved from manifest).
export function setField(name, value) {
  const nameMem = Memory.fromString(name);
  const valueJSON = JSON.stringify(value);
  const valueMem = Memory.fromString(valueJSON);
  set_field(nameMem.offset, valueMem.offset);
}
