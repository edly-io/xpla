// Collaborative editor sandbox - relays Yjs updates between clients
//
// Actions handled:
// - doc.update: Merge Yjs update into stored state, broadcast to all
// - cursor.move: Broadcast cursor position to all clients

import { sendEvent, getField, setField } from "../../src/xpla/lib/sandbox";
import * as Y from "yjs";

function base64ToBytes(base64) {
  const binString = atob(base64);
  const bytes = new Uint8Array(binString.length);
  for (let i = 0; i < binString.length; i++) {
    bytes[i] = binString.charCodeAt(i);
  }
  return bytes;
}

function bytesToBase64(bytes) {
  let binString = "";
  for (let i = 0; i < bytes.length; i++) {
    binString += String.fromCharCode(bytes[i]);
  }
  return btoa(binString);
}

function onAction() {
  const { name, value, scope, permission } = JSON.parse(Host.inputString());
  const user = scope.user_id;

  if (name === "config.save") {
    if (permission !== "edit") {
      console.log("config.save rejected: not edit permission");
      return;
    }
    setField("render_markdown", value.render_markdown);
    sendEventToAllViewers("fields.change.render_markdown", value.render_markdown);
    return;
  }

  if (name === "doc.update") {
    // Load current doc state
    const doc = new Y.Doc();
    const stored = getField("doc_state");
    if (stored) {
      Y.applyUpdate(doc, base64ToBytes(stored));
    }

    // Apply incoming update
    Y.applyUpdate(doc, base64ToBytes(value.data));

    // Save merged state and plain text snapshot
    const fullState = Y.encodeStateAsUpdate(doc);
    setField("doc_state", bytesToBase64(fullState));
    setField("content", doc.getText("codemirror").toString());
    sendEventToAllViewers("doc.update", { data: value.data, user });
  }

  if (name === "cursor.move") {
    sendEventToAllViewers("cursor.move", {
      user,
      index: value.index,
      length: value.length,
    });
  }
}

function sendEventToAllViewers(name, value) {
  // Send the same event to both viewers and players
  sendEvent(name, value, {}, "play");
  sendEvent(name, value, {}, "view");
}

function getState() {
  const { context, permission } = JSON.parse(Host.inputString());
  const state = {
    doc_state: getField("doc_state"),
    content: getField("content"),
    user_id: context.user_id,
    render_markdown: getField("render_markdown") || 0,
  };
  Host.outputString(JSON.stringify(state));
}

module.exports = { onAction, getState };
