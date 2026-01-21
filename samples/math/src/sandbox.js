// Math quiz plugin - validates answers and submits grades via WASM backend
//
// This plugin demonstrates the event-driven architecture:
// - Receives events via onEvent
// - Sends events back via post_event host function
// - Updates values via values.change.* events

const { lms_submit_grade, post_event } = Host.getFunctions();

// State tracking (in real impl, this would come from KV store)
let correctCount = 0;
let wrongCount = 0;

// Helper to post an event
function postEvent(name, value) {
  const nameMem = Memory.fromString(name);
  const valueMem = Memory.fromString(value);
  post_event(nameMem.offset, valueMem.offset);
}

// Handle incoming events from frontend
// Input: JSON { "name": "...", "value": "..." }
function onEvent() {
  const input = JSON.parse(Host.inputString());
  const eventName = input.name;
  const eventValue = input.value;

  if (eventName === "answer.submit") {
    // Parse the submission: { question: "2+2", answer: "4" }
    const submission = JSON.parse(eventValue);
    const result = checkAnswer(submission.question, submission.answer);

    // Update counters and emit value change events
    if (result.correct) {
      correctCount++;
      postEvent("values.change.correct_answers", JSON.stringify(correctCount));
    } else {
      wrongCount++;
      postEvent("values.change.wrong_answers", JSON.stringify(wrongCount));
    }

    // Send feedback event
    postEvent("answer.result", JSON.stringify(result));
  }

  Host.outputString(JSON.stringify({ processed: true }));
}

// Check a math answer
function checkAnswer(question, answer) {
  let expected;
  let correct = false;
  let feedback = "";

  try {
    // Parse simple expressions like "2+2", "3*4", "10-5"
    const match = question.match(/^(\d+)\s*([\+\-\*\/])\s*(\d+)$/);
    if (match) {
      const a = parseInt(match[1], 10);
      const op = match[2];
      const b = parseInt(match[3], 10);

      switch (op) {
        case "+":
          expected = a + b;
          break;
        case "-":
          expected = a - b;
          break;
        case "*":
          expected = a * b;
          break;
        case "/":
          expected = Math.floor(a / b);
          break;
      }

      const userAnswer = parseInt(answer, 10);
      correct = userAnswer === expected;
      feedback = correct
        ? "Correct! Well done."
        : `Incorrect. The answer to ${question} is ${expected}.`;
    } else {
      feedback = "Invalid question format.";
    }
  } catch (e) {
    feedback = "Error evaluating answer.";
  }

  const score = correct ? 100 : 0;

  // Submit grade to LMS via host function
  const gradeInput = JSON.stringify({
    score: score,
    max_score: 100,
    comment: feedback,
  });
  const mem = Memory.fromString(gradeInput);
  lms_submit_grade(mem.offset);

  return { correct, score, feedback };
}

module.exports = { onEvent };
