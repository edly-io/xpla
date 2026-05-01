// Math quiz plugin - validates answers and submits grades via WASM backend

import { reportScored, submitGrade } from "pxc:sandbox/grading";
import { getField, sendEvent, setField } from "pxc:sandbox/state";

// Return state visible to the current user.
export function getState() {
  return JSON.stringify({
    correct_answers: JSON.parse(getField("correct_answers")),
    wrong_answers: JSON.parse(getField("wrong_answers")),
  });
}

// Handle incoming actions from frontend
export function onAction(name, data, context, permission) {
  const value = JSON.parse(data);
  if (name === "answer.submit") {
    // Parse the submission: { question: "2+2", answer: "4" }
    const submission = value;
    const result = checkAnswer(submission.question, submission.answer);

    // Update counters and emit value change events
    if (result.correct) {
      const correctCount = JSON.parse(getField("correct_answers")) + 1;
      setField("correct_answers", JSON.stringify(correctCount));
      sendEvent("fields.change.correct_answers", JSON.stringify(correctCount), null, "play");
    } else {
      const wrongCount = JSON.parse(getField("wrong_answers")) + 1;
      setField("wrong_answers", JSON.stringify(wrongCount));
      sendEvent("fields.change.wrong_answers", JSON.stringify(wrongCount), null, "play");
    }

    // Report score as ratio of correct / total answers
    const correctCount = JSON.parse(getField("correct_answers"));
    const wrongCount = JSON.parse(getField("wrong_answers"));
    const total = correctCount + wrongCount;
    if (total > 0) {
      reportScored(correctCount / total);
    }

    // Send feedback event
    sendEvent("answer.result", JSON.stringify(result), null, "play");
    return "";
  }
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
  submitGrade(score);

  return { correct, score, feedback };
}
