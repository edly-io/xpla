// Client script for chat activity
// Displays messages, input form, listens for chat.new events

export function setup(activity) {
  const element = activity.element;
  const messages = activity.state.messages || [];

  function render() {
    element.innerHTML = `
      <style>
        .chat-container { font-family: sans-serif; max-width: 500px; }
        .chat-messages { border: 1px solid #ccc; border-radius: 4px; padding: 0.5rem; height: 300px; overflow-y: auto; margin-bottom: 0.5rem; }
        .chat-msg { margin: 0.25rem 0; }
        .chat-msg strong { color: #333; }
        .chat-form { display: flex; gap: 0.5rem; }
        .chat-form input { flex: 1; padding: 0.5rem; }
        .chat-form button { padding: 0.5rem 1rem; }
      </style>
      <div class="chat-container">
        <div class="chat-messages" id="chat-messages"></div>
        <form class="chat-form" id="chat-form">
          <input type="text" id="chat-input" placeholder="Type a message..." autocomplete="off">
          <button type="submit">Send</button>
        </form>
      </div>
    `;

    const messagesEl = element.querySelector("#chat-messages");
    for (const msg of messages) {
      appendMessage(messagesEl, msg.value);
    }

    element.querySelector("#chat-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const input = element.querySelector("#chat-input");
      const text = input.value.trim();
      if (!text) return;
      input.value = "";
      await activity.sendAction("chat.post", { text });
    });
  }

  function appendMessage(container, msg) {
    const div = document.createElement("div");
    div.className = "chat-msg";
    div.innerHTML = `<strong>${escapeHtml(msg.user)}:</strong> ${escapeHtml(msg.text)}`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  activity.onEvent = (name, value) => {
    if (name === "chat.new") {
      const container = element.querySelector("#chat-messages");
      if (container) {
        appendMessage(container, value);
      }
    }
  };

  render();
}
