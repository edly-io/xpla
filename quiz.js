export function setup(activity) {
  const form = activity.querySelector("form");

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const answer = new FormData(form).get("answer");

    let feedback = activity.querySelector("#feedback");
    if (!feedback) {
      feedback = document.createElement("p");
      feedback.id = "feedback";
      form.after(feedback);
    }

    feedback.textContent = answer === "right" ? "Correct!" : "Try again.";
  });
}
