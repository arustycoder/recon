# Gateway Observability

## Goal

Give the gateway its own request-level visibility so fallback and skill behavior can be debugged without depending only on desktop-side logs.

## Scope

### Included

- SQLite-backed gateway request records
- in-memory request tracker for active requests
- request lifecycle status
- request phase tracking
- attempted provider ids
- client request correlation id
- request listing and detail endpoints

### Excluded

- cross-process shared state
- metrics export to Prometheus or OTLP
- cost accounting

## API

- `GET /api/requests`
- `GET /api/requests/{request_id}`

Tracked fields:

- `request_id`
- `client_request_id`
- `status`
- `phase`
- `provider_id`
- `attempted_provider_ids`
- `skill_ids`
- `error_detail`
- `created_at`
- `updated_at`

## Implementation Notes

- active request state is mirrored into the shared SQLite store so the gateway can be inspected after a process restart
- gateway request ids are also suitable for downstream `X-Client-Request-Id` propagation when the target provider supports correlation headers
- this is enough for local debugging and integration testing, but not enough for production audit or analytics
- later phases should add metrics export, retention policy, and gateway-side token/cost aggregation
