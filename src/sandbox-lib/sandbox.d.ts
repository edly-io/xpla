// Type declarations for xPLA sandbox modules
//
// This file declares the Extism host functions available to all sandboxes.
// Include in your sandbox project's tsconfig.json or reference directly.

declare module "main" {
  // Handle incoming events from the frontend
  // Input: JSON { "name": "...", "value": "..." }
  export function onAction(): I32;
  // Return state to display to the user.
  // Output: JSON
  export function getState(): I32;
}

declare module "extism:host" {
  interface user {
    // LMS functions (require lms capability)
    submit_grade(score: F64): I32;

    // Get current user permission
    get_permission(): I64;

    // Event posting
    send_event(name_ptr: I64, value_ptr: I64): I64;

    // Get/Set value (scope resolved from manifest)
    get_value(name_ptr: I64): I64;
    set_value(name_ptr: I64, value_ptr: I64): I32;

    // HTTP requests (require http capability)
    http_request(
      url_ptr: I64,
      method_ptr: I64,
      body_ptr: I64,
      headers_ptr: I64,
    ): I64;
  }
}
