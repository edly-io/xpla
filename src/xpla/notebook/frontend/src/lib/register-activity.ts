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

    async _sendActionHttp(action: { action: string; value: unknown; permission: string }): Promise<void> {
      const url = `/api/activity/${this.context.activity_id}/${this.permission}/actions`;
      try {
        const resp = await fetch(url, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: action.action, value: action.value }),
        });
        if (!resp.ok) {
          console.error("HTTP action failed:", resp.status);
        }
      } catch (err) {
        console.error("HTTP action error:", err);
      }
    }

    getAssetUrl(path: string): string {
      return `/a/${this.context.activity_id}/${path}`;
    }
  }

  customElements.define("xpl-activity", NotebookXPLA as unknown as CustomElementConstructor);
}
