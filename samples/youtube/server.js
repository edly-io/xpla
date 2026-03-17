// YouTube plugin - saves video configuration via WASM backend
//
// Actions handled:
// - config.save: Save the video_id

import { sendEvent, getField, setField } from "../../src/xpla/lib/sandbox";

function onAction() {
  const { name, value, permission } = JSON.parse(Host.inputString());

  if (name === "config.save") {
    if (permission !== "edit") {
      console.log("config.save rejected: permission is " + permission);
      return;
    }
    setField("video_id", value.video_id);
    sendEvent("fields.change.video_id", value.video_id, {}, "play");
  }
}

function getState() {
  const state = {
    video_id: getField("video_id"),
  };
  Host.outputString(JSON.stringify(state));
}

module.exports = { onAction, getState };
