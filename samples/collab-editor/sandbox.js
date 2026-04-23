// Collaborative editor sandbox - relays Yjs updates between clients
//
// Actions handled:
// - doc.update: Merge Yjs update into stored state, broadcast to all
// - cursor.move: Broadcast cursor position to all clients

import { getField, sendEvent, setField } from "xpla:sandbox/state";
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

export function onAction(name, data, context, permission) {
  const value = JSON.parse(data);
  const user = context.userId;

  if (name === "config.save") {
    if (permission !== "edit") {
      console.log("config.save rejected: not edit permission");
      return "";
    }
    setField("render_markdown", JSON.stringify(value.render_markdown));
    sendEventToAllViewers("fields.change.render_markdown", value.render_markdown);
  } else if (name === "doc.update") {
    // Load current doc state
    const doc = new Y.Doc();
    const stored = JSON.parse(getField("doc_state"));
    if (stored) {
      Y.applyUpdate(doc, base64ToBytes(stored));
    }

    // Apply incoming update
    Y.applyUpdate(doc, base64ToBytes(value.data));

    // Save merged state and plain text snapshot
    const fullState = Y.encodeStateAsUpdate(doc);
    setField("doc_state", JSON.stringify(bytesToBase64(fullState)));
    setField("content", JSON.stringify(doc.getText("codemirror").toString()));
    sendEventToAllViewers("doc.update", { data: value.data, user });
  } else if (name === "cursor.move") {
    sendEventToAllViewers("cursor.move", {
      user,
      index: value.index,
      length: value.length,
    });
  }
  return "";
}

function sendEventToAllViewers(name, value) {
  // Send the same event to both viewers and players
  sendEvent(name, JSON.stringify(value), null, "play");
  sendEvent(name, JSON.stringify(value), null, "view");
}

export function getState(context, permission) {
  const state = {
    render_markdown: JSON.parse(getField("render_markdown")) || 0
  };
  if (permission === "play" || permission == "play") {
    state.doc_state = JSON.parse(getField("doc_state"));
    state.content = JSON.parse(getField("content"));
  }
  return JSON.stringify(state);
}
