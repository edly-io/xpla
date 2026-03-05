// Chat plugin - appends messages to a log field
//
// Actions handled:
// - chat.post: Append a message and broadcast it

import { sendEvent, logAppend, logGetRange, getPermission } from "../../src/sandbox-lib";

function onAction() {
  const input = JSON.parse(Host.inputString());
  const actionName = input.name;
  const actionValue = input.value;

  if (actionName === "chat.post") {
    const user = getPermission(); // placeholder: use permission as user id
    const entry = { user, text: actionValue.text };
    const id = logAppend("messages", entry);
    sendEvent("chat.new", { id, user, text: actionValue.text });
  }
}

function getState() {
  const messages = logGetRange("messages", 0, 1000);
  Host.outputString(JSON.stringify({ messages }));
}

module.exports = { onAction, getState };
