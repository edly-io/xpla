// Activity script for SCORM (upload and display a SCORM package)

export function setup(activity) {
  const element = activity.element;
  const permission = activity.permission;

  activity.onEvent = (name, value) => {
    if (name === "scorm.ready") {
      activity.state.entry_url = value;
      renderIframe();
    }
  };

  function renderIframe() {
    const iframe = element.querySelector("#scorm-frame");
    const placeholder = element.querySelector("#no-content");
    const url = activity.state.entry_url;
    if (iframe) {
      if (url) {
        iframe.src = url;
        iframe.style.display = "block";
      } else {
        iframe.style.display = "none";
      }
    }
    if (placeholder) {
      placeholder.style.display = url ? "none" : "block";
    }
  }

  function render() {
    const url = activity.state.entry_url;
    element.innerHTML = `
      <style>
        .scorm-container { font-family: sans-serif; }
        .scorm-frame { width: 100%; height: 600px; border: 1px solid #ccc; }
        .no-content { color: #666; font-style: italic; padding: 2rem; text-align: center; }
        .upload-area { margin-bottom: 1rem; }
        .feedback { margin-top: 0.5rem; color: #666; font-size: 0.85rem; }
      </style>
      <div class="scorm-container">
        ${permission === "edit" ? `
          <div class="upload-area">
            <label>Upload SCORM package (.zip):
              <input type="file" accept=".zip" id="file-input">
            </label>
            <div class="feedback" id="feedback"></div>
          </div>
        ` : ""}
        <iframe id="scorm-frame" class="scorm-frame"
          src="${url || ""}"
          style="display: ${url ? "block" : "none"}"
          sandbox="allow-scripts allow-same-origin"></iframe>
        <p id="no-content" class="no-content"
          style="display: ${url ? "none" : "block"}">No SCORM package uploaded yet.</p>
      </div>
    `;

    if (permission === "edit") {
      element.querySelector("#file-input").addEventListener("change", onFileSelected);
    }
  }

  function onFileSelected(e) {
    const file = e.target.files[0];
    if (!file) return;

    const feedback = element.querySelector("#feedback");
    feedback.textContent = "Uploading and extracting...";

    const reader = new FileReader();
    reader.onload = () => {
      activity.sendAction("scorm.upload", { data: reader.result });
      feedback.textContent = "Package uploaded.";
    };
    reader.onerror = () => {
      feedback.textContent = "Error reading file.";
    };
    reader.readAsDataURL(file);
  }

  render();
}
