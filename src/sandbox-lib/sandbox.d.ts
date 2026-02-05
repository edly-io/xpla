// Type declarations for GULPS sandbox modules
//
// This file declares the Extism host functions available to all sandboxes.
// Include in your sandbox project's tsconfig.json or reference directly.

declare module "main" {
    // Handle incoming events from the frontend
    // Input: JSON { "name": "...", "value": "..." }
    // Output: JSON { "processed": true }
    export function onEvent(): I32;
}

declare module "extism:host" {
    interface user {
        // LMS functions (require lms capability)
        lms_submit_grade(ptr: I64): I64;
        get_user_id(ptr: I64): I64;

        // Event posting
        post_event(name_ptr: I64, value_ptr: I64): I64;

        // Get/Set value
        get_value(user_id_ptr: I64, name_ptr: I64): I64;
        set_value(user_id_ptr: I64, name_ptr: I64, value_ptr: I64): I32;

        // HTTP requests (require http capability)
        http_request(
            url_ptr: I64,
            method_ptr: I64,
            body_ptr: I64,
            headers_ptr: I64
        ): I64;
    }
}
