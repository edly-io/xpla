// Markdown plugin - renders Markdown content to HTML via WASM backend
//
// Actions handled:
// - config.save: Save markdown_content and render to HTML

import { sendEvent, getField, setField } from "xpla:sandbox/host";
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

export function onAction(name, data, context, permission) {
  const value = JSON.parse(data);
  if (name === "config.save") {
    if (permission !== "edit") {
      console.log("config.save rejected: permission is " + permission);
      return;
    }
    const markdownContent = value.markdown_content;
    const headerStartLevel = JSON.parse(getField("header_start_level")) || 2;
    const html = renderMarkdown(markdownContent, headerStartLevel);

    setField("markdown_content", JSON.stringify(markdownContent));
    setField("rendered_html", JSON.stringify(html));
    sendEvent("fields.change.markdown_content", JSON.stringify(markdownContent), null, "play");
    sendEvent("fields.change.rendered_html", JSON.stringify(html), null, "play");
  }
}

export function getState(context, permission) {
  const state = {
    rendered_html: JSON.parse(getField("rendered_html")),
  };
  if (permission === "edit") {
    state.markdown_content = JSON.parse(getField("markdown_content"));
  }
  return JSON.stringify(state);
}
