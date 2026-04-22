// Interactive Video plugin - combines YouTube video with MCQ overlays at timestamps
//
// Actions handled:
// - config.save: Save video_id and interactions list
// - answer.submit: Check if selected answers match correct answers for a given interaction

import { sendEvent, getField, setField } from "xpla:sandbox/host";

export function onAction(name, data, context, permission) {
  const value = JSON.parse(data);
  if (name === "config.save") {
    handleConfigSave(value, permission);
  } else if (name === "answer.submit") {
    handleAnswerSubmit(value);
  }
  return "";
}

export function getState(context, permission) {
  const videoId = JSON.parse(getField("video_id"));
  const interactions = JSON.parse(getField("interactions")) || [];

  const state = { video_id: videoId };

  if (permission === "edit") {
    state.interactions = interactions;
  } else {
    // Strip correct_answers for non-edit permissions
    state.interactions = interactions.map(function (interaction) {
      return {
        time: interaction.time,
        question: interaction.question,
        answers: interaction.answers,
      };
    });
  }

  return JSON.stringify(state);
}

function handleConfigSave(config, permission) {
  if (permission !== "edit") {
    console.log("config.save rejected: permission is " + permission);
    return;
  }
  setField("video_id", JSON.stringify(config.video_id));
  setField("interactions", JSON.stringify(config.interactions));

  sendEvent("fields.change.video_id", JSON.stringify(config.video_id), null, "play");

  // Broadcast interactions without correct_answers to non-edit users
  var publicInteractions = config.interactions.map(function (interaction) {
    return {
      time: interaction.time,
      question: interaction.question,
      answers: interaction.answers,
    };
  });
  sendEvent("fields.change.interactions", JSON.stringify(publicInteractions), null, "play");
  sendEvent("fields.change.interactions", JSON.stringify(config.interactions), null, "edit");
}

function handleAnswerSubmit(value) {
  var interactions = JSON.parse(getField("interactions")) || [];
  var index = value.index;
  var selected = value.selected;

  if (index < 0 || index >= interactions.length) {
    sendEvent("answer.result", JSON.stringify({ index: index, correct: false, feedback: "Invalid interaction." }), null, "play");
    return;
  }

  var interaction = interactions[index];
  var correctAnswers = interaction.correct_answers;

  var selectedSet = new Set(selected);
  var correctSet = new Set(correctAnswers);

  var isCorrect =
    selectedSet.size === correctSet.size &&
    [...selectedSet].every(function (x) { return correctSet.has(x); });

  var feedback;
  if (isCorrect) {
    feedback = "Correct! Well done.";
  } else if (selected.length === 0) {
    feedback = "Please select at least one answer.";
  } else {
    feedback = "Incorrect. Try again!";
  }

  sendEvent("answer.result", JSON.stringify({ index: index, correct: isCorrect, feedback: feedback }), null, "play");
}
