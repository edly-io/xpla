// Video plugin - saves video URL configuration via WASM backend
//
// Actions handled:
// - config.save: Save the video_url

import { sendEvent, getField, setField } from "xpla:sandbox/host";

export function onAction(name, data, context, permission) {
  const value = JSON.parse(data);
  if (name === "config.save") {
    if (permission !== "edit") {
      console.log("config.save rejected: permission is " + permission);
      return "";
    }
    setField("video_url", JSON.stringify(value.video_url));
    sendEvent("fields.change.video_url", JSON.stringify(value.video_url), null, "play");
  }
  return "";
}

export function getState() {
  const state = {
    video_url: JSON.parse(getField("video_url")),
  };
  return JSON.stringify(state);
}
