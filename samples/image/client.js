// Activity script for Image (upload and display)

export function setup(activity) {
  const element = activity.element;
  const permission = activity.permission;

  activity.onEvent = (name, value) => {
    if (name === "image.changed") {
      activity.state.image_url = value;
      renderImage();
    }
  };

  function renderImage() {
    const img = element.querySelector("#image-display");
    if (!img) return;
    const url = activity.state.image_url;
    if (url) {
      img.src = url;
      img.style.display = "block";
    } else {
      img.style.display = "none";
    }
    const placeholder = element.querySelector("#no-image");
    if (placeholder) {
      placeholder.style.display = url ? "none" : "block";
    }
  }

  function render() {
    const url = activity.state.image_url;
    element.innerHTML = `
      <style>
        .image-container { font-family: sans-serif; max-width: 800px; }
        .image-display { max-width: 100%; height: auto; }
        .no-image { color: #666; font-style: italic; padding: 2rem; text-align: center; }
        .upload-area { margin-bottom: 1rem; }
        .upload-btn { padding: 0.5rem 1rem; cursor: pointer; }
        .feedback { margin-top: 0.5rem; color: #666; font-size: 0.85rem; }
      </style>
      <div class="image-container">
        ${permission === "edit" ? `
          <div class="upload-area">
            <input type="file" accept="image/*" id="file-input">
            <div class="feedback" id="feedback"></div>
          </div>
        ` : ""}
        <img id="image-display" class="image-display"
          src="${url || ""}"
          style="display: ${url ? "block" : "none"}">
        <p id="no-image" class="no-image"
          style="display: ${url ? "none" : "block"}">No image uploaded yet.</p>
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
    feedback.textContent = "Uploading...";

    const reader = new FileReader();
    reader.onload = () => {
      activity.sendAction("image.upload", { data: reader.result });
      feedback.textContent = "Uploaded.";
    };
    reader.onerror = () => {
      feedback.textContent = "Error reading file.";
    };
    reader.readAsDataURL(file);
  }

  render();
}
