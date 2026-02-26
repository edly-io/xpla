export class XPLA extends HTMLElement {
  constructor() {
    super();
    this.values = {};
    this.permission = "view";
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
      this.values = JSON.parse(stateAttr);
    }

    const permissionAttr = this.getAttribute("data-permission");
    if (permissionAttr) {
      this.permission = permissionAttr;
    }

    this.render();
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
      window.parent.postMessage({ type: "gulps:ready" }, "*");

      const observer = new ResizeObserver(() => {
        window.parent.postMessage(
          { type: "gulps:resize", height: wrapper.scrollHeight },
          "*",
        );
      });
      observer.observe(wrapper);
    }
  }

  render() {
    this.element.innerHTML = "Empty activity";
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

  async sendAction(name, value = "") {
    const response = await fetch("/api/activity/" + this.attributes.name.value + "/actions/" + name, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(value),
    });

    if (!response.ok) {
      throw new Error(`Action send failed: ${response.status}`);
    }

    const data = await response.json();
    this._processEvents(data.events);
    return data.events;
  }

  _processEvents(events) {
    for (const event of events) {
      // Handle values.change.<name> events
      if (event.name.startsWith("values.change.")) {
        const valueName = event.name.slice("values.change.".length);
        const newValue = JSON.parse(event.value);
        this.values[valueName] = newValue;
        this.onValueChange(valueName, newValue);
      }
    }
  }

  getAssetUrl(path) {
    return new URL(`/a/${this.getAttribute("name")}/${path}`, location.href).href;
  }

  onValueChange(name, value) {
    // Default no-op. Override in client.js to handle value changes.
  }
}

// Attach elements to classes
customElements.define("xpla-component", XPLA);
