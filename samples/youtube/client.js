// Activity script for YouTube video embed
// Supports author view (configure video ID) and student view (watch video)

export function setup(activity) {
  const element = activity.element;
  const permission = activity.permission;

  function getVideoId() {
    return activity.state.video_id || "";
  }

  activity.onEvent = (name, value) => {
    if (name === "fields.change.video_id") {
      activity.state.video_id = value;
    }
  };

  function render() {
    const videoId = getVideoId();

    if (permission === "edit") {
      renderEditView(videoId);
    } else {
      renderPlayView(videoId);
    }
  }

  function renderEditView(videoId) {
    element.innerHTML = `
      <style>
        .yt-container { font-family: sans-serif; max-width: 600px; }
        .yt-input { display: flex; gap: 0.5rem; align-items: center; margin-bottom: 1rem; }
        .yt-input input { flex: 1; padding: 0.25rem; }
        .save-btn { padding: 0.5rem 1rem; cursor: pointer; }
        .yt-preview iframe { width: 100%; aspect-ratio: 16/9; border: none; }
        .no-video { color: #666; font-style: italic; }
        .feedback { margin-top: 0.5rem; padding: 0.5rem; border-radius: 4px; }
        .feedback.success { background: #d4edda; color: #155724; }
        .feedback.error { background: #f8d7da; color: #721c24; }
      </style>
      <div class="yt-container">
        <h3>Configure YouTube Video</h3>
        <div class="yt-input">
          <label for="video-id-input">Video ID:</label>
          <input type="text" id="video-id-input" value="${escapeAttr(videoId)}" placeholder="e.g. dQw4w9WgXcQ">
          <button type="button" class="save-btn" id="save-btn">Save</button>
        </div>
        <div id="save-feedback"></div>
        <div class="yt-preview" id="preview"></div>
      </div>
    `;

    renderPreview(videoId);

    element.querySelector("#video-id-input").addEventListener("input", (e) => {
      renderPreview(e.target.value.trim());
    });

    element.querySelector("#save-btn").addEventListener("click", async () => {
      const newVideoId = element.querySelector("#video-id-input").value.trim();
      const feedbackEl = element.querySelector("#save-feedback");
      try {
        await activity.sendAction("config.save", { video_id: newVideoId });
        feedbackEl.innerHTML = '<div class="feedback success">Saved!</div>';
      } catch (err) {
        feedbackEl.innerHTML = `<div class="feedback error">Error: ${err.message}</div>`;
      }
    });
  }

  function renderPreview(videoId) {
    const preview = element.querySelector("#preview");
    if (videoId) {
      preview.innerHTML = `<iframe src="https://www.youtube.com/embed/${encodeURIComponent(videoId)}" allowfullscreen></iframe>`;
    } else {
      preview.innerHTML = '<p class="no-video">No video to preview.</p>';
    }
  }

  function renderPlayView(videoId) {
    element.innerHTML = `
      <style>
        .yt-container { font-family: sans-serif; max-width: 600px; }
        .yt-container iframe { width: 100%; aspect-ratio: 16/9; border: none; }
        .no-video { color: #666; font-style: italic; }
      </style>
      <div class="yt-container">
        ${videoId
          ? `<iframe src="https://www.youtube.com/embed/${encodeURIComponent(videoId)}" allowfullscreen></iframe>`
          : '<p class="no-video">No video configured yet.</p>'}
      </div>
    `;
  }

  function escapeAttr(str) {
    return str.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  render();
}
