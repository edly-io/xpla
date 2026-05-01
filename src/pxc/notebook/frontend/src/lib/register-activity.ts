"use client";

export async function registerPxcActivity(): Promise<void> {
  if (typeof window === "undefined") return;
  if (customElements.get("pxc-activity")) return;

  // @ts-expect-error -- dynamic import of runtime-served JS module
  const { PXC } = await import(/* webpackIgnore: true */ "/static/js/pxc.js");

  class NotebookPXC extends PXC {
    _getWebsocketUrl(): string {
      const proto = location.protocol === "https:" ? "wss:" : "ws:";
      return `${proto}//${location.host}/api/activity/${this.context.activity_id}/${this.permission}/ws`;
    }

    getAssetUrl(path: string): string {
      return `/a/${this.context.activity_id}/${path}`;
    }
  }

  customElements.define("pxc-activity", NotebookPXC as unknown as CustomElementConstructor);
}
