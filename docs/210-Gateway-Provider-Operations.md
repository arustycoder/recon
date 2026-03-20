# Gateway Provider Operations

## Goal

Give desktop operators a direct view into gateway-managed providers so cooldown, health status, and manual resets do not require raw API calls.

## Scope

### Included

- desktop dialog under `工具`
- gateway provider listing
- provider health refresh
- manual provider reset
- display of cooldown and failure counters

### Excluded

- live auto-refresh
- provider editing from the desktop
- role-based access control

## Behavior

- the dialog uses the configured `http_backend` gateway endpoints
- operators can inspect:
  - provider id
  - kind
  - status
  - failure count
  - cooldown remaining
- operators can trigger a reset for a selected provider after upstream fixes

## API Impact

The desktop uses:

- `GET /api/providers`
- `GET /api/providers/{provider_id}/health`
- `POST /api/providers/{provider_id}/reset`

## Implementation Notes

- the desktop reuses `AssistantService` for gateway API calls instead of embedding raw HTTP in the UI layer
- this dialog is intentionally read-mostly; provider edits still belong on the gateway side
