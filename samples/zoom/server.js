// Zoom meeting activity - creates/manages Zoom meetings via API
//
// Actions handled:
// - credentials.save: Store Zoom API credentials (course-scoped)
// - meeting.save: Save meeting config and create/update via Zoom API

import { sendEvent, getField, setField, httpRequest } from "../../src/sandbox-lib";

function getZoomToken() {
  const accountId = getField("zoom_account_id");
  const clientId = getField("zoom_client_id");
  const clientSecret = getField("zoom_client_secret");

  const credentials = clientId + ":" + clientSecret;
  // btoa is available in Extism JS runtime
  const encoded = btoa(credentials);

  const body = "grant_type=account_credentials&account_id=" + accountId;
  const headers = [
    ["Authorization", "Basic " + encoded],
    ["Content-Type", "application/x-www-form-urlencoded"],
  ];

  const response = httpRequest("https://zoom.us/oauth/token", "POST", body, headers);
  if (response.status !== 200) {
    throw new Error("Zoom OAuth failed (HTTP " + response.status + "): " + response.body);
  }
  const data = JSON.parse(response.body);
  return data.access_token;
}

// Handle incoming actions from frontend
function onAction() {
  const { name, value, permission } = JSON.parse(Host.inputString());

  if (name === "credentials.save") {
    handleCredentialsSave(value, permission);
  } else if (name === "meeting.save") {
    handleMeetingSave(value, permission);
  }
}

// Return state visible to the current user based on permission level.
function getState() {
  const { permission } = JSON.parse(Host.inputString());

  const topic = getField("topic");
  const startTime = getField("start_time");
  const duration = getField("duration");
  const timezone = getField("timezone");
  const joinUrl = getField("join_url");

  const state = { topic, start_time: startTime, duration, timezone, join_url: joinUrl };

  if (permission === "edit") {
    const accountId = getField("zoom_account_id");
    const clientId = getField("zoom_client_id");
    const clientSecret = getField("zoom_client_secret");
    state.credentials_configured = !!(accountId && clientId && clientSecret);
    state.password = getField("password");
    state.waiting_room = getField("waiting_room");
    state.join_before_host = getField("join_before_host");
    state.mute_upon_entry = getField("mute_upon_entry");
    state.auto_recording = getField("auto_recording");
    state.meeting_id = getField("meeting_id");
  }

  Host.outputString(JSON.stringify(state));
}

function handleCredentialsSave(value, permission) {
  if (permission !== "edit") {
    console.log("credentials.save rejected: permission is " + permission);
    return;
  }
  setField("zoom_account_id", value.zoom_account_id);
  setField("zoom_client_id", value.zoom_client_id);
  setField("zoom_client_secret", value.zoom_client_secret);

  const configured = !!(value.zoom_account_id && value.zoom_client_id && value.zoom_client_secret);
  sendEvent("credentials.status", { configured }, {}, "edit");
}

function handleMeetingSave(value, permission) {
  if (permission !== "edit") {
    console.log("meeting.save rejected: permission is " + permission);
    return;
  }

  // Store meeting fields
  setField("topic", value.topic);
  setField("start_time", value.start_time);
  setField("duration", value.duration);
  setField("timezone", value.timezone);
  setField("password", value.password);
  setField("waiting_room", value.waiting_room);
  setField("join_before_host", value.join_before_host);
  setField("mute_upon_entry", value.mute_upon_entry);
  setField("auto_recording", value.auto_recording);

  // Call Zoom API to create meeting
  const token = getZoomToken();
  const meetingBody = JSON.stringify({
    topic: value.topic,
    type: 2, // scheduled meeting
    start_time: value.start_time,
    duration: value.duration,
    timezone: value.timezone,
    password: value.password || undefined,
    settings: {
      waiting_room: value.waiting_room,
      join_before_host: value.join_before_host,
      mute_upon_entry: value.mute_upon_entry,
      auto_recording: value.auto_recording,
    },
  });

  const headers = [
    ["Authorization", "Bearer " + token],
    ["Content-Type", "application/json"],
  ];

  const existingMeetingId = getField("meeting_id");
  let response;
  if (existingMeetingId) {
    // Update existing meeting
    response = httpRequest(
      "https://api.zoom.us/v2/meetings/" + existingMeetingId,
      "PATCH",
      meetingBody,
      headers
    );
    if (response.status !== 204) {
      console.log("Zoom API error (PATCH): HTTP " + response.status + " " + response.body);
      return;
    }
    // PATCH returns 204 with empty body on success; re-fetch to get join_url
    response = httpRequest(
      "https://api.zoom.us/v2/meetings/" + existingMeetingId,
      "GET",
      "",
      headers
    );
  } else {
    // Create new meeting
    response = httpRequest(
      "https://api.zoom.us/v2/users/me/meetings",
      "POST",
      meetingBody,
      headers
    );
  }

  if (response.status < 200 || response.status >= 300) {
    console.log("Zoom API error: HTTP " + response.status + " " + response.body);
    return;
  }

  const meeting = JSON.parse(response.body);

  const meetingId = String(meeting.id);
  const joinUrl = meeting.join_url;

  setField("meeting_id", meetingId);
  setField("join_url", joinUrl);

  sendEvent("meeting.updated", {
    topic: value.topic,
    start_time: value.start_time,
    duration: value.duration,
    timezone: value.timezone,
    join_url: joinUrl,
  }, {}, "play");
}

module.exports = { onAction, getState };
