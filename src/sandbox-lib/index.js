// Shared library for xPLA sandbox modules
//
// Provides helper functions for common host function interactions.
// Only includes functions available to ALL activities.

const {
  send_event,
  get_value,
  get_user_value,
  set_value,
  set_user_value,
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

// Get a shared (unit-scoped) value.
export function getValue(name) {
  const nameMem = Memory.fromString(name);
  const resultOffset = get_value(nameMem.offset);
  const result = Memory.find(resultOffset).readString();
  return JSON.parse(result);
}

// Set a shared (unit-scoped) value.
export function setValue(name, value) {
  const nameMem = Memory.fromString(name);
  const valueJSON = JSON.stringify(value);
  const valueMem = Memory.fromString(valueJSON);
  set_value(nameMem.offset, valueMem.offset);
}

// Get a user-scoped value for the current user.
export function getUserValue(name) {
  const nameMem = Memory.fromString(name);
  const resultOffset = get_user_value(nameMem.offset);
  const result = Memory.find(resultOffset).readString();
  return JSON.parse(result);
}

// Set a user-scoped value for the current user.
export function setUserValue(name, value) {
  const nameMem = Memory.fromString(name);
  const valueMem = Memory.fromString(JSON.stringify(value));
  set_user_value(nameMem.offset, valueMem.offset);
}
