// Activity script for math
// Demonstrates event-driven architecture with WASM plugin

// Generate a random math question
function generateQuestion() {
  const ops = ["+", "-", "*"];
  const op = ops[Math.floor(Math.random() * ops.length)];
  let a, b;

  switch (op) {
    case "+":
      a = Math.floor(Math.random() * 50) + 1;
      b = Math.floor(Math.random() * 50) + 1;
      break;
    case "-":
      a = Math.floor(Math.random() * 50) + 10;
      b = Math.floor(Math.random() * a);
      break;
    case "*":
      a = Math.floor(Math.random() * 12) + 1;
      b = Math.floor(Math.random() * 12) + 1;
      break;
  }

  return { expression: `${a} ${op} ${b}`, a, op, b };
}

export function setup(activity) {
  var element = activity.element;
  const canSubmit = activity.permission !== "view";

  element.innerHTML = `
    <style>
      .math-card {
        font-family: sans-serif;
        max-width: 480px;
        margin: 2rem auto;
        padding: 2rem;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.07);
        background: #fff;
      }
      .math-desc {
        color: #666;
        font-size: 0.9rem;
        margin: 0 0 1.5rem;
      }
      .math-score {
        display: flex;
        gap: 0.75rem;
        margin-bottom: 1.5rem;
      }
      .math-score .badge {
        padding: 0.25rem 0.75rem;
        border-radius: 999px;
        font-size: 0.85rem;
        font-weight: 600;
      }
      .badge-correct { background: #d1fae5; color: #065f46; }
      .badge-wrong   { background: #fee2e2; color: #991b1b; }
      .math-question {
        font-size: 1.75rem;
        font-weight: 700;
        text-align: center;
        padding: 1rem;
        background: #f3f4f6;
        border-radius: 8px;
        margin-bottom: 1.5rem;
        letter-spacing: 0.04em;
      }
      .math-input-row {
        display: flex;
        align-items: center;
        gap: 0.75rem;
      }
      .math-input-row label {
        font-size: 0.95rem;
        color: #444;
        white-space: nowrap;
      }
      .math-input-row input[type=number] {
        width: 100px;
        padding: 0.5rem 0.75rem;
        font-size: 1rem;
        border: 1px solid #ccc;
        border-radius: 6px;
        outline: none;
        transition: border-color 0.15s;
      }
      .math-input-row input[type=number]:focus { border-color: #6366f1; }
      .math-input-row button {
        padding: 0.5rem 1.25rem;
        font-size: 1rem;
        background: #6366f1;
        color: #fff;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        transition: background 0.15s;
      }
      .math-input-row button:hover:not(:disabled) { background: #4f46e5; }
      .math-input-row button:disabled,
      .math-input-row input:disabled { opacity: 0.5; cursor: not-allowed; }
      .math-feedback {
        margin-top: 1.25rem;
        padding: 0.75rem 1rem;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.95rem;
      }
      .math-feedback.correct   { background: #d1fae5; color: #065f46; }
      .math-feedback.incorrect { background: #fee2e2; color: #991b1b; }
    </style>

    <div class="math-card">
      <p class="math-desc">Answer the math question below. Your answer will be validated by the WASM backend and your grade will be submitted to the LMS.</p>

      <div class="math-score">
        <span class="badge badge-correct">✓ <span id="correct-count">0</span> correct</span>
        <span class="badge badge-wrong">✗ <span id="wrong-count">0</span> wrong</span>
      </div>

      <form id="quiz-form">
        <div class="math-question" id="question">Loading...</div>
        <div class="math-input-row">
          <label for="answer">Your answer:</label>
          <input type="number" id="answer" name="answer" required ${canSubmit ? "" : "disabled"}>
          <button type="submit" ${canSubmit ? "" : "disabled"}>Submit</button>
        </div>
      </form>

      <div id="feedback" class="math-feedback" style="display: none;"></div>
    </div>
  `;

  const form = element.querySelector("#quiz-form");
  const questionEl = element.querySelector("#question");
  const answerInput = element.querySelector("#answer");
  const feedbackEl = element.querySelector("#feedback");
  const correctCountEl = element.querySelector("#correct-count");
  const wrongCountEl = element.querySelector("#wrong-count");

  // Initialize display with current field values
  correctCountEl.textContent = activity.state.correct_answers || 0;
  wrongCountEl.textContent = activity.state.wrong_answers || 0;

  // Handle events from backend
  activity.onEvent = (name, value) => {
    if (name === "fields.change.correct_answers") {
      correctCountEl.textContent = value;
    } else if (name === "fields.change.wrong_answers") {
      wrongCountEl.textContent = value;
    } else if (name === "answer.result") {
      feedbackEl.style.display = "block";
      feedbackEl.textContent = value.feedback;
      feedbackEl.className = `math-feedback ${value.correct ? "correct" : "incorrect"}`;
    }
  };

  // Initialize with a random question
  let current = generateQuestion();
  questionEl.textContent = `What is ${current.expression}?`;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const userAnswer = answerInput.value.trim();

    try {
      // Send action to backend
      await activity.sendAction(
        "answer.submit",
        { question: current.expression, answer: userAnswer }
      );
    } catch (err) {
      feedbackEl.style.display = "block";
      feedbackEl.textContent = `Error: ${err.message}`;
      feedbackEl.className = "math-feedback incorrect";
    }

    // Generate a new question after a short delay
    setTimeout(() => {
      current = generateQuestion();
      questionEl.textContent = `What is ${current.expression}?`;
      answerInput.value = "";
      feedbackEl.style.display = "none";
    }, 2000);
  });
}
