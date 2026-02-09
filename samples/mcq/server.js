// MCQ plugin - validates answers and saves configuration via WASM backend
//
// Events handled:
// - config.save: Save question, answers, and correct_answers
// - answer.submit: Check if selected answers match correct answers

import { postEvent, getValue, setValue } from "../../src/sandbox-lib";

// Handle incoming events from frontend
function onEvent() {
  const input = JSON.parse(Host.inputString());
  const eventName = input.name;
  const eventValue = input.value;

  if (eventName === "config.save") {
    handleConfigSave(eventValue);
  } else if (eventName === "answer.submit") {
    handleAnswerSubmit(eventValue);
  }
}

// Save configuration (question, answers, correct_answers)
function handleConfigSave(config) {
  setValue("question", config.question);
  setValue("answers", JSON.stringify(config.answers));
  setValue("correct_answers", JSON.stringify(config.correct_answers));

  // Notify frontend of value changes
  postEvent("values.change.question", config.question);
  postEvent("values.change.answers", JSON.stringify(config.answers));
  postEvent(
    "values.change.correct_answers",
    JSON.stringify(config.correct_answers)
  );
}

// Check submitted answers against correct answers
function handleAnswerSubmit(submission) {
  const selected = submission.selected;

  // Get correct answers from stored config
  const correctAnswers = JSON.parse(getValue("correct_answers"));

  // Compare selected answers with correct answers
  const selectedSet = new Set(selected);
  const correctSet = new Set(correctAnswers);

  const isCorrect =
    selectedSet.size === correctSet.size &&
    [...selectedSet].every((x) => correctSet.has(x));

  let feedback;
  if (isCorrect) {
    feedback = "Correct! Well done.";
  } else if (selected.length === 0) {
    feedback = "Please select at least one answer.";
  } else {
    feedback = "Incorrect. Try again!";
  }

  postEvent("answer.result", { correct: isCorrect, feedback });
}

module.exports = { onEvent };
