// YouTube plugin - saves video configuration via WASM backend
//
// Actions handled:
// - config.save: Save the video_id

import { getField, sendEvent, setField } from "pxc:sandbox/state";

export function onAction(name, data, context, permission) {
  const value = JSON.parse(data);
  if (name === "config.save") {
    if (permission !== "edit") {
      console.log("config.save rejected: permission is " + permission);
      return "";
    }
    setField("video_id", JSON.stringify(value.video_id));
    sendEvent("fields.change.video_id", JSON.stringify(value.video_id), null, "play");
  }
  return "";
}

export function getState() {
  const state = {
    video_id: JSON.parse(getField("video_id")),
  };
  return JSON.stringify(state);
}
