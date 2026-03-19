# Project Metadata And State

## Goal

Improve the first MVP so it behaves more like a usable desktop workbench:

- project metadata can be edited instead of staying implicit
- the app remembers the last selected session
- the UI shows whether it is running in mock mode or HTTP mode

## Scope

### Included

- create and edit project metadata:
  - name
  - plant
  - unit
  - expert type
- persist last selected session in local storage
- show mode and database location in the status bar

### Excluded

- user accounts
- cloud sync
- multi-device session restore
- advanced settings page

## UI Impact

- new project dialog replaces a single text prompt
- edit project action is available from menu and tree context menu
- right panel shows project metadata under the current project title
- status bar shows:
  - current assistant mode
  - active local database path

## Data Impact

Adds local key-value state storage:

- key: `last_session_id`

This state is only used for client-side continuity.

## Implementation Notes

- keep project metadata lightweight and editable in one place
- treat persisted UI state as optional convenience, not business data
- do not mix UI state with domain tables unless necessary
