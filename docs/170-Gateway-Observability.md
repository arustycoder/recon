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
- execution metrics and estimated cost
- request listing and detail endpoints

### Excluded

- cross-process shared state
- metrics export to Prometheus or OTLP
- cost accounting

## API

- `GET /api/requests`
- `GET /api/requests/summary`
- `GET /api/requests/{request_id}`

Listing filters:

- `provider_id`
- `status`
- `phase`
- `since_minutes`
- `limit`

Tracked fields:

- `request_id`
- `client_request_id`
- `status`
- `phase`
- `provider_id`
- `target`
- `stream_mode`
- `latency_ms`
- `first_token_latency_ms`
- `prompt_tokens`
- `completion_tokens`
- `total_tokens`
- `estimated_cost_usd`
- `attempted_provider_ids`
- `skill_ids`
- `error_type`
- `error_detail`
- `created_at`
- `updated_at`

Summary fields:

- request and error counts
- average latency
- average first-token latency
- total tokens
- total estimated cost
- grouped metrics by provider
- grouped metrics by status
- grouped metrics by normalized error type

## Implementation Notes

- active request state is mirrored into the shared SQLite store so the gateway can be inspected after a process restart
- gateway request ids are also suitable for downstream `X-Client-Request-Id` propagation when the target provider supports correlation headers
- normalized `error_type` is intended to be the operator-facing grouping key; `error_detail` remains the raw explanatory text
- this is enough for local debugging and integration testing, but not enough for production audit or analytics
- later phases should add metrics export, retention policy, and gateway-side token/cost aggregation
