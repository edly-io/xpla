// Type declarations for the MCQ plugin

declare module "main" {
    // Handle incoming events from the frontend
    // Input: JSON { "name": "...", "value": "..." }
    // Output: JSON { "processed": true }
    export function onEvent(): I32;
}

declare module "extism:host" {
    interface user {
        lms_get_user(ptr: I64): I64;
        post_event(name_ptr: I64, value_ptr: I64): I64;
        value_get(user_id_ptr: I64, name_ptr: I64): I64;
        value_set(user_id_ptr: I64, name_ptr: I64, value_ptr: I64): I32;
    }
}
