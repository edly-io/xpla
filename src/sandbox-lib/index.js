// Shared library for GULPS sandbox modules
//
// Provides helper functions for common host function interactions.
// Only includes functions available to ALL activities.

const { post_event, get_value, set_value, get_user_id } = Host.getFunctions();

export function postEvent(name, value) {
  const nameMem = Memory.fromString(name);
  const valueMem = Memory.fromString(JSON.stringify(value));
  post_event(nameMem.offset, valueMem.offset);
}

// Get current user info from LMS. Requires lms capability with get_user.
// Returns { id: "..." }
export function getUserId() {
  const resultOffset = get_user_id();
  return Memory.find(resultOffset).readString();
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
  const valueJSON = JSON.stringify(value);
  const valueMem = Memory.fromString(valueJSON);
  set_value(userIdMem.offset, nameMem.offset, valueMem.offset);
}

// Get a user-scoped value for the current user.
export function getUserValue(name) {
  const userId = getUserId();
  const userIdMem = Memory.fromString(userId);
  const nameMem = Memory.fromString(name);
  const resultOffset = get_value(userIdMem.offset, nameMem.offset);
  const result = Memory.find(resultOffset).readString();
  return JSON.parse(result);
}

// Set a user-scoped value for the current user.
export function setUserValue(name, value) {
  const userId = getUserId();
  const userIdMem = Memory.fromString(userId);
  const nameMem = Memory.fromString(name);
  const valueMem = Memory.fromString(JSON.stringify(value));
  set_value(userIdMem.offset, nameMem.offset, valueMem.offset);
}
