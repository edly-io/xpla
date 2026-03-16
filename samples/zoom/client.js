// Activity script for Zoom meeting
// Edit mode: configure credentials and meeting details
// Play mode: display meeting info with join button
// View mode: display meeting info without join button

export function setup(activity) {
  const element = activity.element;
  const permission = activity.permission;

  function render() {
    const state = activity.state;

    if (permission === "edit") {
      renderEditView(state);
    } else if (permission === "play") {
      renderPlayView(state);
    } else {
      renderViewView(state);
    }
  }

  function renderEditView(state) {
    const credentialsConfigured = state.credentials_configured;

    element.innerHTML = `
      <style>
        .zoom-container { font-family: sans-serif; max-width: 640px; }
        .zoom-section { border: 1px solid #ccc; border-radius: 4px; padding: 1rem; margin-bottom: 1rem; }
        .zoom-section h3 { margin-top: 0; }
        .zoom-field { margin-bottom: 0.75rem; }
        .zoom-field label { display: block; font-weight: bold; margin-bottom: 0.25rem; }
        .zoom-field input, .zoom-field select { width: 100%; padding: 0.375rem; box-sizing: border-box; }
        .zoom-row { display: flex; gap: 1rem; }
        .zoom-row .zoom-field { flex: 1; }
        .zoom-checkbox { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; }
        .zoom-checkbox label { font-weight: normal; }
        .zoom-btn { padding: 0.5rem 1rem; cursor: pointer; border: none; border-radius: 4px; color: white; }
        .zoom-btn-primary { background: #2d8cff; }
        .zoom-btn-primary:hover { background: #1a73e8; }
        .zoom-feedback { margin-top: 0.75rem; padding: 0.75rem; border-radius: 4px; }
        .zoom-feedback.success { background: #d4edda; color: #155724; }
        .zoom-feedback.error { background: #f8d7da; color: #721c24; }
        .zoom-status { display: inline-block; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.875rem; }
        .zoom-status.configured { background: #d4edda; color: #155724; }
        .zoom-status.not-configured { background: #fff3cd; color: #856404; }
        .zoom-credentials-toggle { cursor: pointer; user-select: none; }
        .zoom-credentials-body { overflow: hidden; }
        .zoom-credentials-body.collapsed { display: none; }
        .zoom-preview { background: #f8f9fa; padding: 1rem; border-radius: 4px; margin-top: 1rem; }
      </style>
      <div class="zoom-container">
        <div class="zoom-section">
          <h3 class="zoom-credentials-toggle" id="cred-toggle">
            Zoom API Credentials
            <span class="zoom-status ${credentialsConfigured ? "configured" : "not-configured"}">
              ${credentialsConfigured ? "Configured" : "Not configured"}
            </span>
          </h3>
          <div class="zoom-credentials-body ${credentialsConfigured ? "collapsed" : ""}" id="cred-body">
            <div class="zoom-field">
              <label for="zoom-account-id">Account ID</label>
              <input type="text" id="zoom-account-id" placeholder="Zoom Account ID">
            </div>
            <div class="zoom-field">
              <label for="zoom-client-id">Client ID</label>
              <input type="text" id="zoom-client-id" placeholder="Zoom Client ID">
            </div>
            <div class="zoom-field">
              <label for="zoom-client-secret">Client Secret</label>
              <input type="password" id="zoom-client-secret" placeholder="Zoom Client Secret">
            </div>
            <button type="button" class="zoom-btn zoom-btn-primary" id="save-credentials">Save Credentials</button>
            <div id="cred-feedback"></div>
          </div>
        </div>

        <div class="zoom-section">
          <h3>Meeting Configuration</h3>
          <div class="zoom-field">
            <label for="zoom-topic">Topic</label>
            <input type="text" id="zoom-topic" value="${escapeAttr(state.topic || "")}">
          </div>
          <div class="zoom-row">
            <div class="zoom-field">
              <label for="zoom-start-time">Start Time</label>
              <input type="datetime-local" id="zoom-start-time" value="${toDatetimeLocal(state.start_time)}">
            </div>
            <div class="zoom-field">
              <label for="zoom-duration">Duration (minutes)</label>
              <input type="number" id="zoom-duration" min="1" max="1440" value="${state.duration || 60}">
            </div>
          </div>
          <div class="zoom-row">
            <div class="zoom-field">
              <label for="zoom-timezone">Timezone</label>
              <select id="zoom-timezone">
                ${timezoneOptions(state.timezone || "UTC")}
              </select>
            </div>
            <div class="zoom-field">
              <label for="zoom-password">Password</label>
              <input type="text" id="zoom-password" value="${escapeAttr(state.password || "")}">
            </div>
          </div>
          <div class="zoom-row">
            <div class="zoom-field">
              <label for="zoom-auto-recording">Auto Recording</label>
              <select id="zoom-auto-recording">
                <option value="none" ${state.auto_recording === "none" ? "selected" : ""}>None</option>
                <option value="local" ${state.auto_recording === "local" ? "selected" : ""}>Local</option>
                <option value="cloud" ${state.auto_recording === "cloud" ? "selected" : ""}>Cloud</option>
              </select>
            </div>
          </div>
          <div class="zoom-checkbox">
            <input type="checkbox" id="zoom-waiting-room" ${state.waiting_room ? "checked" : ""}>
            <label for="zoom-waiting-room">Waiting Room</label>
          </div>
          <div class="zoom-checkbox">
            <input type="checkbox" id="zoom-join-before-host" ${state.join_before_host ? "checked" : ""}>
            <label for="zoom-join-before-host">Join Before Host</label>
          </div>
          <div class="zoom-checkbox">
            <input type="checkbox" id="zoom-mute-upon-entry" ${state.mute_upon_entry ? "checked" : ""}>
            <label for="zoom-mute-upon-entry">Mute Upon Entry</label>
          </div>
          <button type="button" class="zoom-btn zoom-btn-primary" id="save-meeting">Save & Create Meeting</button>
          <div id="meeting-feedback"></div>
        </div>

        ${state.join_url ? `
          <div class="zoom-preview">
            <strong>Meeting created:</strong> <a href="${escapeAttr(state.join_url)}" target="_blank">${escapeHtml(state.join_url)}</a>
          </div>
        ` : ""}
      </div>
    `;

    // Credentials toggle
    element.querySelector("#cred-toggle").addEventListener("click", () => {
      element.querySelector("#cred-body").classList.toggle("collapsed");
    });

    // Save credentials
    element.querySelector("#save-credentials").addEventListener("click", async () => {
      const feedbackEl = element.querySelector("#cred-feedback");
      try {
        await activity.sendAction("credentials.save", {
          zoom_account_id: element.querySelector("#zoom-account-id").value.trim(),
          zoom_client_id: element.querySelector("#zoom-client-id").value.trim(),
          zoom_client_secret: element.querySelector("#zoom-client-secret").value.trim(),
        });
        feedbackEl.innerHTML = '<div class="zoom-feedback success">Credentials saved!</div>';
      } catch (err) {
        feedbackEl.innerHTML = '<div class="zoom-feedback error">Error: ' + escapeHtml(err.message) + '</div>';
      }
    });

    // Save meeting
    element.querySelector("#save-meeting").addEventListener("click", async () => {
      const feedbackEl = element.querySelector("#meeting-feedback");
      const startTimeVal = element.querySelector("#zoom-start-time").value;

      try {
        await activity.sendAction("meeting.save", {
          topic: element.querySelector("#zoom-topic").value.trim(),
          start_time: startTimeVal ? new Date(startTimeVal).toISOString() : "",
          duration: parseInt(element.querySelector("#zoom-duration").value, 10) || 60,
          timezone: element.querySelector("#zoom-timezone").value,
          password: element.querySelector("#zoom-password").value.trim(),
          waiting_room: element.querySelector("#zoom-waiting-room").checked,
          join_before_host: element.querySelector("#zoom-join-before-host").checked,
          mute_upon_entry: element.querySelector("#zoom-mute-upon-entry").checked,
          auto_recording: element.querySelector("#zoom-auto-recording").value,
        });
        feedbackEl.innerHTML = '<div class="zoom-feedback success">Meeting saved!</div>';
      } catch (err) {
        feedbackEl.innerHTML = '<div class="zoom-feedback error">Error: ' + escapeHtml(err.message) + '</div>';
      }
    });
  }

  function renderPlayView(state) {
    renderMeetingCard(state, true);
  }

  function renderViewView(state) {
    renderMeetingCard(state, false);
  }

  function renderMeetingCard(state, showJoinButton) {
    if (!state.topic || !state.join_url) {
      element.innerHTML = `
        <style>
          .zoom-placeholder { font-family: sans-serif; color: #666; font-style: italic; padding: 2rem; text-align: center; }
        </style>
        <div class="zoom-placeholder">No Zoom meeting has been configured yet.</div>
      `;
      return;
    }

    const formattedTime = state.start_time ? formatDateTime(state.start_time, state.timezone) : "TBD";

    element.innerHTML = `
      <style>
        .zoom-card { font-family: sans-serif; max-width: 480px; border: 1px solid #e0e0e0; border-radius: 8px; padding: 1.5rem; }
        .zoom-card h3 { margin-top: 0; margin-bottom: 1rem; }
        .zoom-card-info { margin-bottom: 0.5rem; color: #555; }
        .zoom-card-info strong { color: #333; }
        .zoom-join-btn { display: inline-block; margin-top: 1rem; padding: 0.75rem 1.5rem; background: #2d8cff; color: white; text-decoration: none; border-radius: 4px; font-size: 1rem; }
        .zoom-join-btn:hover { background: #1a73e8; }
      </style>
      <div class="zoom-card">
        <h3>${escapeHtml(state.topic)}</h3>
        <div class="zoom-card-info"><strong>When:</strong> ${escapeHtml(formattedTime)}</div>
        <div class="zoom-card-info"><strong>Duration:</strong> ${state.duration} minutes</div>
        ${showJoinButton ? '<a class="zoom-join-btn" href="' + escapeAttr(state.join_url) + '" target="_blank">Join Meeting</a>' : ""}
      </div>
    `;
  }

  function formatDateTime(isoString, timezone) {
    try {
      const date = new Date(isoString);
      return date.toLocaleString(undefined, {
        dateStyle: "long",
        timeStyle: "short",
        timeZone: timezone || undefined,
      });
    } catch (e) {
      return isoString;
    }
  }

  function toDatetimeLocal(isoString) {
    if (!isoString) return "";
    try {
      const d = new Date(isoString);
      // Format as YYYY-MM-DDTHH:MM for datetime-local input
      const pad = (n) => String(n).padStart(2, "0");
      return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()) +
        "T" + pad(d.getHours()) + ":" + pad(d.getMinutes());
    } catch (e) {
      return "";
    }
  }

  function timezoneOptions(selected) {
    const zones = [
      "UTC", "US/Eastern", "US/Central", "US/Mountain", "US/Pacific",
      "Europe/London", "Europe/Paris", "Europe/Berlin",
      "Asia/Tokyo", "Asia/Shanghai", "Asia/Kolkata",
      "Australia/Sydney", "Pacific/Auckland",
    ];
    return zones.map(
      (tz) => '<option value="' + tz + '"' + (tz === selected ? " selected" : "") + ">" + tz + "</option>"
    ).join("");
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function escapeAttr(str) {
    return str.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  // Handle events from backend
  activity.onEvent = (name, value) => {
    if (name === "meeting.updated") {
      activity.state.topic = value.topic;
      activity.state.start_time = value.start_time;
      activity.state.duration = value.duration;
      activity.state.timezone = value.timezone;
      activity.state.join_url = value.join_url;
      render();
    } else if (name === "credentials.status") {
      activity.state.credentials_configured = value.configured;
      render();
    }
  };

  // Initial render
  render();
}
