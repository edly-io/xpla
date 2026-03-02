// Shared library for xPLA sandbox modules
//
// Provides helper functions for common host function interactions.
// Only includes functions available to ALL activities.

const {
  send_event,
  get_field,
  set_field,
  get_permission,
  stream_query,
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

// Append a value to a stream. Returns the assigned integer ID.
export function streamAppend(name, value) {
  return memoryOffset2data(stream_query(
    string2memoryOffset(name),
    data2memoryOffset({ op: "append", value }),
  ));
}

// Read entries from a stream. Options: { after, limit } or { last }.
export function streamRange(name, { after, limit, last } = {}) {
  const op = { op: "range" };
  if (last !== undefined) op.last = last;
  if (after !== undefined) op.after = after;
  if (limit !== undefined) op.limit = limit;
  return memoryOffset2data(stream_query(
    string2memoryOffset(name),
    data2memoryOffset(op),
  ));
}

// Get the number of entries in a stream.
export function streamLength(name) {
  return memoryOffset2data(stream_query(
    string2memoryOffset(name),
    data2memoryOffset({ op: "length" }),
  ));
}

// Delete an entry from a stream by ID. Returns boolean.
export function streamDelete(name, id) {
  return memoryOffset2data(stream_query(
    string2memoryOffset(name),
    data2memoryOffset({ op: "delete", id }),
  ));
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