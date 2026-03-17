"use client";

export async function registerXplActivity(): Promise<void> {
  if (typeof window === "undefined") return;
  if (customElements.get("xpl-activity")) return;

  const { XPLA } = await import(/* webpackIgnore: true */ "/static/js/xpla.js");

  class NotebookXPLA extends XPLA {
    _getWebsocketUrl(): string {
      const proto = location.protocol === "https:" ? "wss:" : "ws:";
      const host =
        location.port === "3000"
          ? location.hostname + ":9753"
          : location.host;
      return `${proto}//${host}/api/activity/${this.scope.activity_id}/ws`;
    }

    getAssetUrl(path: string): string {
      const host =
        location.port === "3000"
          ? location.hostname + ":9753"
          : location.host;
      return `${location.protocol}//${host}/a/${this.scope.activity_id}/${path}`;
    }
  }

  customElements.define("xpl-activity", NotebookXPLA);
}
