// Shared library for xPLA sandbox modules
//
// Provides helper functions for common host function interactions.
// Only includes functions available to ALL activities.

import {
  sendEvent as _sendEvent,
  getField as _getField,
  setField as _setField,
  logGet as _logGet,
  logGetRange as _logGetRange,
  logAppend as _logAppend,
  logDelete as _logDelete,
  logDeleteRange as _logDeleteRange,
  httpRequest as _httpRequest,
  submitGrade as _submitGrade,
  storageRead as _storageRead,
  storageExists as _storageExists,
  storageUrl as _storageUrl,
  storageList as _storageList,
  storageWrite as _storageWrite,
  storageDelete as _storageDelete,
} from "xpla:sandbox/host";

export function sendEvent(name, value, context = null, permission = "play") {
  _sendEvent(name, JSON.stringify(value), context, permission);
}

// Get a field (scope resolved from manifest).
export function getField(name, context = null) {
  return JSON.parse(_getField(name, context));
}

// Set a field (scope resolved from manifest).
export function setField(name, value, context = null) {
  _setField(name, JSON.stringify(value), context);
}

// Get a single log entry by id.
export function logGet(name, id, context = null) {
  return JSON.parse(_logGet(name, id, context));
}

// Get log entries in range [fromId, toId).
export function logGetRange(name, fromId, toId, context = null) {
  return JSON.parse(_logGetRange(name, fromId, toId, context));
}

// Append a value to a log field. Returns the assigned id.
export function logAppend(name, value, context = null) {
  return _logAppend(name, JSON.stringify(value), context);
}

// Delete a single log entry by id.
export function logDelete(name, id, context = null) {
  return _logDelete(name, id, context);
}

// Delete log entries in range [fromId, toId). Returns count deleted.
export function logDeleteRange(name, fromId, toId, context = null) {
  return _logDeleteRange(name, fromId, toId, context);
}

// Make an HTTP request. Returns {status, headers, body}.
// status=0 indicates a connection or capability error.
export function httpRequest(url, method, body, headers) {
  const result = _httpRequest(
    url,
    method,
    body || "",
    JSON.stringify(headers || []),
  );
  return JSON.parse(result);
}

// Submit a grade to the LMS. Score is a float (0-100).
export function submitGrade(score) {
  return _submitGrade(score);
}

// Read a file from storage. Returns raw bytes (Uint8Array).
export function storageRead(name, path) {
  return _storageRead(name, path);
}

// Check whether a path exists in storage.
export function storageExists(name, path) {
  return _storageExists(name, path);
}

// Get the HTTP URL for a storage file.
export function storageUrl(name, path) {
  return _storageUrl(name, path);
}

// List files and directories at a storage path.
// Returns {files: string[], directories: string[]}.
export function storageList(name, path) {
  return _storageList(name, path);
}

// Write content (Uint8Array) to a storage file.
export function storageWrite(name, path, content) {
  return _storageWrite(name, path, content);
}

// Delete a storage file. Returns true if it existed.
export function storageDelete(name, path) {
  return _storageDelete(name, path);
}
