// Activity script for math-backend
// Demonstrates backend integration via LMS API for grade submission
// Can also use WASM plugin when available (requires extism-js to build)

// Generate a random math question
function generateQuestion() {
    const ops = ["+", "-", "*"];
    const op = ops[Math.floor(Math.random() * ops.length)];
    let a, b;

    switch (op) {
        case "+":
            a = Math.floor(Math.random() * 50) + 1;
            b = Math.floor(Math.random() * 50) + 1;
            break;
        case "-":
            a = Math.floor(Math.random() * 50) + 10;
            b = Math.floor(Math.random() * a);
            break;
        case "*":
            a = Math.floor(Math.random() * 12) + 1;
            b = Math.floor(Math.random() * 12) + 1;
            break;
    }

    return { expression: `${a} ${op} ${b}`, a, op, b };
}

// Evaluate a math expression
function evaluate(a, op, b) {
    switch (op) {
        case "+": return a + b;
        case "-": return a - b;
        case "*": return a * b;
        default: return NaN;
    }
}

// Load and display grade history from LMS API
async function loadGrades(gradesEl) {
    try {
        const response = await fetch("/api/lms/grades");
        const data = await response.json();

        if (data.grades && data.grades.length > 0) {
            const recentGrades = data.grades.slice(-5).reverse();
            gradesEl.innerHTML = recentGrades
                .map(g => `<div class="grade-entry">Score: ${g.score}/${g.max_score} - ${g.comment || "No comment"}</div>`)
                .join("");
        } else {
            gradesEl.textContent = "No grades yet.";
        }
    } catch (err) {
        gradesEl.textContent = "Could not load grades.";
    }
}

// Submit grade to LMS backend
async function submitGrade(score, comment) {
    try {
        const response = await fetch("/api/lms/grade", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ score, max_score: 100, comment }),
        });
        return response.ok;
    } catch {
        return false;
    }
}

export function setup(activity) {
    const form = activity.querySelector("#quiz-form");
    const questionEl = activity.querySelector("#question");
    const answerInput = activity.querySelector("#answer");
    const feedbackEl = activity.querySelector("#feedback");
    const gradesEl = activity.querySelector("#grades");

    // Initialize with a random question
    let current = generateQuestion();
    questionEl.textContent = `What is ${current.expression}?`;

    // Load initial grades from LMS backend
    loadGrades(gradesEl);

    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const userAnswer = parseInt(answerInput.value, 10);
        const correctAnswer = evaluate(current.a, current.op, current.b);
        const correct = userAnswer === correctAnswer;

        const score = correct ? 100 : 0;
        const feedback = correct
            ? "Correct! Well done."
            : `Incorrect. ${current.expression} = ${correctAnswer}`;

        // Submit grade to LMS backend (HTTP API call)
        await submitGrade(score, feedback);

        // Display feedback
        feedbackEl.style.display = "block";
        feedbackEl.textContent = feedback;
        feedbackEl.className = correct ? "correct" : "incorrect";

        // Reload grades from backend
        await loadGrades(gradesEl);

        // Generate a new question after a short delay
        setTimeout(() => {
            current = generateQuestion();
            questionEl.textContent = `What is ${current.expression}?`;
            answerInput.value = "";
            feedbackEl.style.display = "none";
        }, 2000);
    });
}
