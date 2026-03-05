"use client";

import { useRef, useEffect } from "react";

type XplActivityProps = {
  activityId: string;
  activityType: string;
  clientPath: string;
  state: unknown;
  permission: string;
};

let scriptLoaded = false;

export function XplActivity({ activityId, activityType, clientPath, state, permission }: XplActivityProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!scriptLoaded) {
      const script = document.createElement("script");
      script.type = "module";
      script.textContent = `
        import { XPLA } from "/static/js/xpla.js";
        class NotebookXPLA extends XPLA {
          sendAction(name, value = "") {
            this._pushAction({ action: name, value, permission: this.permission });
          }
          _getWebsocketUrl() {
            const activityId = this.getAttribute("data-activity-id");
            const proto = location.protocol === "https:" ? "wss:" : "ws:";
            const host = location.port === "3000" ? location.hostname + ":9753" : location.host;
            return proto + "//" + host + "/api/activity/" + activityId + "/ws";
          }
          getAssetUrl(path) {
            const activityId = this.getAttribute("data-activity-id");
            const host = location.port === "3000" ? location.hostname + ":9753" : location.host;
            return location.protocol + "//" + host + "/a/" + activityId + "/" + path;
          }
        }
        if (!customElements.get("xpl-activity")) {
          customElements.define("xpl-activity", NotebookXPLA);
        }
      `;
      document.head.appendChild(script);
      scriptLoaded = true;
    }
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    container.innerHTML = "";
    const el = document.createElement("xpl-activity");
    el.setAttribute("name", activityType);
    el.setAttribute("src", `/a/${activityId}/${clientPath}`);
    el.setAttribute("data-activity-id", activityId);
    el.setAttribute("data-state", JSON.stringify(state));
    el.setAttribute("data-permission", permission);
    container.appendChild(el);
  }, [activityId, activityType, clientPath, state, permission]);

  return <div ref={containerRef} />;
}
