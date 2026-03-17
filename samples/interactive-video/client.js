// Activity script for Interactive Video
// Combines YouTube video playback with MCQ overlays at configured timestamps

export function setup(activity) {
  const element = activity.element;
  const permission = activity.permission;
  function getConfig() {
    return {
      video_id: activity.state.video_id || "",
      interactions: activity.state.interactions || [],
    };
  }

  // --- Author View ---

  function render() {
    const config = getConfig();

    if (permission === "edit") {
      renderAuthorView(config);
    } else {
      renderPlayerView(config);
    }
  }

  function renderAuthorView(config) {
    const interactionsHtml = config.interactions.map((inter, i) => renderInteractionEditor(inter, i)).join("");

    element.innerHTML = `
      <style>
        .iv-container { font-family: sans-serif; max-width: 700px; }
        .iv-section { padding: 1rem; border: 1px solid #ccc; border-radius: 4px; margin-bottom: 1rem; }
        .iv-input { display: flex; gap: 0.5rem; align-items: center; margin-bottom: 0.5rem; }
        .iv-input input[type="text"] { flex: 1; padding: 0.25rem; }
        .iv-interaction { border: 1px solid #ddd; border-radius: 4px; padding: 0.75rem; margin: 0.5rem 0; background: #f9f9f9; }
        .iv-interaction h4 { margin: 0 0 0.5rem 0; }
        .iv-answer-item { display: flex; align-items: center; gap: 0.5rem; margin: 0.25rem 0; }
        .iv-answer-item input[type="text"] { flex: 1; padding: 0.25rem; }
        .iv-btn { padding: 0.25rem 0.75rem; cursor: pointer; }
        .iv-save-btn { padding: 0.5rem 1rem; cursor: pointer; margin-top: 0.5rem; }
        .iv-preview iframe { width: 100%; aspect-ratio: 16/9; border: none; margin-top: 0.5rem; }
        .iv-feedback { margin-top: 0.5rem; padding: 0.5rem; border-radius: 4px; }
        .iv-feedback.success { background: #d4edda; color: #155724; }
        .iv-feedback.error { background: #f8d7da; color: #721c24; }
      </style>
      <div class="iv-container">
        <div class="iv-section">
          <h3>Configure Interactive Video</h3>
          <div class="iv-input">
            <label for="iv-video-id">YouTube Video ID:</label>
            <input type="text" id="iv-video-id" value="${escapeAttr(config.video_id)}" placeholder="e.g. dQw4w9WgXcQ">
          </div>
          <div class="iv-preview" id="iv-preview"></div>
        </div>
        <div class="iv-section">
          <h3>Interactions</h3>
          <div id="iv-interactions-list">${interactionsHtml}</div>
          <button type="button" class="iv-btn" id="iv-add-interaction">+ Add Interaction</button>
        </div>
        <button type="button" class="iv-save-btn" id="iv-save">Save</button>
        <div id="iv-save-feedback"></div>
      </div>
    `;

    // Preview
    renderVideoPreview(config.video_id);
    element.querySelector("#iv-video-id").addEventListener("input", (e) => {
      renderVideoPreview(e.target.value.trim());
    });

    // Remove buttons
    element.querySelectorAll(".iv-remove-interaction").forEach(attachInteractionRemoveHandler);
    element.querySelectorAll(".iv-remove-answer").forEach(attachAnswerRemoveHandler);

    // Add interaction
    element.querySelector("#iv-add-interaction").addEventListener("click", () => {
      const list = element.querySelector("#iv-interactions-list");
      const idx = list.querySelectorAll(".iv-interaction").length;
      const div = document.createElement("div");
      div.innerHTML = renderInteractionEditor({ time: 0, question: "", answers: ["", ""], correct_answers: [] }, idx);
      const interactionEl = div.firstElementChild;
      list.appendChild(interactionEl);
      interactionEl.querySelectorAll(".iv-remove-answer").forEach(attachAnswerRemoveHandler);
      attachInteractionRemoveHandler(interactionEl.querySelector(".iv-remove-interaction"));
      attachAddAnswerHandler(interactionEl.querySelector(".iv-add-answer"));
    });

    // Add answer buttons for existing interactions
    element.querySelectorAll(".iv-add-answer").forEach(attachAddAnswerHandler);

    // Save
    element.querySelector("#iv-save").addEventListener("click", async () => {
      const videoId = element.querySelector("#iv-video-id").value.trim();
      const interactionEls = element.querySelectorAll(".iv-interaction");
      const interactions = [];

      interactionEls.forEach((el) => {
        const time = parseFloat(el.querySelector(".iv-time").value) || 0;
        const question = el.querySelector(".iv-question").value.trim();
        const answerItems = el.querySelectorAll(".iv-answer-item");
        const answers = [];
        const correct_answers = [];

        answerItems.forEach((item) => {
          const text = item.querySelector(".iv-answer-text").value.trim();
          if (text) {
            const newIndex = answers.length;
            answers.push(text);
            if (item.querySelector(".iv-correct-cb").checked) {
              correct_answers.push(newIndex);
            }
          }
        });

        interactions.push({ time, question, answers, correct_answers });
      });

      const feedbackEl = element.querySelector("#iv-save-feedback");
      try {
        await activity.sendAction("config.save", { video_id: videoId, interactions });
        feedbackEl.innerHTML = '<div class="iv-feedback success">Configuration saved!</div>';
      } catch (err) {
        feedbackEl.innerHTML = `<div class="iv-feedback error">Error: ${err.message}</div>`;
      }
    });
  }

  function renderInteractionEditor(inter, index) {
    const answersHtml = inter.answers.map((ans, ai) => `
      <div class="iv-answer-item">
        <input type="checkbox" class="iv-correct-cb" ${inter.correct_answers.includes(ai) ? "checked" : ""}>
        <input type="text" class="iv-answer-text" value="${escapeAttr(ans)}">
        <button type="button" class="iv-remove-answer iv-btn">Remove</button>
      </div>
    `).join("");

    return `
      <div class="iv-interaction" data-index="${index}">
        <h4>
          Interaction ${index + 1}
          <button type="button" class="iv-remove-interaction iv-btn" style="float:right;">Remove</button>
        </h4>
        <div class="iv-input">
          <label>Time (seconds):</label>
          <input type="number" class="iv-time" value="${inter.time}" min="0" step="1" style="width:80px;">
        </div>
        <div>
          <label>Question:</label><br>
          <textarea class="iv-question" rows="2" style="width:100%;margin-top:0.25rem;">${escapeHtml(inter.question)}</textarea>
        </div>
        <div style="margin-top:0.5rem;">
          <strong>Answers:</strong> <em>(check correct ones)</em>
          <div class="iv-answers-list">${answersHtml}</div>
          <button type="button" class="iv-add-answer iv-btn">+ Add Answer</button>
        </div>
      </div>
    `;
  }

  function attachInteractionRemoveHandler(btn) {
    btn.addEventListener("click", () => {
      btn.closest(".iv-interaction").remove();
    });
  }

  function attachAnswerRemoveHandler(btn) {
    btn.addEventListener("click", () => {
      btn.closest(".iv-answer-item").remove();
    });
  }

  function attachAddAnswerHandler(btn) {
    btn.addEventListener("click", () => {
      const list = btn.previousElementSibling;
      const item = document.createElement("div");
      item.className = "iv-answer-item";
      item.innerHTML = `
        <input type="checkbox" class="iv-correct-cb">
        <input type="text" class="iv-answer-text" value="">
        <button type="button" class="iv-remove-answer iv-btn">Remove</button>
      `;
      list.appendChild(item);
      attachAnswerRemoveHandler(item.querySelector(".iv-remove-answer"));
    });
  }

  function renderVideoPreview(videoId) {
    const preview = element.querySelector("#iv-preview");
    if (!preview) return;
    if (videoId) {
      preview.innerHTML = `<iframe src="https://www.youtube.com/embed/${encodeURIComponent(videoId)}" allowfullscreen></iframe>`;
    } else {
      preview.innerHTML = "";
    }
  }

  // --- Player View (student/view) ---

  let player = null;
  let pollInterval = null;
  const completedInteractions = new Set();
  let activeOverlayIndex = -1;

  function renderPlayerView(config) {
    if (!config.video_id) {
      element.innerHTML = `
        <style>.iv-container { font-family: sans-serif; max-width: 700px; } .iv-no-config { color: #666; font-style: italic; }</style>
        <div class="iv-container"><p class="iv-no-config">No video configured yet.</p></div>
      `;
      return;
    }

    element.innerHTML = `
      <style>
        .iv-container { font-family: sans-serif; max-width: 700px; }
        .iv-player-wrap { position: relative; width: 100%; }
        .iv-player-wrap iframe, .iv-player-wrap > div { width: 100%; aspect-ratio: 16/9; }
        .iv-overlay {
          position: absolute; top: 0; left: 0; width: 100%; height: 100%;
          background: rgba(0,0,0,0.85); display: flex; align-items: center; justify-content: center;
          z-index: 10;
        }
        .iv-overlay-content {
          background: #fff; border-radius: 8px; padding: 1.5rem; max-width: 90%; max-height: 90%;
          overflow-y: auto; min-width: 300px;
        }
        .iv-overlay-content h3 { margin-top: 0; }
        .iv-overlay-answer { display: flex; align-items: center; gap: 0.5rem; margin: 0.5rem 0; }
        .iv-submit-btn { padding: 0.5rem 1rem; cursor: pointer; margin-top: 0.75rem; }
        .iv-result { margin-top: 0.75rem; padding: 0.75rem; border-radius: 4px; }
        .iv-result.correct { background: #d4edda; color: #155724; }
        .iv-result.incorrect { background: #f8d7da; color: #721c24; }
        .iv-progress { margin-top: 0.5rem; font-size: 0.85rem; color: #666; }
      </style>
      <div class="iv-container">
        <div class="iv-player-wrap">
          <div id="iv-yt-player"></div>
          <div id="iv-overlay" class="iv-overlay" style="display:none;"></div>
        </div>
        <div class="iv-progress" id="iv-progress"></div>
      </div>
    `;

    loadYouTubeAPI().then(() => {
      const playerEl = element.querySelector("#iv-yt-player");
      player = new YT.Player(playerEl, {
        videoId: config.video_id,
        playerVars: { rel: 0 },
        events: {
          onReady: () => { startPolling(config); },
          onStateChange: (event) => {
            // If playing and there's an active unanswered interaction, pause
            if (event.data === YT.PlayerState.PLAYING && activeOverlayIndex >= 0) {
              player.pauseVideo();
            }
          },
        },
      });
    });

    updateProgress(config);
  }

  function startPolling(config) {
    const sorted = config.interactions
      .map((inter, i) => ({ ...inter, originalIndex: i }))
      .sort((a, b) => a.time - b.time);

    pollInterval = setInterval(() => {
      if (!player || typeof player.getCurrentTime !== "function") return;
      if (activeOverlayIndex >= 0) return; // overlay is showing

      const currentTime = player.getCurrentTime();

      for (const inter of sorted) {
        if (completedInteractions.has(inter.originalIndex)) continue;
        if (Math.abs(currentTime - inter.time) < 0.75) {
          triggerInteraction(inter, config);
          break;
        }
      }
    }, 250);
  }

  function triggerInteraction(inter, config) {
    activeOverlayIndex = inter.originalIndex;
    player.pauseVideo();

    const overlay = element.querySelector("#iv-overlay");
    const canSubmit = permission !== "view";
    const answersHtml = inter.answers.map((ans, i) => `
      <div class="iv-overlay-answer">
        <input type="checkbox" id="iv-oa-${i}" data-index="${i}" ${canSubmit ? "" : "disabled"}>
        <label for="iv-oa-${i}">${escapeHtml(ans)}</label>
      </div>
    `).join("");

    overlay.innerHTML = `
      <div class="iv-overlay-content">
        <h3>${escapeHtml(inter.question)}</h3>
        ${answersHtml}
        ${canSubmit ? '<button type="button" class="iv-submit-btn" id="iv-overlay-submit">Submit</button>' : ""}
        <div id="iv-overlay-result"></div>
      </div>
    `;
    overlay.style.display = "flex";

    if (canSubmit) {
      overlay.querySelector("#iv-overlay-submit").addEventListener("click", async () => {
        const checkboxes = overlay.querySelectorAll('input[type="checkbox"]:checked');
        const selected = Array.from(checkboxes).map((cb) => parseInt(cb.dataset.index, 10));
        try {
          await activity.sendAction("answer.submit", { index: inter.originalIndex, selected });
        } catch (err) {
          const resultEl = overlay.querySelector("#iv-overlay-result");
          resultEl.innerHTML = `<div class="iv-result incorrect">Error: ${err.message}</div>`;
        }
      });
    }
  }

  function hideOverlayAndResume(config) {
    const overlay = element.querySelector("#iv-overlay");
    if (overlay) overlay.style.display = "none";
    activeOverlayIndex = -1;
    if (player && typeof player.playVideo === "function") {
      player.playVideo();
    }
    updateProgress(config);
  }

  function updateProgress(config) {
    const el = element.querySelector("#iv-progress");
    if (!el) return;
    const total = config.interactions.length;
    if (total === 0) {
      el.textContent = "";
      return;
    }
    el.textContent = `Questions answered: ${completedInteractions.size} / ${total}`;
  }

  function cleanup() {
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
    if (player && typeof player.destroy === "function") {
      player.destroy();
      player = null;
    }
    activeOverlayIndex = -1;
  }

  // --- YouTube IFrame API loader ---

  let ytReadyPromise = null;

  function loadYouTubeAPI() {
    if (ytReadyPromise) return ytReadyPromise;

    if (window.YT && window.YT.Player) {
      ytReadyPromise = Promise.resolve();
      return ytReadyPromise;
    }

    ytReadyPromise = new Promise((resolve) => {
      const prev = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = () => {
        if (prev) prev();
        resolve();
      };

      if (!document.querySelector('script[src*="youtube.com/iframe_api"]')) {
        const tag = document.createElement("script");
        tag.src = "https://www.youtube.com/iframe_api";
        document.head.appendChild(tag);
      }
    });

    return ytReadyPromise;
  }

  // --- Utility ---

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function escapeAttr(str) {
    return str.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  // --- Events ---

  activity.onEvent = (name, value) => {
    const config = getConfig();

    if (name === "answer.result") {
      const overlay = element.querySelector("#iv-overlay");
      if (overlay && activeOverlayIndex === value.index) {
        const resultEl = overlay.querySelector("#iv-overlay-result");
        if (resultEl) {
          resultEl.innerHTML = `<div class="iv-result ${value.correct ? "correct" : "incorrect"}">${escapeHtml(value.feedback)}</div>`;
        }
        const submitBtn = overlay.querySelector("#iv-overlay-submit");
        if (value.correct) {
          if (submitBtn) submitBtn.disabled = true;
          completedInteractions.add(value.index);
          setTimeout(() => hideOverlayAndResume(config), 2000);
        } else {
          if (submitBtn) submitBtn.disabled = true;
          setTimeout(() => { if (submitBtn) submitBtn.disabled = false; }, 1500);
        }
      }
    } else if (name === "fields.change.video_id") {
      activity.state.video_id = value;
    } else if (name === "fields.change.interactions") {
      activity.state.interactions = value;
    }
  };

  // Initial render
  render();
}
