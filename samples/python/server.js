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
  getPermission,
} from "../../src/sandbox-lib";

function saveUserCode(code) {
  setField("user_code", code);
  sendEvent("fields.change.user_code", code);
}

function onAction() {
  const { name, value } = JSON.parse(Host.inputString());

  if (name === "config.save") {
    if (getPermission() !== "edit") {
      console.log("config.save rejected: permission is " + getPermission());
      return;
    }
    for (const key of ["instructions", "starter_code", "test_code"]) {
      if (value[key] !== undefined) {
        setField(key, value[key]);
        sendEvent("fields.change." + key, value[key]);
      }
    }
  }

  if (name === "code.run" || name === "code.check") {
    if (getPermission() === "view") {
      console.log(name + " rejected: permission is view");
      return;
    }
    saveUserCode(value.code);
  }
}

function getState() {
  const state = {
    instructions: getField("instructions"),
    starter_code: getField("starter_code"),
    test_code: getField("test_code"),
    user_code: getField("user_code"),
  };
  Host.outputString(JSON.stringify(state));
}

module.exports = { onAction, getState };
