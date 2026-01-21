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
  const form = activity.querySelector("#quiz-form");
  const questionEl = activity.querySelector("#question");
  const answerInput = activity.querySelector("#answer");
  const feedbackEl = activity.querySelector("#feedback");
  const correctCountEl = activity.querySelector("#correct-count");
  const wrongCountEl = activity.querySelector("#wrong-count");

  // Initialize display with current values
  correctCountEl.textContent = activity.values.correct_answers || 0;
  wrongCountEl.textContent = activity.values.wrong_answers || 0;

  // Handle value changes from backend
  activity.onValueChange = (name, value) => {
    if (name === "correct_answers") {
      correctCountEl.textContent = value;
    } else if (name === "wrong_answers") {
      wrongCountEl.textContent = value;
    }
  };

  // Initialize with a random question
  let current = generateQuestion();
  questionEl.textContent = `What is ${current.expression}?`;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const userAnswer = answerInput.value.trim();

    try {
      // Send event to backend
      const events = await activity.sendEvent(
        "answer.submit",
        JSON.stringify({ question: current.expression, answer: userAnswer })
      );

      // Find the result event
      const resultEvent = events.find((ev) => ev.name === "answer.result");
      if (resultEvent) {
        const result = JSON.parse(resultEvent.value);
        feedbackEl.style.display = "block";
        feedbackEl.textContent = result.feedback;
        feedbackEl.className = result.correct ? "correct" : "incorrect";
      }
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
