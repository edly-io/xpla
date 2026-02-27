// Activity script for video player (Plyr)
// Supports author view (configure video URL) and student view (watch video)
//
// Plyr uses SVG <use href="#plyr-play"> references for icons, which don't work
// in shadow DOM (fragment refs resolve against the document root, not the shadow
// root). We work around this by parsing the SVG sprite at init time and replacing
// every <use> element with the actual inline <path> content after Plyr builds
// its controls.

import Plyr from "plyr";
import plyrCss from "plyr/dist/plyr.css";
import plyrSvg from "./node_modules/plyr/dist/plyr.svg";

// Parse the SVG sprite once: build a map of id -> SVG inner content
const iconMap = buildIconMap(plyrSvg);

function buildIconMap(svgText) {
  const map = {};
  const doc = new DOMParser().parseFromString(svgText, "image/svg+xml");
  for (const symbol of doc.querySelectorAll("symbol[id]")) {
    map["#" + symbol.id] = symbol.innerHTML;
  }
  return map;
}

function inlineIcons(root) {
  for (const use of root.querySelectorAll("use")) {
    const href =
      use.getAttribute("href") || use.getAttributeNS("http://www.w3.org/1999/xlink", "href");
    if (href && iconMap[href]) {
      const parent = use.closest("svg");
      if (parent) {
        parent.innerHTML = iconMap[href];
      }
    }
  }
}

export function setup(activity) {
  const element = activity.element;
  const permission = activity.permission;
  let player = null;

  // Inject Plyr CSS into shadow DOM via adoptedStyleSheets
  const sheet = new CSSStyleSheet();
  sheet.replaceSync(plyrCss);
  element.adoptedStyleSheets = [...element.adoptedStyleSheets, sheet];

  function getVideoUrl() {
    return activity.state.video_url || "";
  }

  activity.onEvent = (name, value) => {
    if (name === "values.change.video_url") {
      activity.state.video_url = value;
    }
  };

  function render() {
    const videoUrl = getVideoUrl();
    if (permission === "edit") {
      renderEditView(videoUrl);
    } else {
      renderPlayView(videoUrl);
    }
  }

  function renderEditView(videoUrl) {
    destroyPlayer();
    element.innerHTML = `
      <style>
        // .video-container { font-family: sans-serif; max-width: 640px; }
        .video-input { display: flex; gap: 0.5rem; align-items: center; margin-bottom: 1rem; }
        .video-input input { flex: 1; padding: 0.25rem; }
        .save-btn { padding: 0.5rem 1rem; cursor: pointer; }
        .feedback { margin-top: 0.5rem; padding: 0.5rem; border-radius: 4px; }
        .feedback.success { background: #d4edda; color: #155724; }
        .feedback.error { background: #f8d7da; color: #721c24; }
        .no-video { color: #666; font-style: italic; }
      </style>
      <div class="video-container">
        <h3>Configure Video</h3>
        <div class="video-input">
          <label for="video-url-input">Video URL:</label>
          <input type="text" id="video-url-input" value="${escapeAttr(videoUrl)}" placeholder="https://example.com/video.mp4">
          <button type="button" class="save-btn" id="save-btn">Save</button>
        </div>
        <div id="save-feedback"></div>
        <div id="player-container"></div>
        ${!videoUrl ? '<p class="no-video">No video to preview.</p>' : ""}
      </div>
    `;

    if (videoUrl) {
      createPlayer(videoUrl);
    }

    element.querySelector("#save-btn").addEventListener("click", async () => {
      const newUrl = element.querySelector("#video-url-input").value.trim();
      const feedbackEl = element.querySelector("#save-feedback");
      try {
        await activity.sendAction("config.save", { video_url: newUrl });
        feedbackEl.innerHTML = '<div class="feedback success">Saved!</div>';
        render();
      } catch (err) {
        feedbackEl.innerHTML = `<div class="feedback error">Error: ${err.message}</div>`;
      }
    });
  }

  function renderPlayView(videoUrl) {
    destroyPlayer();
    if (videoUrl) {
      element.innerHTML = `
        <div class="video-container"><div id="player-container"></div></div>
      `;
      createPlayer(videoUrl);
    } else {
      element.innerHTML = `
        <style>.no-video { color: #666; font-style: italic; font-family: sans-serif; }</style>
        <p class="no-video">No video configured yet.</p>
      `;
    }
  }

  function createPlayer(url) {
    const container = element.querySelector("#player-container");
    const video = document.createElement("video");
    video.setAttribute("controls", "");
    video.setAttribute("playsinline", "");
    const source = document.createElement("source");
    source.src = url;
    source.type = "video/mp4";
    video.appendChild(source);
    container.appendChild(video);
    player = new Plyr(video, { loadSprite: false });
    // Replace <use> refs with inline SVG paths (shadow DOM workaround)
    inlineIcons(container);
  }

  function destroyPlayer() {
    if (player) {
      player.destroy();
      player = null;
    }
  }

  function escapeAttr(str) {
    return str.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  render();
}
