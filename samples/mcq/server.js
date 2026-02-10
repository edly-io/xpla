// MCQ plugin - validates answers and saves configuration via WASM backend
//
// Actions handled:
// - config.save: Save question, answers, and correct_answers
// - answer.submit: Check if selected answers match correct answers

import { postEvent, getValue, setValue, getPermission } from "../../src/sandbox-lib";

// Handle incoming actions from frontend
function onAction() {
  const input = JSON.parse(Host.inputString());
  const actionName = input.name;
  const actionValue = input.value;

  if (actionName === "config.save") {
    handleConfigSave(actionValue);
  } else if (actionName === "answer.submit") {
    handleAnswerSubmit(actionValue);
  }
}

// Return state visible to the current user based on permission level.
function getState() {
  const state = {
    question: getValue("question"),
    answers: getValue("answers"),
  };
  if (getPermission() === "edit") {
    state.correct_answers = getValue("correct_answers");
  }
  Host.outputString(JSON.stringify(state));
}

// Save configuration (question, answers, correct_answers)
function handleConfigSave(config) {
  if (getPermission() !== "edit") {
    console.log("config.save rejected: permission is " + getPermission());
    return;
  }
  setValue("question", config.question);
  setValue("answers", config.answers);
  setValue("correct_answers", config.correct_answers);

  // Notify frontend of value changes
  postEvent("values.change.question", config.question);
  postEvent("values.change.answers", config.answers);
  postEvent("values.change.correct_answers", config.correct_answers);
}

// Check submitted answers against correct answers
function handleAnswerSubmit(submission) {
  const selected = submission.selected;

  // Get correct answers from stored config
  const correctAnswers = getValue("correct_answers");

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

module.exports = { onAction, getState };
