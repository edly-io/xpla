export class LearningActivity extends HTMLElement {
  constructor() {
    super();
    console.log("Element constructor");
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
// Attach <learning-activity> elements to the LearningActivity component
customElements.define("learning-activity", LearningActivity);
