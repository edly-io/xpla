export class XPLA extends HTMLElement {
  constructor() {
    super();
    this.state = {};
    this.permission = "view";
    this._ws = null;
    this._reconnectDelay = 1000;
  }

  connectedCallback() {
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
    const src = this.getAttribute("src");
    if (src) {
      this.loadScript(src);
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
    const activityName = this.getAttribute("name");
    // Cookies are sent automatically on the WebSocket handshake
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${proto}//${location.host}/api/activity/${activityName}/ws`;
    this._ws = new WebSocket(url);
    this._ws.onopen = () => {
      this._reconnectDelay = 1000;
      this._flushQueue();
      this._setOfflineBanner(false);
    };
    this._ws.onmessage = (e) => {
      const event = JSON.parse(e.data);
      this.onEvent(event.name, JSON.parse(event.value));
    };
    this._ws.onclose = () => {
      this._setOfflineBanner(true);
      this._scheduleReconnect();
    };
  }

  _setOfflineBanner(visible) {
    var elements = document.getElementsByClassName("offline-banner");
    if(visible) {
      for(var element of elements) {
        element.classList.add("offline");
      }
    } else {
      for(var element of elements) {
        element.classList.remove("offline");
      }
    }
  }

  _scheduleReconnect() {
    setTimeout(() => {
      this._reconnectDelay = Math.min(this._reconnectDelay * 2, 30000);
      this._connectWebSocket();
    }, this._reconnectDelay);
  }

  _storageKey() {
    return `xpla:pending:${this.getAttribute("name")}`;
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

  async loadScript(url) {
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
    const key = this._storageKey();
    const pending = JSON.parse(localStorage.getItem(key) || "[]");
    pending.push({ action: name, value });
    localStorage.setItem(key, JSON.stringify(pending));
    if (this._ws.readyState === WebSocket.OPEN) {
      this._flushQueue();
    }
  }

  getAssetUrl(path) {
    return new URL(`/a/${this.getAttribute("name")}/${path}`, location.href).href;
  }

  onEvent(name, value) {
    // Default no-op. Override in client.js to handle events.
  }
}

// Attach elements to classes
customElements.define("xpl-activity", XPLA);
