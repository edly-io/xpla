export class LearningActivity extends HTMLElement {
  constructor() {
    super();
    this.shadow = this.attachShadow({ mode: "closed" });
  }

  connectedCallback() {
    console.log("Element connected callback");
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
