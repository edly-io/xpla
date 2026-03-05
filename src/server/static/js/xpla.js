export class XPLA extends HTMLElement {
  constructor() {
    super();
    this.state = {};
    this.permission = "view";
    this._ws = null;
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
    this._ws.onmessage = (e) => {
      const event = JSON.parse(e.data);
      this.onEvent(event.name, JSON.parse(event.value));
    };
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
    this._ws.send(JSON.stringify({ action: name, value }));
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
