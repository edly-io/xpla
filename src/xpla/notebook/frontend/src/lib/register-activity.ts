"use client";

export async function registerXplActivity(): Promise<void> {
  if (typeof window === "undefined") return;
  if (customElements.get("xpl-activity")) return;

  // @ts-expect-error -- dynamic import of runtime-served JS module
  const { XPLA } = await import(/* webpackIgnore: true */ "/static/js/xpla.js");

  class NotebookXPLA extends XPLA {
    _getWebsocketUrl(): string {
      const proto = location.protocol === "https:" ? "wss:" : "ws:";
      return `${proto}//${location.host}/api/activity/${this.context.activity_id}/${this.permission}/ws`;
    }

    getAssetUrl(path: string): string {
      return `/a/${this.context.activity_id}/${path}`;
    }
  }

  customElements.define("xpl-activity", NotebookXPLA as unknown as CustomElementConstructor);
}
