# Gateway Error Classification

## Goal

Replace ad-hoc string matching with a stable internal error classification layer so gateway behavior is consistent across:

- sync chat
- streaming chat
- provider health
- request inspection
- request summaries

## Scope

This version adds a gateway-side `GatewayErrorInfo` classifier and wires it into:

- `POST /api/chat`
- `POST /api/chat/stream`
- provider cooldown decisions
- provider health responses
- persisted gateway request records
- request summary aggregation

## Error Types

Current normalized error types:

- `rate_limited`
- `stream_interrupted`
- `upstream_timeout`
- `upstream_unreachable`
- `upstream_http_error`
- `empty_response`
- `invalid_response`
- `misconfigured`
- `provider_disabled`
- `provider_cooldown`
- `unknown`

Each classified error now carries:

- `error_type`
- user-facing `detail`
- gateway HTTP status code
- provider health status
- optional cooldown reason
- retryability hint

## API Impact

### Provider health

`GET /api/providers/{provider_id}/health` now includes:

- `last_error_type`
- `last_error_detail`

### Request inspection

`GET /api/requests`
`GET /api/requests/{request_id}`

now include:

- `error_type`

### Request summary

`GET /api/requests/summary` now includes:

- `by_error_type`

This allows operators to distinguish rate limits from timeouts, disconnects, and malformed upstream responses without parsing free-form text.

### Streaming events

Gateway stream error events now include:

- `error_type`
- `status_code`

## Behavior

### Sync chat

`POST /api/chat` now maps upstream failures through the classifier instead of using a narrow string-to-status mapping.

Examples:

- rate limit -> `429`
- timeout -> `504`
- unreachable upstream -> `503`
- generic upstream/provider failures -> `502`

### Streaming chat

`POST /api/chat/stream` continues to avoid broken chunked bodies. In addition, terminal `error` events now carry normalized error semantics so desktop can show a clearer reason.

### Provider resilience

Provider circuit state now keeps:

- `last_error_type`
- `last_error_detail`

Short cooldown and rate-limit cooldown still exist, but they are now driven by classified error semantics instead of scattered detail checks.

## Implementation Notes

- classification lives in `src/darkfactory_gateway/errors.py`
- adapter failures are normalized into `GatewayProviderError`
- desktop/provider client code now raises typed `AssistantServiceError` values for HTTP, timeout, and stream-interruption failures
- request persistence stores `error_type` in SQLite
- request summaries aggregate `by_error_type`
- provider health no longer infers everything from raw exception text
- retry/cooldown decisions now start from a shared policy table documented in `docs/270-Gateway-Provider-Error-Policy.md`
- same-provider sync recovery for OpenAI-compatible flows now also consults that shared policy table

## Remaining Gaps

- some classifications still begin from provider detail text, but provider-client and adapter boundaries now both emit typed exceptions
- desktop request logs now persist `error_type` and expose a basic error-type filter, but they still do not offer summary or trend views by category
- retry policy is improved, but not yet fully centralized into one declarative table
