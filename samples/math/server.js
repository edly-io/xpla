// Math quiz plugin - validates answers and submits grades via WASM backend
//
// This plugin demonstrates the action/event architecture:
// - Receives actions via onAction
// - Sends events back via send_event host function
// - Updates fields via fields.change.* events
// - Persists counters via getField/setField host functions

import {
  sendEvent,
  getPermission,
  getField,
  setField,
} from "../../src/sandbox-lib";

const { submit_grade } = Host.getFunctions();

// Return state visible to the current user.
function getState() {
  Host.outputString(
    JSON.stringify({
      correct_answers: getField("correct_answers"),
      wrong_answers: getField("wrong_answers"),
    }),
  );
}

// Handle incoming actions from frontend
// Input: JSON { "name": "...", "value": "..." }
function onAction() {
  const input = JSON.parse(Host.inputString());
  const actionName = input.name;
  const actionValue = input.value;

  if (actionName === "answer.submit") {
    if (getPermission() === "view") {
      console.log("answer.submit rejected: permission is view");
      return;
    }
    // Parse the submission: { question: "2+2", answer: "4" }
    const submission = actionValue;
    const result = checkAnswer(submission.question, submission.answer);

    // Update counters and emit value change events
    if (result.correct) {
      const correctCount = getField("correct_answers") + 1;
      setField("correct_answers", correctCount);
      sendEvent("fields.change.correct_answers", correctCount);
    } else {
      const wrongCount = getField("wrong_answers") + 1;
      setField("wrong_answers", wrongCount);
      sendEvent("fields.change.wrong_answers", wrongCount);
    }

    // Send feedback event
    sendEvent("answer.result", result);
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
  submit_grade(score);

  return { correct, score, feedback };
}

module.exports = { onAction, getState };
