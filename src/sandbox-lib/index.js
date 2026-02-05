// Shared library for GULPS sandbox modules
//
// Provides helper functions for common host function interactions.
// Only includes functions available to ALL activities.

const { post_event, get_value, set_value, get_user_id } = Host.getFunctions();

export function postEvent(name, value) {
  const nameMem = Memory.fromString(name);
  const valueMem = Memory.fromString(value);
  post_event(nameMem.offset, valueMem.offset);
}

// Get current user info from LMS. Requires lms capability with get_user.
// Returns { id: "..." }
export function getUser() {
  const mem = Memory.fromString("");
  const resultOffset = get_user_id(mem.offset);
  const result = Memory.find(resultOffset).readString();
  return JSON.parse(result);
}

// Get a shared (unit-scoped) value.
export function getValue(name) {
  const userIdMem = Memory.fromString("");
  const nameMem = Memory.fromString(name);
  const resultOffset = get_value(userIdMem.offset, nameMem.offset);
  const result = Memory.find(resultOffset).readString();
  return JSON.parse(result);
}

// Set a shared (unit-scoped) value.
export function setValue(name, value) {
  const userIdMem = Memory.fromString("");
  const nameMem = Memory.fromString(name);
  const valueMem = Memory.fromString(JSON.stringify(value));
  set_value(userIdMem.offset, nameMem.offset, valueMem.offset);
}

// Get a user-scoped value for the current user.
export function getUserValue(name) {
  const userId = String(getUser().id);
  const userIdMem = Memory.fromString(userId);
  const nameMem = Memory.fromString(name);
  const resultOffset = get_value(userIdMem.offset, nameMem.offset);
  const result = Memory.find(resultOffset).readString();
  return JSON.parse(result);
}

// Set a user-scoped value for the current user.
export function setUserValue(name, value) {
  const userId = String(getUser().id);
  const userIdMem = Memory.fromString(userId);
  const nameMem = Memory.fromString(name);
  const valueMem = Memory.fromString(JSON.stringify(value));
  set_value(userIdMem.offset, nameMem.offset, valueMem.offset);
}
