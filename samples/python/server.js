// Python coding activity - saves configuration and user code via WASM backend
//
// Actions handled:
// - config.save: Save instructions, starter_code, and test_code (edit only)
// - code.run: Save user_code (play only)
// - code.check: Save user_code (play only)

import {
  sendEvent,
  getField,
  setField,
} from "xpla:sandbox/host";

function saveUserCode(code) {
  setField("user_code", JSON.stringify(code));
  sendEvent("fields.change.user_code", JSON.stringify(code), null, "play");
}

export function onAction(name, data, context, permission) {
  const value = JSON.parse(data);
  if (name === "config.save") {
    if (permission !== "edit") {
      console.log("config.save rejected: permission is " + permission);
      return "";
    }
    for (const key of ["instructions", "starter_code", "test_code"]) {
      if (value[key] !== undefined) {
        setField(key, JSON.stringify(value[key]));
        sendEvent("fields.change." + key, JSON.stringify(value[key]), null, "play");
      }
    }
  }

  if (name === "code.run" || name === "code.check") {
    if (permission === "view") {
      console.log(name + " rejected: permission is view");
      return;
    }
    saveUserCode(value.code);
  }
  return "";
}

export function getState(input) {
  const state = {
    instructions: JSON.parse(getField("instructions")),
    starter_code: JSON.parse(getField("starter_code")),
    test_code: JSON.parse(getField("test_code")),
    user_code: JSON.parse(getField("user_code")),
  };
  return JSON.stringify(state);
}
