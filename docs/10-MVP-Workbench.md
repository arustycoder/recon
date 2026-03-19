# MVP Workbench

## Goal

Deliver the first runnable desktop version of DarkFactory:

- left-side `Project / Session` tree
- right-side chat workbench
- local persistence
- quick domain prompts
- minimal conversation service that works without a backend

## Scope

### Included

- Qt main window and split layout
- project create / rename / delete
- session create / rename / delete
- local SQLite storage
- message history loading
- quick action buttons for domain prompts
- assistant service abstraction
- mock assistant as default fallback
- local LLM mode for direct desktop-side chat
- optional HTTP backend client
- packaging path reserved for future Windows installer delivery

### Excluded

- real plant data integration
- streaming responses
- markdown rendering
- multi-user support
- authentication UI

## UI Behavior

### Left Panel

- shows projects as top-level nodes
- shows sessions under each project
- supports basic create / rename / delete operations

### Right Panel

- shows current project and current session
- shows message history for the selected session
- provides quick buttons:
  - `蒸汽不足`
  - `负荷优化`
  - `能效诊断`
- allows free-text input

## Data Model Impact

### Project

- `id`
- `name`
- `plant`
- `unit`
- `expert_type`
- `created_at`

### Session

- `id`
- `project_id`
- `name`
- `summary`
- `updated_at`

### Message

- `id`
- `session_id`
- `role`
- `content`
- `created_at`

## API Impact

The desktop app supports two execution modes:

### Mock mode

- default mode
- returns deterministic structured domain text
- used for local development and demo

### HTTP mode

- enabled when `DARKFACTORY_API_URL` is set
- sends project/session context plus recent messages
- expects a JSON response with `reply`

### Local LLM mode

- enabled when local provider configuration is present
- uses the same desktop chat window
- should preserve structured output and recent-message context
- first target providers are `ollama` and `openai_compatible`

## Implementation Notes

- keep UI code thin
- keep storage in a separate module
- keep assistant integration behind a service interface
- ensure the app remains usable without external dependencies beyond the configured Python packages
- keep entrypoints and resources compatible with later executable and installer packaging
