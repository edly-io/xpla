// Activity script for Slideshow (reveal.js presentation)
// Embeds reveal.js in iframes for complete CSS/JS isolation.

const DEFAULT_SLIDES = `<section>
  <h2>Welcome</h2>
  <p>Edit this presentation in author mode.</p>
</section>
<section>
  <h2>Slide 2</h2>
  <p>Add more &lt;section&gt; elements for additional slides.</p>
</section>`;

function buildSrcdoc(slidesHtml, assetUrls) {
  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <link rel="stylesheet" href="${assetUrls.resetCss}">
  <link rel="stylesheet" href="${assetUrls.revealCss}">
  <link rel="stylesheet" href="${assetUrls.themeCss}">
  <style>body { margin: 0; }</style>
</head>
<body>
  <div class="reveal"><div class="slides">${slidesHtml}</div></div>
  <script src="${assetUrls.revealJs}"><\/script>
  <script>
    let deck = new Reveal(document.querySelector('.reveal'), {
      keyboardCondition: 'focused',
    });
    deck.initialize();
  <\/script>
</body>
</html>`;
}

export function setup(activity) {
  const element = activity.element;
  const permission = activity.permission;
  const assetUrls = {
    resetCss: activity.getAssetUrl("static/reveal/reset.css"),
    revealCss: activity.getAssetUrl("static/reveal/reveal.css"),
    themeCss: activity.getAssetUrl("static/reveal/theme/white.css"),
    revealJs: activity.getAssetUrl("static/reveal/reveal.js"),
  };

  function getSlidesHtml() {
    return activity.state.slides_html || "";
  }

  activity.onEvent = (name, value) => {
    if (name === "fields.change.slides_html") {
      activity.state.slides_html = value;
      if (permission !== "edit") {
        renderPlayView();
      }
    }
  };

  function render() {
    if (permission === "edit") {
      renderEditView();
    } else {
      renderPlayView();
    }
  }

  function renderEditView() {
    const slidesHtml = getSlidesHtml() || DEFAULT_SLIDES;

    element.innerHTML = `
      <style>
        .slideshow-container { font-family: sans-serif; max-width: 900px; }
        .slides-editor { width: 100%; min-height: 300px; font-family: monospace; font-size: 0.9rem; padding: 0.5rem; box-sizing: border-box; tab-size: 2; }
        .save-btn { margin-top: 0.5rem; padding: 0.5rem 1rem; cursor: pointer; }
        .feedback { margin-top: 0.5rem; padding: 0.5rem; border-radius: 4px; }
        .feedback.success { background: #d4edda; color: #155724; }
        .feedback.error { background: #f8d7da; color: #721c24; }
        .preview-label { font-weight: bold; margin-top: 1rem; }
        .slideshow-preview { margin-top: 0.5rem; }
      </style>
      <div class="slideshow-container">
        <h3>Edit Slides</h3>
        <p style="color: #666; font-size: 0.85rem;">
          Each slide is a <code>&lt;section&gt;</code> element. Nest <code>&lt;section&gt;</code> elements for vertical slides.
        </p>
        <textarea class="slides-editor" id="slides-input">${escapeHtml(slidesHtml)}</textarea>
        <button type="button" class="save-btn" id="save-btn">Save</button>
        <div id="save-feedback"></div>
        <div class="preview-label">Preview:</div>
        <div class="slideshow-preview" id="slideshow-preview"></div>
      </div>
    `;

    element.querySelector("#save-btn").addEventListener("click", async () => {
      const content = element.querySelector("#slides-input").value;
      const feedbackEl = element.querySelector("#save-feedback");
      try {
        await activity.sendAction("config.save", { slides_html: content });
        feedbackEl.innerHTML = '<div class="feedback success">Saved!</div>';
        updatePreview(content);
      } catch (err) {
        feedbackEl.innerHTML = '<div class="feedback error">Error: ' + escapeHtml(err.message) + '</div>';
      }
    });

    updatePreview(slidesHtml);
  }

  function updatePreview(slidesHtml) {
    const container = element.querySelector("#slideshow-preview");
    if (!container) return;
    if (!slidesHtml) {
      container.innerHTML = '<p style="color: #666; font-style: italic;">No slides to preview.</p>';
      return;
    }
    container.innerHTML = '<iframe style="width: 100%; height: 400px; border: 1px solid #ccc;"></iframe>';
    container.querySelector("iframe").srcdoc = buildSrcdoc(slidesHtml, assetUrls);
  }

  function renderPlayView() {
    const slidesHtml = getSlidesHtml();

    element.innerHTML = `
      <style>
        .slideshow-container { font-family: sans-serif; }
        .no-slides { color: #666; font-style: italic; padding: 2rem; text-align: center; }
      </style>
      <div class="slideshow-container">
        ${slidesHtml
          ? '<iframe style="width: 100%; height: 500px; border: none;"></iframe>'
          : '<p class="no-slides">No slides configured yet.</p>'}
      </div>
    `;

    if (slidesHtml) {
      element.querySelector("iframe").srcdoc = buildSrcdoc(slidesHtml, assetUrls);
    }
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  render();
}
