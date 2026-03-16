// Collaborative text editor client
// Uses Yjs (CRDT) + CodeMirror 6 for real-time collaborative editing

import * as Y from "yjs";
import { yCollab } from "y-codemirror.next";
import { EditorView, basicSetup } from "codemirror";
import { EditorState } from "@codemirror/state";
import { marked } from "marked";

const UPDATE_THROTTLE_MS = 100;
const CURSOR_THROTTLE_MS = 50;

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

// Assign a consistent color per user
const CURSOR_COLORS = [
  "#e06c75", "#61afef", "#98c379", "#e5c07b",
  "#c678dd", "#56b6c2", "#be5046", "#d19a66",
];
function getUserColor(userId) {
  let hash = 0;
  for (let i = 0; i < userId.length; i++) {
    hash = (hash * 31 + userId.charCodeAt(i)) | 0;
  }
  return CURSOR_COLORS[((hash % CURSOR_COLORS.length) + CURSOR_COLORS.length) % CURSOR_COLORS.length];
}

export function setup(activity) {
  const element = activity.element;
  const permission = activity.permission;
  const root = element.getRootNode();
  const readOnly = permission === "view";

  // Yjs document
  const ydoc = new Y.Doc();
  const ytext = ydoc.getText("codemirror");

  // Remote cursors state: Map<userId, {index, length, color}>
  const remoteCursors = new Map();

  // Render UI
  element.innerHTML = `
    <style>
      .collab-container { font-family: sans-serif; max-width: 900px; }
      .collab-header { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; }
      .collab-header h3 { margin: 0; }
      .collab-users { display: flex; gap: 0.25rem; }
      .collab-user-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
      .cm-wrap { border: 1px solid #ccc; position: relative; }
      .cm-wrap .cm-editor { min-height: 200px; max-height: 600px; overflow: auto; }
      .remote-cursor-line { position: absolute; width: 2px; pointer-events: none; z-index: 10; }
      .remote-cursor-label { position: absolute; font-size: 10px; color: white; padding: 0 3px; border-radius: 2px; white-space: nowrap; pointer-events: none; z-index: 10; transform: translateY(-100%); }
      #md-preview { display: none; border: 1px solid #ccc; padding: 1rem; min-height: 200px; max-height: 600px; overflow: auto; }
      #md-preview h1, #md-preview h2, #md-preview h3 { margin-top: 0.5rem; }
      #md-preview pre { background: #f4f4f4; padding: 0.5rem; border-radius: 4px; overflow-x: auto; }
      #md-preview code { background: #f4f4f4; padding: 0.1rem 0.3rem; border-radius: 3px; }
      #md-preview pre code { background: none; padding: 0; }
    </style>
    <div class="collab-container">
      <div class="collab-header">
        <div class="collab-users" id="collab-users"></div>
      </div>
      <div class="cm-wrap" id="editor-wrap">
        <div id="editor-container"></div>
      </div>
      <div id="md-preview"></div>
    </div>
  `;

  const editorContainer = element.querySelector("#editor-container");
  const editorWrap = element.querySelector("#editor-wrap");
  const usersContainer = element.querySelector("#collab-users");
  const mdPreview = element.querySelector("#md-preview");
  const header = element.querySelector(".collab-header");

  const isEdit = permission === "edit";
  const renderMd = !!activity.state.render_markdown;

  let previewVisible = !isEdit && renderMd;

  function renderMarkdown() {
    mdPreview.innerHTML = marked.parse(ytext.toString());
  }

  if (isEdit) {
    // Edit mode: only show checkbox to configure markdown rendering, hide editor
    editorWrap.style.display = "none";
    const label = document.createElement("label");
    label.style.cssText = "display:flex;align-items:center;gap:0.3rem;font-size:0.85rem;cursor:pointer;";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = renderMd;
    label.appendChild(checkbox);
    label.append("Render markdown");
    header.appendChild(label);
    checkbox.addEventListener("change", () => {
      activity.sendAction("config.save", { render_markdown: checkbox.checked ? 1 : 0 });
    });
  } else if (renderMd) {
    // Play/view mode with markdown enabled: show editor + preview below
    mdPreview.style.display = "block";
  }

  // Create CodeMirror with Yjs binding
  const undoManager = new Y.UndoManager(ytext);
  const editor = new EditorView({
    extensions: [
      basicSetup,
      yCollab(ytext, null, { undoManager }),
      EditorState.readOnly.of(readOnly),
    ],
    parent: editorContainer,
    root,
  });

  // Restore stored Yjs state — must happen AFTER EditorView creation so that
  // the yCollab observer is already attached and syncs content to CodeMirror.
  const storedState = activity.state.doc_state;
  if (storedState) {
    Y.applyUpdate(ydoc, base64ToBytes(storedState));
  }

  // Render initial markdown if preview is visible (e.g. view mode with restored state)
  if (previewVisible) renderMarkdown();

  // Throttled action senders
  let updateTimer = null;
  let pendingUpdates = [];
  let cursorTimer = null;

  // Listen for local Yjs updates and send to server
  // Each "update" event carries an incremental delta — we must accumulate
  // all pending deltas and merge them before sending, otherwise the throttle
  // would silently drop intermediate updates.
  if (!readOnly) {
    ydoc.on("update", (update, origin) => {
      if (origin === "remote") return;
      pendingUpdates.push(update);
      if (updateTimer) clearTimeout(updateTimer);
      updateTimer = setTimeout(() => {
        const merged = Y.mergeUpdates(pendingUpdates);
        pendingUpdates = [];
        activity.sendAction("doc.update", { data: bytesToBase64(merged) });
        if (previewVisible) renderMarkdown();
      }, UPDATE_THROTTLE_MS);
    });
  }

  // Track local cursor changes and send to server
  if (!readOnly) {
    editor.dom.addEventListener("keyup", sendCursor);
    editor.dom.addEventListener("mouseup", sendCursor);
    editor.dom.addEventListener("click", sendCursor);
  }

  function sendCursor() {
    if (cursorTimer) clearTimeout(cursorTimer);
    cursorTimer = setTimeout(() => {
      const sel = editor.state.selection.main;
      activity.sendAction("cursor.move", {
        index: sel.head,
        length: sel.to - sel.from,
      });
    }, CURSOR_THROTTLE_MS);
  }

  // Handle events from server
  activity.onEvent = (name, value) => {
    if (name === "doc.update") {
      Y.applyUpdate(ydoc, base64ToBytes(value.data), "remote");
      if (previewVisible) renderMarkdown();
    }
    if (name === "cursor.move") {
      const userId = value.user;
      if (userId === activity.state.user_id) return;
      const color = getUserColor(userId);
      remoteCursors.set(userId, { index: value.index, length: value.length, color });
      renderRemoteCursors();
      renderUserDots();
    }
  };

  // Render remote cursor indicators as overlay elements
  function renderRemoteCursors() {
    // Remove old cursor elements
    editorWrap.querySelectorAll(".remote-cursor-line, .remote-cursor-label").forEach((el) => el.remove());

    for (const [userId, cursor] of remoteCursors.entries()) {
      const pos = Math.min(cursor.index, editor.state.doc.length);
      const coords = editor.coordsAtPos(pos);
      if (!coords) continue;

      const wrapRect = editorWrap.getBoundingClientRect();

      // Cursor line
      const line = document.createElement("div");
      line.className = "remote-cursor-line";
      line.style.backgroundColor = cursor.color;
      line.style.left = (coords.left - wrapRect.left) + "px";
      line.style.top = (coords.top - wrapRect.top) + "px";
      line.style.height = (coords.bottom - coords.top) + "px";
      editorWrap.appendChild(line);

      // User label
      const label = document.createElement("div");
      label.className = "remote-cursor-label";
      label.style.backgroundColor = cursor.color;
      label.style.left = (coords.left - wrapRect.left) + "px";
      label.style.top = (coords.top - wrapRect.top) + "px";
      label.textContent = userId;
      editorWrap.appendChild(label);
    }
  }

  // Show colored dots for connected users
  function renderUserDots() {
    usersContainer.innerHTML = "";
    for (const [userId, cursor] of remoteCursors.entries()) {
      const dot = document.createElement("span");
      dot.className = "collab-user-dot";
      dot.style.backgroundColor = cursor.color;
      dot.title = userId;
      usersContainer.appendChild(dot);
    }
  }
}
