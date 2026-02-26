// Activity script for Markdown content
// Supports author view (edit markdown) and student view (rendered HTML)

export function setup(activity) {
  const element = activity.element;
  const permission = activity.permission;

  function render() {
    if (permission === "edit") {
      renderEditView();
    } else {
      renderPlayView();
    }
  }

  function renderEditView() {
    const markdown = activity.values.markdown_content || "";
    const html = activity.values.rendered_html || "";

    element.innerHTML = `
      <style>
        .md-container { font-family: sans-serif; max-width: 800px; }
        .md-editor { width: 100%; min-height: 200px; font-family: monospace; padding: 0.5rem; box-sizing: border-box; }
        .save-btn { margin-top: 0.5rem; padding: 0.5rem 1rem; cursor: pointer; }
        .feedback { margin-top: 0.5rem; padding: 0.5rem; border-radius: 4px; }
        .feedback.success { background: #d4edda; color: #155724; }
        .feedback.error { background: #f8d7da; color: #721c24; }
        .md-preview { margin-top: 1rem; padding: 1rem; border: 1px solid #ccc; border-radius: 4px; }
        .md-preview-label { font-weight: bold; margin-top: 1rem; }
        .no-preview { color: #666; font-style: italic; }
      </style>
      <div class="md-container">
        <h3>Edit Markdown Content</h3>
        <textarea class="md-editor" id="md-input">${escapeHtml(markdown)}</textarea>
        <button type="button" class="save-btn" id="save-btn">Save</button>
        <div id="save-feedback"></div>
        <div class="md-preview-label">Preview:</div>
        <div class="md-preview" id="preview">${html || '<span class="no-preview">No content yet.</span>'}</div>
      </div>
    `;

    element.querySelector("#save-btn").addEventListener("click", async () => {
      const content = element.querySelector("#md-input").value;
      const feedbackEl = element.querySelector("#save-feedback");
      try {
        await activity.sendAction("config.save", { markdown_content: content });
        feedbackEl.innerHTML = '<div class="feedback success">Saved!</div>';
      } catch (err) {
        feedbackEl.innerHTML = '<div class="feedback error">Error: ' + escapeHtml(err.message) + '</div>';
      }
    });
  }

  function renderPlayView() {
    const html = activity.values.rendered_html || "";

    element.innerHTML = `
      <style>
        .md-container { font-family: sans-serif; max-width: 800px; }
        .no-content { color: #666; font-style: italic; }
      </style>
      <div class="md-container">
        ${html || '<p class="no-content">No content available yet.</p>'}
      </div>
    `;
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  activity.onEvent = (name, value) => {
    if (name === "values.change.rendered_html") {
      const preview = element.querySelector("#preview");
      if (preview) {
        preview.innerHTML = value || '<span class="no-preview">No content yet.</span>';
      } else {
        activity.values.rendered_html = value;
        renderPlayView();
      }
    } else if (name === "values.change.markdown_content") {
      activity.values.markdown_content = value;
    }
  };

  render();
}
