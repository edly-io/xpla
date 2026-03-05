// Video plugin - saves video URL configuration via WASM backend
//
// Actions handled:
// - config.save: Save the video_url

import { sendEvent, getField, setField, getPermission } from "../../src/sandbox-lib";

function onAction() {
  const { name, value } = JSON.parse(Host.inputString());

  if (name === "config.save") {
    if (getPermission() !== "edit") {
      console.log("config.save rejected: permission is " + getPermission());
      return;
    }
    setField("video_url", value.video_url);
    sendEvent("fields.change.video_url", value.video_url, {}, "play");
  }
}

function getState() {
  const state = {
    video_url: getField("video_url"),
  };
  Host.outputString(JSON.stringify(state));
}

module.exports = { onAction, getState };
