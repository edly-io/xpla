// Slideshow plugin - saves reveal.js presentation HTML via WASM backend
//
// Actions handled:
// - config.save: Save the slides_html

import { sendEvent, getField, setField } from "../../src/sandbox-lib";

function onAction() {
  const { name, value, permission } = JSON.parse(Host.inputString());

  if (name === "config.save") {
    if (permission !== "edit") {
      console.log("config.save rejected: permission is " + permission);
      return;
    }
    setField("slides_html", value.slides_html);
    sendEvent("fields.change.slides_html", value.slides_html, {}, "play");
  }
}

function getState() {
  const state = {
    slides_html: getField("slides_html"),
  };
  Host.outputString(JSON.stringify(state));
}

module.exports = { onAction, getState };
