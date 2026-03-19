def get_activity_information() -> str:
    """
    Return information about an activity such that it can be parsed by an LLM.
    """
    return """
## Introduction

This is information that your user has sent to you to better interact with this platform. With the information contained in this documentation, you can read content from this platform and make extensive changes.

This is a learning platform. It has multiple courses. Each course has multiple pages. Each page has multiple learning activities.

## Documentation

Before you decide to make any change, you *must* read the API documentation of the platform.

- Human-readable documentation: {base_url}/docs
- OpenAPI spec: {base_url}/openapi.json

DO NOT try to second guess API endpoints.

## This activity

This specific documentation page provides information about the following learning activity instance:

- ID: {activity_id}
- Type: {activity_type}
- Activity belongs to page with ID: {page_id}
- Page belongs to course with ID: {course_id}
- Currently accessed with permission: {permission}

### Current state of this activity

Currently, the activity has the following state:

```
{activity_state}
```

### Making changes to this activity

To modify the content of a specific learning activity instance, use the endpoint to trigger actions. This endpoint is fully described in the documentation mentioned above.

For this specific activity, the supported actions are the following:

```
{manifest_actions}
```

Actions should be sent with the following permissions:

- "edit": to simulate a user making changes to the configuration of the activity.
- "play": to simulate a user interacting with the activity.

Actions should never be sent with "view" permission. This documentation was generated with the "{permission}" permission. But that DOES NOT MEAN that you should use the same permission.
"""
