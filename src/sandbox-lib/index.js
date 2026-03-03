// Shared library for xPLA sandbox modules
//
// Provides helper functions for common host function interactions.
// Only includes functions available to ALL activities.

const {
  send_event,
  get_field,
  set_field,
  get_object_field,
  set_object_field,
  get_permission,
} = Host.getFunctions();

export function sendEvent(name, value) {
  send_event(string2memoryOffset(name), data2memoryOffset(value));
}

// Get the current permission level ("view", "play", or "edit").
export function getPermission() {
  return memoryOffset2string(get_permission());
}

// Get a field (scope resolved from manifest).
// Optional scope overrides: e.g. { user_id: "bob" }
export function getField(name, scope = {}) {
  return memoryOffset2data(get_field(string2memoryOffset(name), data2memoryOffset(scope)));
}

// Set a field (scope resolved from manifest).
// Optional scope overrides: e.g. { user_id: "bob" }
export function setField(name, value, scope = {}) {
  set_field(string2memoryOffset(name), data2memoryOffset(value), data2memoryOffset(scope));
}

// Get a single key from an object field.
// Returns defaultValue if the key doesn't exist.
export function getObjectField(name, key, defaultValue = null, scope = {}) {
  return memoryOffset2data(
    get_object_field(string2memoryOffset(name), string2memoryOffset(key), data2memoryOffset(defaultValue), data2memoryOffset(scope))
  );
}

// Set a single key in an object field.
export function setObjectField(name, key, value, scope = {}) {
  set_object_field(
    string2memoryOffset(name), string2memoryOffset(key), data2memoryOffset(value), data2memoryOffset(scope)
  );
}

function string2memoryOffset(str) {
  return Memory.fromString(str).offset;
}

function data2memoryOffset(data) {
  const dataJSON = JSON.stringify(data);
  const memory = Memory.fromString(dataJSON);
  return memory.offset;
}

function memoryOffset2data(offset) {
  return JSON.parse(memoryOffset2string(offset));
}

function memoryOffset2string(offset) {
  return Memory.find(offset).readString();
}
