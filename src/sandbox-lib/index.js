// Shared library for xPLA sandbox modules
//
// Provides helper functions for common host function interactions.
// Only includes functions available to ALL activities.

const {
  send_event,
  get_field,
  set_field,
  get_user_field,
  set_user_field,
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
export function getField(name) {
  return memoryOffset2data(get_field(string2memoryOffset(name)));
}

// Set a field (scope resolved from manifest).
export function setField(name, value) {
  set_field(string2memoryOffset(name), data2memoryOffset(value));
}

// Get a user-scoped field for a specific user.
export function getUserField(userId, name) {
  return memoryOffset2data(get_user_field(string2memoryOffset(userId), string2memoryOffset(name)));
}

// Set a user-scoped field for a specific user.
export function setUserField(userId, name, value) {
  set_user_field(string2memoryOffset(userId), string2memoryOffset(name), data2memoryOffset(value));
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