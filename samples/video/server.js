// Video plugin - saves video URL configuration via WASM backend
//
// Actions handled:
// - config.save: Save the video_url

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
    setValue("video_url", actionValue.video_url);
    sendEvent("values.change.video_url", actionValue.video_url);
  }
}

function getState() {
  const state = {
    video_url: getValue("video_url"),
  };
  Host.outputString(JSON.stringify(state));
}

module.exports = { onAction, getState };
