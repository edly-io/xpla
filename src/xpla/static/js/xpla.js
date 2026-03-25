// Actions larger than this (in JSON-serialized bytes) are sent via HTTP
// instead of WebSocket, to avoid WebSocket frame-size limitations.
const HTTP_SIZE_THRESHOLD = 1_000_000;

export class XPLA extends HTMLElement {
  constructor() {
    super();
    this.context = {};
    this.state = {};
    this.permission = "view";
    this._ws = null;
    this._reconnectDelay = 500;
  }

  connectedCallback() {
    const contextAttr = this.getAttribute("data-context");
    if (contextAttr) {
      this.context = JSON.parse(contextAttr);
    }

    const embedMode = this.getAttribute("embed") || "shadow";

    if (embedMode === "native") {
      this._initNative();
    } else {
      this._initShadow();
    }

    const stateAttr = this.getAttribute("data-state");
    if (stateAttr) {
      this.state = JSON.parse(stateAttr);
    }

    const permissionAttr = this.getAttribute("data-permission");
    if (permissionAttr) {
      this.permission = permissionAttr;
    }

    this.render();
    this._connectWebSocket();
    const src = this.getAttribute("data-src");
    if (src) {
      this._loadScript(src);
    }
  }

  _initShadow() {
    this.element = this.attachShadow({ mode: "closed" });
    var sheet = new CSSStyleSheet();
    // TODO how to pass CSS from the host to the shadow element? Should this be part of the standard?
    sheet.replaceSync(`
      :host {
          display: block;
          padding: 1em;
          border: 1px solid #ccc;
        }
    `);
    this.element.adoptedStyleSheets = [sheet];
  }

  _initNative() {
    const wrapper = document.createElement("div");
    this.appendChild(wrapper);
    this.element = wrapper;

    // Shim adoptedStyleSheets on the wrapper div — delegate to document
    Object.defineProperty(wrapper, "adoptedStyleSheets", {
      get() {
        return document.adoptedStyleSheets;
      },
      set(sheets) {
        document.adoptedStyleSheets = sheets;
      },
    });

    // If inside an iframe, send ready/resize messages to parent
    if (window.parent !== window) {
      window.parent.postMessage({ type: "xpla:ready" }, "*");

      const observer = new ResizeObserver(() => {
        window.parent.postMessage(
          { type: "xpla:resize", height: wrapper.scrollHeight },
          "*",
        );
      });
      observer.observe(wrapper);
    }
  }

  render() {
    this.element.innerHTML = "Empty activity";
  }

  _connectWebSocket() {
    // Cookies are sent automatically on the WebSocket handshake
    this._ws = new WebSocket(this._getWebsocketUrl());
    this._ws.onopen = () => {
      this._reconnectDelay = 500;
      this._flushQueue();
      this._setOfflineBanner(false);
    };
    this._ws.onmessage = (e) => {
      const event = JSON.parse(e.data);
      this.onEvent(event.name, JSON.parse(event.value));
    };
    this._ws.onclose = () => {
      if (this.isConnected) {
        // Only attempt to reconnect when the activity is in the DOM
        this._setOfflineBanner(true);
        this._scheduleReconnect();
      }
    };
  }

  _getWebsocketUrl() {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    return `${proto}//${location.host}/api/activity/${this.context.activity_id}/ws`;
  }

  _setOfflineBanner(visible) {
    var elements = document.getElementsByClassName("offline-banner");
    for (var element of elements) {
      if (visible) {
        element.classList.add("offline");
      } else {
        element.classList.remove("offline");
      }
    }
  }

  _scheduleReconnect() {
    setTimeout(() => {
      this._reconnectDelay = Math.min(this._reconnectDelay * 2, 2000);
      this._connectWebSocket();
    }, this._reconnectDelay);
  }

  _storageKey() {
    return `xpla:pending:${this.context.activity_id}`;
  }

  _flushQueue() {
    const key = this._storageKey();
    let pending = JSON.parse(localStorage.getItem(key) || "[]");
    while (pending.length > 0 && this._ws.readyState === WebSocket.OPEN) {
      const item = pending.shift();
      this._ws.send(JSON.stringify(item));
      localStorage.setItem(key, JSON.stringify(pending));
    }
  }

  async _sendActionHttp(action) {
    const url = `/api/activity/${this.context.activity_id}/actions/${encodeURIComponent(action.action)}`;
    try {
      const resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(action.value),
      });
      if (!resp.ok) {
        console.error("HTTP action failed:", resp.status);
      }
    } catch (err) {
      console.error("HTTP action error:", err);
    }
  }

  async _loadScript(url) {
    try {
      const module = await import(url);
      if (typeof module.setup === "function") {
        module.setup(this);
      }
    } catch (error) {
      console.error("Failed to load activity script:", error);
    }
  }

  sendAction(name, value = "") {
    const action = { action: name, value, permission: this.permission };
    const payload = JSON.stringify(action);
    if (payload.length > HTTP_SIZE_THRESHOLD) {
      // Large payloads bypass the localStorage queue (which has a ~5MB
      // limit) and are sent directly via HTTP POST.
      this._sendActionHttp(action);
    } else {
      this._pushAction(action);
    }
  }

  _pushAction(action) {
    const key = this._storageKey();
    const pending = JSON.parse(localStorage.getItem(key) || "[]");
    pending.push(action);
    localStorage.setItem(key, JSON.stringify(pending));
    if (this._ws.readyState === WebSocket.OPEN) {
      this._flushQueue();
    }
  }

  getAssetUrl(path) {
    return new URL(`/a/${this.context.activity_id}/${path}`, location.href).href;
  }

  onEvent(name, value) {
    // Default no-op. Override in client.js to handle events.
  }

  disconnectedCallback() {
    if (this._ws) {
      // Disconnect from websocket on removal from DOM
      this._ws.close();
    }
  }
}
