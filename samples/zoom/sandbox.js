// Zoom meeting activity - creates/manages Zoom meetings via API
//
// Actions handled:
// - credentials.save: Store Zoom API credentials (course-scoped)
// - meeting.save: Save meeting config and create/update via Zoom API

import { httpRequest } from "pxc:sandbox/http";
import { getField, sendEvent, setField } from "pxc:sandbox/state";

function getZoomToken() {
  const accountId = JSON.parse(getField("zoom_account_id"));
  const clientId = JSON.parse(getField("zoom_client_id"));
  const clientSecret = JSON.parse(getField("zoom_client_secret"));

  const credentials = clientId + ":" + clientSecret;
  const encoded = btoa(credentials);

  const body = "grant_type=account_credentials&account_id=" + accountId;
  const headers = [
    ["Authorization", "Basic " + encoded],
    ["Content-Type", "application/x-www-form-urlencoded"],
  ];

  const response = JSON.parse(httpRequest("https://zoom.us/oauth/token", "POST", body, JSON.stringify(headers)));
  if (response.status !== 200) {
    throw new Error("Zoom OAuth failed (HTTP " + response.status + "): " + response.body);
  }
  const data = JSON.parse(response.body);
  return data.access_token;
}

// Handle incoming actions from frontend
export function onAction(name, data, context, permission) {
  const value = JSON.parse(data);
  if (name === "credentials.save") {
    handleCredentialsSave(value, permission);
  } else if (name === "meeting.save") {
    handleMeetingSave(value, permission);
  }
  return "";
}

// Return state visible to the current user based on permission level.
export function getState(context, permission) {
  const topic = JSON.parse(getField("topic"));
  const startTime = JSON.parse(getField("start_time"));
  const duration = JSON.parse(getField("duration"));
  const timezone = JSON.parse(getField("timezone"));
  const joinUrl = JSON.parse(getField("join_url"));

  const state = { topic, start_time: startTime, duration, timezone, join_url: joinUrl };

  if (permission === "edit") {
    const accountId = JSON.parse(getField("zoom_account_id"));
    const clientId = JSON.parse(getField("zoom_client_id"));
    const clientSecret = JSON.parse(getField("zoom_client_secret"));
    state.credentials_configured = !!(accountId && clientId && clientSecret);
    state.password = JSON.parse(getField("password"));
    state.waiting_room = JSON.parse(getField("waiting_room"));
    state.join_before_host = JSON.parse(getField("join_before_host"));
    state.mute_upon_entry = JSON.parse(getField("mute_upon_entry"));
    state.auto_recording = JSON.parse(getField("auto_recording"));
    state.meeting_id = JSON.parse(getField("meeting_id"));
  }

  return JSON.stringify(state);
}

function handleCredentialsSave(value, permission) {
  if (permission !== "edit") {
    console.log("credentials.save rejected: permission is " + permission);
    return;
  }
  setField("zoom_account_id", JSON.stringify(value.zoom_account_id));
  setField("zoom_client_id", JSON.stringify(value.zoom_client_id));
  setField("zoom_client_secret", JSON.stringify(value.zoom_client_secret));

  const configured = !!(value.zoom_account_id && value.zoom_client_id && value.zoom_client_secret);
  sendEvent("credentials.status", JSON.stringify({ configured }), null, "edit");
}

function handleMeetingSave(value, permission) {
  if (permission !== "edit") {
    console.log("meeting.save rejected: permission is " + permission);
    return;
  }

  // Store meeting fields
  setField("topic", JSON.stringify(value.topic));
  setField("start_time", JSON.stringify(value.start_time));
  setField("duration", JSON.stringify(value.duration));
  setField("timezone", JSON.stringify(value.timezone));
  setField("password", JSON.stringify(value.password));
  setField("waiting_room", JSON.stringify(value.waiting_room));
  setField("join_before_host", JSON.stringify(value.join_before_host));
  setField("mute_upon_entry", JSON.stringify(value.mute_upon_entry));
  setField("auto_recording", JSON.stringify(value.auto_recording));

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
  const headersStr = JSON.stringify(headers);

  const existingMeetingId = JSON.parse(getField("meeting_id"));
  let response;
  if (existingMeetingId) {
    // Update existing meeting
    response = JSON.parse(httpRequest(
      "https://api.zoom.us/v2/meetings/" + existingMeetingId,
      "PATCH",
      meetingBody,
      headersStr
    ));
    if (response.status !== 204) {
      console.log("Zoom API error (PATCH): HTTP " + response.status + " " + response.body);
      return;
    }
    // PATCH returns 204 with empty body on success; re-fetch to get join_url
    response = JSON.parse(httpRequest(
      "https://api.zoom.us/v2/meetings/" + existingMeetingId,
      "GET",
      "",
      headersStr
    ));
  } else {
    // Create new meeting
    response = JSON.parse(httpRequest(
      "https://api.zoom.us/v2/users/me/meetings",
      "POST",
      meetingBody,
      headersStr
    ));
  }

  if (response.status < 200 || response.status >= 300) {
    console.log("Zoom API error: HTTP " + response.status + " " + response.body);
    return;
  }

  const meeting = JSON.parse(response.body);

  const meetingId = String(meeting.id);
  const joinUrl = meeting.join_url;

  setField("meeting_id", JSON.stringify(meetingId));
  setField("join_url", JSON.stringify(joinUrl));

  sendEvent("meeting.updated", JSON.stringify({
    topic: value.topic,
    start_time: value.start_time,
    duration: value.duration,
    timezone: value.timezone,
    join_url: joinUrl,
  }), null, "play");
}
