// Type declarations for the math quiz plugin

declare module "main" {
    // Handle incoming events from the frontend
    // Input: JSON { "name": "...", "value": "..." }
    // Output: JSON { "processed": true }
    export function onEvent(): I32;
}

declare module "extism:host" {
    interface user {
        lms_submit_grade(ptr: I64): I64;
        post_event(name_ptr: I64, value_ptr: I64): I64;
    }
}
