# Gateway Metrics And Costs

## Goal

Persist gateway-side request metrics so routing, provider quality, and estimated usage cost can be inspected without depending only on desktop logs.

## Scope

### Included

- request latency and first-token latency
- `stream_mode`
- prompt, completion, and total token counts
- provider target label
- estimated request cost derived from provider profile rates

### Excluded

- provider-billed exact cost reconciliation
- aggregated dashboards
- retention policy and archival

## Data Model

Gateway request records now persist:

- `target`
- `stream_mode`
- `latency_ms`
- `first_token_latency_ms`
- `prompt_tokens`
- `completion_tokens`
- `total_tokens`
- `estimated_cost_usd`

## API Impact

### `POST /api/chat`

The response now includes gateway-side execution metrics and estimated cost.

### `GET /api/requests`

Request detail now exposes the same execution metrics for later inspection.

## Implementation Notes

- metrics are measured in the gateway adapter layer instead of the desktop UI
- cost is estimated from per-provider `prompt_cost_per_1k` and `completion_cost_per_1k`
- this keeps the current design deterministic while leaving room for future billing reconciliation
