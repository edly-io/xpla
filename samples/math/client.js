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

  element.innerHTML = `
    <p>Answer the math question below. Your answer will be validated by the WASM backend and your grade will be submitted to the LMS.</p>

    <div id="score">
      Correct: <span id="correct-count">0</span> |
      Wrong: <span id="wrong-count">0</span>
    </div>

    <form id="quiz-form">
      <div class="question" id="question">Loading...</div>
      <label for="answer">Your answer: </label>
      <input type="number" id="answer" name="answer" required>
      <button type="submit">Submit</button>
    </form>

    <div id="feedback" style="display: none;"></div>
  `;

  const form = element.querySelector("#quiz-form");
  const questionEl = element.querySelector("#question");
  const answerInput = element.querySelector("#answer");
  const feedbackEl = element.querySelector("#feedback");
  const correctCountEl = element.querySelector("#correct-count");
  const wrongCountEl = element.querySelector("#wrong-count");

  // Initialize display with current values
  correctCountEl.textContent = activity.values.correct_answers || 0;
  wrongCountEl.textContent = activity.values.wrong_answers || 0;

  // Handle events from backend
  activity.onEvent = (name, value) => {
    if (name === "values.change.correct_answers") {
      correctCountEl.textContent = value;
    } else if (name === "values.change.wrong_answers") {
      wrongCountEl.textContent = value;
    } else if (name === "answer.result") {
      feedbackEl.style.display = "block";
      feedbackEl.textContent = value.feedback;
      feedbackEl.className = value.correct ? "correct" : "incorrect";
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
      feedbackEl.className = "incorrect";
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
