// Chat plugin - appends messages to a log field
//
// Actions handled:
// - chat.post: Append a message and broadcast it

import { logAppend, logGetRange, sendEvent } from "xpla:sandbox/state";

export function onAction(name, data, context, permission) {
  const value = JSON.parse(data);
  if (name === "chat.post") {
    const user = context.userId;
    const entry = { user, text: value.text };
    const id = logAppend("messages", JSON.stringify(entry));
    sendEvent("chat.new", JSON.stringify({ id, user, text: value.text }), null, "play");
  }

  return "";
}

export function getState() {
  const messages = JSON.parse(logGetRange("messages", 0, 1000));
  return JSON.stringify({ messages });
}
