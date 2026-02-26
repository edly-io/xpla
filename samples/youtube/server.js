// YouTube plugin - saves video configuration via WASM backend
//
// Actions handled:
// - config.save: Save the video_id

import { sendEvent, getValue, setValue, getPermission } from "../../src/sandbox-lib";

function onAction() {
  const input = JSON.parse(Host.inputString());
  const actionName = input.name;
  const actionValue = input.value;

  if (actionName === "config.save") {
    if (getPermission() !== "edit") {
      console.log("config.save rejected: permission is " + getPermission());
      return;
    }
    setValue("video_id", actionValue.video_id);
    sendEvent("values.change.video_id", actionValue.video_id);
  }
}

function getState() {
  const state = {
    video_id: getValue("video_id"),
  };
  Host.outputString(JSON.stringify(state));
}

module.exports = { onAction, getState };
