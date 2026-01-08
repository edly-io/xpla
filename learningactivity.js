class LearningActivity extends HTMLElement {
  constructor() {
    super();
    console.log("Element constructor");
    this.shadow = this.attachShadow({ mode: "closed" });
  }

  connectedCallback() {
    console.log("Element connected callback");
    const child = document.createElement("p");
    child.textContent = "I'm in the shadow DOM";
    this.shadow.appendChild(child);
  }
}

customElements.define("learning-activity", LearningActivity);
