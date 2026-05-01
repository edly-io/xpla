// Reports course activity — queries report statements and returns data for charting

import { reportQuery } from "pxc:sandbox/analytics";
import { getField, sendEvent, setField } from "pxc:sandbox/state";

function getConfig() {
  return JSON.parse(getField("config"));
}

function buildFilters(config) {
  const filters = {};
  if (config.activity_id) filters.activity_id = config.activity_id;
  if (config.activity_name) filters.activity_name = config.activity_name;
  if (config.user_id) filters.user_id = config.user_id;
  if (config.verb) filters.verb = config.verb;
  if (config.before_date) filters.before_date = config.before_date;
  if (config.after_date) filters.after_date = config.after_date;
  return filters;
}

function queryData(config) {
  return JSON.parse(reportQuery(JSON.stringify(buildFilters(config))));
}

export function getState(context, permission) {
  const config = getConfig();
  const data = queryData(config);
  return JSON.stringify({ config, data });
}

export function onAction(name, data, context, permission) {
  if (name === "config.save") {
    if (permission !== "edit") return "";
    const value = JSON.parse(data);
    setField("config", JSON.stringify(value));
    sendEvent("fields.change.config", JSON.stringify(value), null, "play");
    const results = queryData(value);
    sendEvent("data.result", JSON.stringify(results), null, "play");
  } else if (name === "data.refresh") {
    const config = getConfig();
    const results = queryData(config);
    sendEvent("data.result", JSON.stringify(results), null, "play");
  }
  return "";
}
