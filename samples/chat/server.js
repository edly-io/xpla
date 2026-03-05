// Chat plugin - appends messages to a log field
//
// Actions handled:
// - chat.post: Append a message and broadcast it

import { sendEvent, logAppend, logGetRange } from "../../src/sandbox-lib";

function onAction() {
  const { name, value, scope } = JSON.parse(Host.inputString());

  if (name === "chat.post") {
    const user = scope.user_id;
    const entry = { user, text: value.text };
    const id = logAppend("messages", entry);
    sendEvent("chat.new", { id, user, text: value.text }, {}, "play");
  }
}

function getState() {
  const messages = logGetRange("messages", 0, 1000);
  Host.outputString(JSON.stringify({ messages }));
}

module.exports = { onAction, getState };
