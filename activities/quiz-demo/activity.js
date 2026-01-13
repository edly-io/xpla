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

        if (answer === "4") {
            feedback.textContent = "Correct!";
            feedback.style.color = "green";
        } else {
            feedback.textContent = "Try again!";
            feedback.style.color = "red";
        }
    });
}
