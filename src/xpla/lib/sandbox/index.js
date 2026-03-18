// Shared library for xPLA sandbox modules
//
// Provides helper functions for common host function interactions.
// Only includes functions available to ALL activities.

const {
  send_event,
  get_field,
  set_field,
  log_get,
  log_get_range,
  log_append,
  log_delete,
  log_delete_range,
  http_request,
} = Host.getFunctions();

export function sendEvent(name, value, context = {}, permission = "play") {
  send_event(string2memoryOffset(name), data2memoryOffset(value), data2memoryOffset(context), string2memoryOffset(permission));
}

// Get a field (scope resolved from manifest).
// Optional context overrides: e.g. { user_id: "bob" }
export function getField(name, context = {}) {
  return memoryOffset2data(get_field(string2memoryOffset(name), data2memoryOffset(context)));
}

// Set a field (scope resolved from manifest).
// Optional context overrides: e.g. { user_id: "bob" }
export function setField(name, value, context = {}) {
  set_field(string2memoryOffset(name), data2memoryOffset(value), data2memoryOffset(context));
}

// Get a single log entry by id.
export function logGet(name, id, context = {}) {
  return memoryOffset2data(log_get(string2memoryOffset(name), id, data2memoryOffset(context)));
}

// Get log entries in range [fromId, toId).
export function logGetRange(name, fromId, toId, context = {}) {
  return memoryOffset2data(log_get_range(string2memoryOffset(name), fromId, toId, data2memoryOffset(context)));
}

// Append a value to a log field. Returns the assigned id.
export function logAppend(name, value, context = {}) {
  return log_append(string2memoryOffset(name), data2memoryOffset(value), data2memoryOffset(context));
}

// Delete a single log entry by id.
export function logDelete(name, id, context = {}) {
  return log_delete(string2memoryOffset(name), id, data2memoryOffset(context));
}

// Delete log entries in range [fromId, toId). Returns count deleted.
export function logDeleteRange(name, fromId, toId, context = {}) {
  return log_delete_range(string2memoryOffset(name), fromId, toId, data2memoryOffset(context));
}

// Make an HTTP request. Returns {status, headers, body}.
// status=0 indicates a connection or capability error.
export function httpRequest(url, method, body, headers) {
  const resultOffset = http_request(
    string2memoryOffset(url),
    string2memoryOffset(method),
    string2memoryOffset(body || ""),
    data2memoryOffset(headers || []),
  );
  return JSON.parse(memoryOffset2string(resultOffset));
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
