// Image activity — upload and display an image
//
// Actions handled:
// - image.upload: Save an image from a data URI

import { getField, sendEvent, setField } from "pxc:sandbox/state";
import { storageUrl, storageWrite } from "pxc:sandbox/storage";

const MIME_TO_EXT = {
  "image/jpeg": "jpg",
  "image/png": "png",
  "image/gif": "gif",
  "image/webp": "webp",
  "image/svg+xml": "svg",
};

function base64ToBytes(base64) {
  const binString = atob(base64);
  const bytes = new Uint8Array(binString.length);
  for (let i = 0; i < binString.length; i++) {
    bytes[i] = binString.charCodeAt(i);
  }
  return bytes;
}

export function onAction(name, data, context, permission) {
  if (name === "image.upload") {
    if (permission !== "edit") {
      console.log("image.upload rejected: permission is " + permission);
      return "";
    }
    const value = JSON.parse(data);
    const dataUri = value.data;

    // Parse data URI: data:<mime>;base64,<data>
    const match = dataUri.match(/^data:([^;]+);base64,(.+)$/);
    if (!match) {
      console.log("image.upload rejected: invalid data URI");
      return "";
    }
    const mime = match[1];
    const base64 = match[2];
    const ext = MIME_TO_EXT[mime] || "bin";
    const filename = "img." + ext;

    storageWrite("media", filename, base64ToBytes(base64), null);
    setField("image_filename", JSON.stringify(filename));
    sendEvent("image.changed", JSON.stringify(storageUrl("media", filename, null)), null, "view");
  }
  return "";
}

export function getState() {
  const filename = JSON.parse(getField("image_filename"));
  const state = {
    image_url: filename ? storageUrl("media", filename, null) : "",
    image_filename: filename,
  };
  return JSON.stringify(state);
}
