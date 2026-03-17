// Video plugin - saves video URL configuration via WASM backend
//
// Actions handled:
// - config.save: Save the video_url

import { sendEvent, getField, setField } from "../../src/xpla/lib/sandbox";

function onAction() {
  const { name, value, permission } = JSON.parse(Host.inputString());

  if (name === "config.save") {
    if (permission !== "edit") {
      console.log("config.save rejected: permission is " + permission);
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
