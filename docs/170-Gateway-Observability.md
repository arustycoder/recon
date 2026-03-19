# Gateway Observability

## Goal

Give the gateway its own request-level visibility so fallback and skill behavior can be debugged without depending only on desktop-side logs.

## Scope

### Included

- in-memory request tracker
- request lifecycle status
- attempted provider ids
- client request correlation id
- request listing and detail endpoints

### Excluded

- durable database storage
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
- `provider_id`
- `attempted_provider_ids`
- `skill_ids`
- `error_detail`

## Implementation Notes

- the request tracker currently keeps active requests and a bounded recent history in memory
- gateway request ids are also suitable for downstream `X-Client-Request-Id` propagation when the target provider supports correlation headers
- this is enough for local debugging and integration testing, but not enough for production audit or analytics
- later phases should move request history, metrics, and provider error rates into persistent gateway storage
