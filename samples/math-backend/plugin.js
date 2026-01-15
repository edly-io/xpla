// Math quiz plugin - validates answers and submits grades via WASM backend
//
// This plugin demonstrates calling host functions from WASM:
// - lms_submit_grade: Submit grade to the LMS

const { lms_submit_grade } = Host.getFunctions();

// Check a math answer and submit grade
// Input: JSON { "question": "2+2", "answer": "4" }
// Output: JSON { "correct": true, "score": 100, "feedback": "..." }
function check_answer() {
    const input = JSON.parse(Host.inputString());
    const question = input.question;
    const answer = input.answer;

    // Simple evaluation (for demo - real impl would be more robust)
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
                case "+": expected = a + b; break;
                case "-": expected = a - b; break;
                case "*": expected = a * b; break;
                case "/": expected = Math.floor(a / b); break;
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
    const gradeInput = JSON.stringify({ score: score, max_score: 100, comment: feedback });
    const mem = Memory.fromString(gradeInput);
    lms_submit_grade(mem.offset);

    // Return result to frontend
    const result = {
        correct: correct,
        score: score,
        feedback: feedback,
    };

    Host.outputString(JSON.stringify(result));
}

module.exports = { check_answer };
