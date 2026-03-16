// Type declarations for xPLA sandbox modules
//
// This file declares the Extism host functions available to all sandboxes.
// Include in your sandbox project's tsconfig.json or reference directly.

declare module "main" {
  // Handle incoming action from the frontend.
  // Input: JSON { "name": "...", "value": ..., "scope": { "user_id": "...", "course_id": "...", "activity_id": "..." }, "permission": "view"|"play"|"edit" }
  export function onAction(): I32;
  // Return state to display to the user.
  // Input: JSON { "scope": { "user_id": "...", "course_id": "...", "activity_id": "..." }, "permission": "view"|"play"|"edit" }
  // Output: JSON
  export function getState(): I32;
}

declare module "extism:host" {
  interface user {
    // LMS functions (require lms capability)
    submit_grade(score: F64): I32;

    // Event posting
    send_event(name_ptr: I64, value_ptr: I64, scope_ptr: I64, permission_ptr: I64): I64;

    // Get/Set field (scope resolved from manifest)
    get_field(name_ptr: I64, scope_ptr: I64): I64;
    set_field(name_ptr: I64, value_ptr: I64, scope_ptr: I64): I32;

    // Log field operations
    log_get(name_ptr: I64, id: I64, scope_ptr: I64): I64;
    log_get_range(name_ptr: I64, from_id: I64, to_id: I64, scope_ptr: I64): I64;
    log_append(name_ptr: I64, value_ptr: I64, scope_ptr: I64): I64;
    log_delete(name_ptr: I64, id: I64, scope_ptr: I64): I32;
    log_delete_range(name_ptr: I64, from_id: I64, to_id: I64, scope_ptr: I64): I64;

    // HTTP requests (require http capability)
    // Returns a JSON string: {"status": int, "headers": [[k,v],...], "body": str}
    // status=0 indicates a connection or capability error.
    http_request(
      url_ptr: I64,
      method_ptr: I64,
      body_ptr: I64,
      headers_ptr: I64,
    ): I64;
  }
}
