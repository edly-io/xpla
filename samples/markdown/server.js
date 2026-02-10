// Markdown plugin - renders Markdown content to HTML via WASM backend
//
// Actions handled:
// - config.save: Save markdown_content and render to HTML

import { postEvent, getValue, setValue, getPermission } from "../../src/sandbox-lib";
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
  const input = JSON.parse(Host.inputString());
  const actionName = input.name;
  const actionValue = input.value;

  if (actionName === "config.save") {
    if (getPermission() !== "edit") {
      console.log("config.save rejected: permission is " + getPermission());
      return;
    }
    const markdownContent = actionValue.markdown_content;
    const headerStartLevel = getValue("header_start_level") || 2;
    const html = renderMarkdown(markdownContent, headerStartLevel);

    setValue("markdown_content", markdownContent);
    setValue("rendered_html", html);
    postEvent("values.change.markdown_content", markdownContent);
    postEvent("values.change.rendered_html", html);
  }
}

function getState() {
  const state = {
    rendered_html: getValue("rendered_html"),
  };
  if (getPermission() === "edit") {
    state.markdown_content = getValue("markdown_content");
  }
  Host.outputString(JSON.stringify(state));
}

module.exports = { onAction, getState };
