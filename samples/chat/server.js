// Chat plugin - appends messages to a log field
//
// Actions handled:
// - chat.post: Append a message and broadcast it

import { sendEvent, logAppend, logGetRange } from "../../src/xpla/lib/sandbox";

export function onAction(name, data, context, permission) {
  const value = JSON.parse(data);
  if (name === "chat.post") {
    const user = context.userId;
    const entry = { user, text: value.text };
    const id = logAppend("messages", entry);
    sendEvent("chat.new", { id, user, text: value.text }, "play");
  }

  return "";
}

export function getState() {
  const messages = logGetRange("messages", 0, 1000);
  return JSON.stringify({ messages });
}
