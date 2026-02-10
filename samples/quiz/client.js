export function setup(activity) {
    // TODO what can we do to add HTML without accessing the shadow attribute, which should be private?
    var element = activity.element;

    element.innerHTML = `
        <p>What is 2 + 2?</p>
        <form>
            <label><input type="radio" name="answer" value="3"> 3</label><br>
            <label><input type="radio" name="answer" value="4"> 4</label><br>
            <label><input type="radio" name="answer" value="5"> 5</label><br>
            <button type="submit">Check Answer</button>
        </form>
    `;

    const form = element.querySelector("form");

    form.addEventListener("submit", (e) => {
        e.preventDefault();
        const answer = new FormData(form).get("answer");

        let feedback = element.querySelector("#feedback");
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
