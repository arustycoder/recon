# Settings And Operations

## Goal

Make Recon operable by non-developer users without editing shell variables manually.

## Scope

### Included

- in-app settings dialog for provider configuration
- persistent provider settings stored locally
- request timeout configuration
- provider connection health check action
- local request logging with latency, status, and error detail
- request log viewer UI for diagnostics
- cancel-wait interaction for long-running requests

### Excluded

- encrypted secret storage
- cloud profile sync
- provider cost dashboards
- true server-side request abort for all backends

## UI And Behavior

### Settings Dialog

- provide a single entry point from the menu bar
- let users choose one provider:
  - `mock`
  - `ollama`
  - `openai_compatible`
  - `http_backend`
- show provider-specific fields only when relevant
- allow testing the current dialog values before saving

### Health Check

- `mock` should succeed immediately
- `ollama` and `openai_compatible` should verify the configured endpoint is reachable
- `http_backend` should test a configured or derived health URL
- return a short operator-friendly result string

### Request Logging

- store one local log record per request outcome
- capture:
  - session id
  - provider
  - model or endpoint
  - status
  - latency
  - error detail when present
- expose recent request logs in a simple desktop viewer
- keep the first viewer read-only and operator-focused

### Cancel Behavior

- users can dismiss a long-running wait from the chat panel
- canceled requests should not write a late reply back into the conversation
- cancellation should be logged locally
- cancellation is a UI-side ignore path in the first implementation, not a guaranteed backend abort

## Data And API Impact

### Local State

- provider settings are stored in `app_state`
- request log records are stored in a local table for diagnostics

### Provider Contract

- providers should expose enough metadata for operator logging:
  - provider name
  - model or endpoint label

## Implementation Notes

- keep environment-variable support as a bootstrap path
- let saved settings override bootstrap defaults inside the desktop app
- keep the settings format close to the existing provider abstraction
- prefer synchronous provider code inside worker threads over UI-thread networking
