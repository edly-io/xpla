export class LearningActivity extends HTMLElement {
  constructor() {
    super();
    this.shadow = this.attachShadow({ mode: "closed" });
  }

  connectedCallback() {
    this.render();
    const src = this.getAttribute("src");
    if (src) {
      this.loadScript(src);
    }
  }

  render() {
    this.shadow.innerHTML = `
      <style>
        :host {
          display: block;
        }
        .content {
          padding: 1em;
          border: 1px solid #ccc;
        }
      </style>
      <!-- TODO custom header depth -->
      <h1>
        <slot name="title">Default Title</slot>
      </h1>
      <div class="content">
        <slot name="content"></slot>
      </div>
    `;
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

  async callSandboxFunction(functionName, body) {
    // TODO actually, there shouldn't be any mention of JSON in this function, unless we
    // decide that JSON is actually the data format we want
    const response = await fetch("/api/" + this.attributes.name.value + "/plugin/" + functionName, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(`Plugin call failed: ${response.status}`);
    }

    const data = await response.json();
    return JSON.parse(data.result);
  }
}

class ActivityTitle extends HTMLElement {
  constructor() {
    super();
    this.slot = "title";
  }
}

class ActivityContent extends HTMLElement {
  constructor() {
    super();
    this.slot = "content";
  }
}

// Attach elements to classes
customElements.define("learning-activity", LearningActivity);
// TODO revisit child class names
customElements.define("activity-title", ActivityTitle);
customElements.define("activity-content", ActivityContent);
