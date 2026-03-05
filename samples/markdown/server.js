// Markdown plugin - renders Markdown content to HTML via WASM backend
//
// Actions handled:
// - config.save: Save markdown_content and render to HTML

import { sendEvent, getField, setField, getPermission } from "../../src/sandbox-lib";
import { Marked } from "marked";

function renderMarkdown(content, headerStartLevel) {
  const offset = headerStartLevel - 1;
  const marked = new Marked();
  marked.use({
    walkTokens(token) {
      if (token.type === "heading") {
        token.depth = Math.min(token.depth + offset, 6);
      }
    },
  });
  return marked.parse(content);
}

function onAction() {
  const { name, value } = JSON.parse(Host.inputString());

  if (name === "config.save") {
    if (getPermission() !== "edit") {
      console.log("config.save rejected: permission is " + getPermission());
      return;
    }
    const markdownContent = value.markdown_content;
    const headerStartLevel = getField("header_start_level") || 2;
    const html = renderMarkdown(markdownContent, headerStartLevel);

    setField("markdown_content", markdownContent);
    setField("rendered_html", html);
    sendEvent("fields.change.markdown_content", markdownContent, {}, "play");
    sendEvent("fields.change.rendered_html", html, {}, "play");
  }
}

function getState() {
  const state = {
    rendered_html: getField("rendered_html"),
  };
  if (getPermission() === "edit") {
    state.markdown_content = getField("markdown_content");
  }
  Host.outputString(JSON.stringify(state));
}

module.exports = { onAction, getState };
