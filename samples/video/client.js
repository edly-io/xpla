// Activity script for video player (Video.js)
// Supports author view (configure video URL) and student view (watch video)
//
// Video.js does not support shadow DOM (https://github.com/videojs/video.js/issues/8069),
// so the player is rendered in the light DOM and projected into the shadow DOM via <slot>.

import videojs from "video.js";
import videojsCss from "video.js/dist/video-js.css";

export function setup(activity) {
  const element = activity.shadow;
  const host = activity; // the custom element itself (light DOM)
  const permission = activity.permission;
  let player = null;

  // Inject Video.js CSS into document head (once, for light DOM elements)
  if (!document.querySelector("style[data-videojs]")) {
    const style = document.createElement("style");
    style.dataset.videojs = "";
    style.textContent = videojsCss;
    document.head.appendChild(style);
  }

  function getVideoUrl() {
    return activity.values.video_url || "";
  }

  function render() {
    const videoUrl = getVideoUrl();
    if (permission === "edit") {
      renderEditView(videoUrl);
    } else {
      renderPlayView(videoUrl);
    }
  }

  function renderEditView(videoUrl) {
    disposePlayer();
    clearContent();

    element.innerHTML = `
      <style>
        .video-container { font-family: sans-serif; max-width: 640px; }
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
        <slot name="video-player"></slot>
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
        activity.values.video_url = newUrl;
        feedbackEl.innerHTML = '<div class="feedback success">Saved!</div>';
        render();
      } catch (err) {
        feedbackEl.innerHTML = `<div class="feedback error">Error: ${err.message}</div>`;
      }
    });
  }

  function renderPlayView(videoUrl) {
    disposePlayer();
    clearContent();

    if (videoUrl) {
      element.innerHTML = `
        <style>.video-container { max-width: 640px; }</style>
        <div class="video-container"><slot name="video-player"></slot></div>
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
    const wrapper = document.createElement("div");
    wrapper.setAttribute("slot", "video-player");
    wrapper.dataset.videoplayer = "";

    const video = document.createElement("video");
    video.className = "video-js";
    video.setAttribute("controls", "");
    video.setAttribute("preload", "auto");
    video.setAttribute("width", "640");
    video.setAttribute("height", "360");
    wrapper.appendChild(video);

    // Append to host (light DOM) — projected into shadow DOM via <slot>
    host.appendChild(wrapper);

    player = videojs(video, {
      sources: [{ src: url, type: "video/mp4" }],
    });
  }

  function disposePlayer() {
    if (player) {
      player.dispose();
      player = null;
    }
    // Remove light DOM video elements
    host.querySelectorAll("[data-videoplayer]").forEach((el) => el.remove());
  }

  function clearContent() {
    element.innerHTML = "";
  }

  function escapeAttr(str) {
    return str.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  render();
}
