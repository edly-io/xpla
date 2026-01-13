// Type declarations for the math quiz plugin

declare module "main" {
    // Check answer and submit grade
    // Input: JSON { "question": "2+2", "answer": "4" }
    // Output: JSON { "correct": true, "score": 100, "feedback": "..." }
    export function check_answer(): I32;
}

declare module "extism:host" {
    interface user {
        lms_submit_grade(ptr: I64): I64;
    }
}
