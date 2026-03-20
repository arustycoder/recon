# Gateway Request Analytics

## Goal

Let operators and future desktop views inspect gateway request records without downloading and aggregating the full request history client-side.

## Scope

### Included

- filtered request listing
- summary and aggregate metrics endpoint
- filters for provider, status, phase, and recent time window
- grouped summaries by provider and by status

### Excluded

- long-term BI dashboards
- percentile latency computation
- cross-process distributed analytics
- chart rendering in the gateway itself

## API

### Request Listing

- `GET /api/requests`

Supported query params:

- `provider_id`
- `status`
- `phase`
- `since_minutes`
- `limit`

### Request Summary

- `GET /api/requests/summary`

Supported query params:

- `provider_id`
- `status`
- `phase`
- `since_minutes`

Response includes:

- total requests
- completed and error counts
- average latency
- average first-token latency
- total tokens
- total estimated cost
- grouped rows by provider
- grouped rows by status

## Implementation Notes

- summary is computed from the same persisted `gateway_requests` records used by request detail views
- the first phase prefers simple server-side aggregation over adding another analytics store
- this endpoint is intended to back an operator view and desktop diagnostics, not external BI tooling
