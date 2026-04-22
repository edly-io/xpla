// Slideshow plugin - saves reveal.js presentation HTML via WASM backend
//
// Actions handled:
// - config.save: Save the slides_html

import { sendEvent, getField, setField } from "xpla:sandbox/host";

export function onAction(name, data, context, permission) {
  const value = JSON.parse(data);
  if (name === "config.save") {
    if (permission !== "edit") {
      console.log("config.save rejected: permission is " + permission);
      return "";
    }
    setField("slides_html", JSON.stringify(value.slides_html));
    sendEvent("fields.change.slides_html", JSON.stringify(value.slides_html), null, "play");
  }
  return "";
}

export function getState() {
  const state = {
    slides_html: JSON.parse(getField("slides_html")),
  };
  return JSON.stringify(state);
}
