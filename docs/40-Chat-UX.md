# Chat UX

## Goal

Improve the first-version conversation area so it feels like a usable desktop workbench instead of a raw debug panel.

## Scope

### Included

- clearer empty states when no session is selected
- better visual hierarchy for project/session context
- styled message rendering for user and assistant roles
- basic message metadata display
- visible in-flight feedback after the user sends a message
- a slow-request notice when the model backend takes too long to respond
- streamed assistant text updates when the provider supports incremental output

### Excluded

- markdown rendering
- streaming token output
- rich attachments
- charts and tables

## UI Changes

### Empty State

- show a dedicated empty state when no conversation is active
- explain what the user should do next
- keep quick actions visible only when a session is active

### Message Rendering

- render messages as styled widgets rather than plain list rows
- distinguish user and assistant alignment
- show role label and timestamp
- preserve multi-line structured content
- insert a temporary assistant placeholder immediately after send
- replace the placeholder with the real reply or an error message
- update the same assistant card progressively during streaming

### Context Area

- keep project name and session name prominent
- show project metadata under the main context labels

## Implementation Notes

- use custom list item widgets instead of plain text rows
- keep the rendering simple enough for Qt Widgets
- prefer legibility and stability over decorative styling
- keep the waiting state in the UI only; do not persist placeholder rows to SQLite
- route replies back to the session that originated the request, even if the user changes selection
