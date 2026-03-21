// MCQ plugin - validates answers and saves configuration via WASM backend
//
// Actions handled:
// - config.save: Save question, answers, and correct_answers
// - answer.submit: Check if selected answers match correct answers

import { sendEvent, getField, setField } from "../../src/xpla/lib/sandbox";

// Handle incoming actions from frontend
export function onAction(name, data, context, permission) {
  const value = JSON.parse(data);
  if (name === "config.save") {
    handleConfigSave(value, permission);
  } else if (name === "answer.submit") {
    handleAnswerSubmit(value);
  }
  return "";
}

// Return state visible to the current user based on permission level.
export function getState(context, permission) {
  const state = {
    question: getField("question"),
    answers: getField("answers"),
  };
  if (permission === "edit") {
    state.correct_answers = getField("correct_answers");
  }
  return JSON.stringify(state);
}

// Save configuration (question, answers, correct_answers)
function handleConfigSave(config, permission) {
  if (permission !== "edit") {
    console.log("config.save rejected: permission is " + permission);
    return;
  }
  setField("question", config.question);
  setField("answers", config.answers);
  setField("correct_answers", config.correct_answers);

  // Notify frontend of field changes
  sendEvent("fields.change.question", config.question, {}, "play");
  sendEvent("fields.change.answers", config.answers, {}, "play");
  sendEvent("fields.change.correct_answers", config.correct_answers, {}, "edit");
}

// Check submitted answers against correct answers
function handleAnswerSubmit(selected) {

  // Get correct answers from stored config
  const correctAnswers = getField("correct_answers");

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

  sendEvent("answer.result", { correct: isCorrect, feedback }, {}, "play");
}
