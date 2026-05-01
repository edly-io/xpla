// SCORM activity — upload a SCORM zip package and display it
//
// Actions handled:
// - scorm.upload: Receive a base64-encoded zip, decompress, store all files

import { getField, sendEvent, setField } from "pxc:sandbox/state";
import { storageDelete, storageList, storageUrl, storageWrite } from "pxc:sandbox/storage";
import { unzipSync } from "fflate";

function base64ToBytes(base64) {
  const binString = atob(base64);
  const bytes = new Uint8Array(binString.length);
  for (let i = 0; i < binString.length; i++) {
    bytes[i] = binString.charCodeAt(i);
  }
  return bytes;
}

/** Delete all files currently in the "content" storage namespace. */
function clearStorage(prefix) {
  const [dirs, files] = storageList("content", prefix, null);
  for (const file of files) {
    const path = prefix ? prefix + "/" + file : file;
    storageDelete("content", path, null);
  }
  for (const dir of dirs) {
    const path = prefix ? prefix + "/" + dir : dir;
    clearStorage(path);
  }
}

/** Find the SCORM entry point inside the extracted file tree. */
function findEntryPoint(paths) {
  // Look for imsmanifest.xml to determine the launch resource
  // Fall back to index.html at the shallowest depth
  const htmlFiles = paths
    .filter((p) => p.toLowerCase().endsWith(".html") || p.toLowerCase().endsWith(".htm"))
    .sort((a, b) => a.split("/").length - b.split("/").length);

  // Prefer index.html / index.htm
  const index = htmlFiles.find(
    (p) =>
      p.toLowerCase().endsWith("/index.html") ||
      p.toLowerCase().endsWith("/index.htm") ||
      p.toLowerCase() === "index.html" ||
      p.toLowerCase() === "index.htm",
  );
  if (index) return index;

  // Otherwise, pick the shallowest HTML file
  return htmlFiles.length > 0 ? htmlFiles[0] : "";
}

export function onAction(name, data, context, permission) {
  if (name === "scorm.upload") {
    if (permission !== "edit") {
      console.log("scorm.upload rejected: permission is " + permission);
      return "";
    }

    const value = JSON.parse(data);
    const dataUri = value.data;

    // Parse data URI: data:<mime>;base64,<data>
    const match = dataUri.match(/^data:[^;]*;base64,(.+)$/);
    if (!match) {
      console.log("scorm.upload rejected: invalid data URI");
      return "";
    }

    const zipBytes = base64ToBytes(match[1]);

    // Decompress
    let files;
    try {
      files = unzipSync(zipBytes);
    } catch (e) {
      console.log("scorm.upload rejected: invalid zip file: " + e);
      return "";
    }

    // Clear previous content
    clearStorage("");

    // Store each file
    const storedPaths = [];
    for (const [path, content] of Object.entries(files)) {
      // Skip directories (they have zero-length content and trailing /)
      if (path.endsWith("/") || content.length === 0) continue;
      storageWrite("content", path, content, null);
      storedPaths.push(path);
    }

    // Find and save the entry point
    const entryPoint = findEntryPoint(storedPaths);
    setField("entry_point", JSON.stringify(entryPoint));

    const url = entryPoint ? storageUrl("content", entryPoint, null) : "";
    sendEvent("scorm.ready", JSON.stringify(url), null, "view");
  }
  return "";
}

export function getState() {
  const entryPoint = JSON.parse(getField("entry_point"));
  return JSON.stringify({
    entry_url: entryPoint ? storageUrl("content", entryPoint, null) : "",
  });
}
