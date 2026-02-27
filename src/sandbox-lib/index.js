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
  get_course_value,
  set_course_value,
  get_course_user_value,
  set_course_user_value,
  get_platform_value,
  set_platform_value,
  get_platform_user_value,
  set_platform_user_value,
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

// Get a shared (activity-scoped) value.
export function getValue(name) {
  const nameMem = Memory.fromString(name);
  const resultOffset = get_value(nameMem.offset);
  const result = Memory.find(resultOffset).readString();
  return JSON.parse(result);
}

// Set a shared (activity-scoped) value.
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

// Get a course-scoped value.
export function getCourseValue(name) {
  const nameMem = Memory.fromString(name);
  const resultOffset = get_course_value(nameMem.offset);
  const result = Memory.find(resultOffset).readString();
  return JSON.parse(result);
}

// Set a course-scoped value.
export function setCourseValue(name, value) {
  const nameMem = Memory.fromString(name);
  const valueMem = Memory.fromString(JSON.stringify(value));
  set_course_value(nameMem.offset, valueMem.offset);
}

// Get a user,course-scoped value for the current user.
export function getCourseUserValue(name) {
  const nameMem = Memory.fromString(name);
  const resultOffset = get_course_user_value(nameMem.offset);
  const result = Memory.find(resultOffset).readString();
  return JSON.parse(result);
}

// Set a user,course-scoped value for the current user.
export function setCourseUserValue(name, value) {
  const nameMem = Memory.fromString(name);
  const valueMem = Memory.fromString(JSON.stringify(value));
  set_course_user_value(nameMem.offset, valueMem.offset);
}

// Get a platform-scoped value.
export function getPlatformValue(name) {
  const nameMem = Memory.fromString(name);
  const resultOffset = get_platform_value(nameMem.offset);
  const result = Memory.find(resultOffset).readString();
  return JSON.parse(result);
}

// Set a platform-scoped value.
export function setPlatformValue(name, value) {
  const nameMem = Memory.fromString(name);
  const valueMem = Memory.fromString(JSON.stringify(value));
  set_platform_value(nameMem.offset, valueMem.offset);
}

// Get a user,platform-scoped value for the current user.
export function getPlatformUserValue(name) {
  const nameMem = Memory.fromString(name);
  const resultOffset = get_platform_user_value(nameMem.offset);
  const result = Memory.find(resultOffset).readString();
  return JSON.parse(result);
}

// Set a user,platform-scoped value for the current user.
export function setPlatformUserValue(name, value) {
  const nameMem = Memory.fromString(name);
  const valueMem = Memory.fromString(JSON.stringify(value));
  set_platform_user_value(nameMem.offset, valueMem.offset);
}
