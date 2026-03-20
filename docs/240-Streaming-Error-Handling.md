# Streaming Error Handling

## Goal

Make direct provider streaming and gateway SSE streaming resilient enough that upstream timeouts or early disconnects do not surface to users as raw transport errors.

## Scope

### Included

- normalize OpenAI-compatible streaming failures into clearer application errors
- retry once with a non-stream request when a provider fails before the first streamed chunk
- make gateway `POST /api/chat/stream` end with structured SSE `error` and `done` events instead of a truncated chunked body
- make gateway `POST /api/chat` surface upstream provider failures as structured gateway errors instead of opaque 500 responses
- treat upstream `429 Too Many Requests` as a first-class gateway error with cooldown semantics
- preserve request persistence and provider error tracking when streaming fails

### Excluded

- true provider-side abort guarantees
- multi-stage retry backoff policies
- markdown-aware partial reply recovery

## Behavior

- if a direct OpenAI-compatible stream times out or the peer closes early before any chunk arrives:
  - retry once using a normal non-stream completion request
- if a direct OpenAI-compatible stream breaks after partial output:
  - stop the request
  - raise a normalized provider error
  - do not expose the raw `incomplete chunked read` message to the desktop user
- if a gateway stream request fails:
  - emit an SSE `error` event with provider and detail fields
  - emit a terminal `done` event with `status=error`
  - return normally from the generator

## API Impact

- `POST /api/chat` should return a gateway-managed error payload and non-500 status when an upstream provider fails
- gateway SSE consumers should expect:
  - `request`
  - `delta`
  - `usage`
  - `provider_error`
  - `error`
  - `done`
- `done` may now include `status=completed|error|canceled`

## Implementation Notes

- keep the desktop-side non-stream fallback limited to stream transport failures, not general HTTP status failures
- prefer preserving a useful provider-specific error message over hiding all context behind a generic timeout string
- treat gateway stream completion as a protocol contract: callers should always receive a terminal event, even on failure
