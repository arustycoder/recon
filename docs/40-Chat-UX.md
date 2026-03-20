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
- keep scenario actions available in the left column without crowding the input area

### Message Rendering

- render messages as styled widgets rather than plain list rows
- distinguish user and assistant alignment
- show role label and timestamp
- convert stored UTC timestamps into local display time in the desktop UI
- preserve multi-line structured content
- insert a temporary assistant placeholder immediately after send
- show a visible `输入中` state on the pending assistant card until the reply completes
- replace the placeholder with the real reply or an error message
- update the same assistant card progressively during streaming
- use a multi-line input area that grows with content instead of a fixed single-line field
- keep `Enter` for send and `Shift+Enter` for newline
- use one primary action button instead of separate send/cancel buttons
- default state is an upward send icon, and the in-flight state switches to a custom coin-like stop icon with a black outer circle and white square center
- add a plus-button on the left side of the composer for selecting local files
- show selected files above the input area before send
- allow removing a single selected attachment before send
- allow dragging files into the composer
- render links and markdown tables more clearly inside message cards

### Context Area

- keep project name and session name prominent
- show project metadata under the main context labels

## Implementation Notes

- use custom list item widgets instead of plain text rows
- keep the rendering simple enough for Qt Widgets
- prefer legibility and stability over decorative styling
- keep the waiting state in the UI only; do not persist placeholder rows to SQLite
- route replies back to the session that originated the request, even if the user changes selection
