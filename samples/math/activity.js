// Activity script for math
// Demonstrates backend validation via WASM plugin with LMS grade submission

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

// Call WASM plugin to validate answer (plugin also submits grade)
async function checkAnswer(question, answer) {
  const response = await fetch("/api/plugin/check_answer", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, answer: String(answer) }),
  });

  if (!response.ok) {
    throw new Error(`Plugin call failed: ${response.status}`);
  }

  const data = await response.json();
  // Plugin returns { result: '{"correct":true,"score":100,"feedback":"..."}' }
  return JSON.parse(data.result);
}

export function setup(activity) {
  const form = activity.querySelector("#quiz-form");
  const questionEl = activity.querySelector("#question");
  const answerInput = activity.querySelector("#answer");
  const feedbackEl = activity.querySelector("#feedback");
  const gradesEl = activity.querySelector("#grades");

  // Initialize with a random question
  let current = generateQuestion();
  questionEl.textContent = `What is ${current.expression}?`;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const userAnswer = answerInput.value.trim();

    try {
      // Call WASM plugin to validate answer (plugin also submits grade)
      const result = await checkAnswer(current.expression, userAnswer);

      // Display feedback from plugin
      feedbackEl.style.display = "block";
      feedbackEl.textContent = result.feedback;
      feedbackEl.className = result.correct ? "correct" : "incorrect";
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
