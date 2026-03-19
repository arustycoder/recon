# Gateway And Service Layer

## Goal

Define the future server-side layer that sits between the desktop workbench and model providers or business systems.

## Why

- keep provider keys off the desktop client
- centralize prompt and context orchestration
- support true server-side cancellation
- unify logging, rate control, and fallback behavior
- create a stable path for future plant-data and Rust-service integration

## Responsibility Split

### Desktop

- project and session management
- local persistence
- operator-facing chat UI
- request settings and local diagnostics

### Gateway / Service Layer

- stable API contract for desktop clients
- request orchestration and `request_id` lifecycle
- provider routing
- model prompt assembly
- business-data enrichment
- request logging and governance
- cancellation handling

### Downstream Integrations

- OpenAI-compatible providers
- local model runtimes
- domain business APIs
- future Rust compute or analysis services

## Reserved API Contract

### Health

- `GET /api/health`
- returns service availability and optional dependency health

Suggested shape:

```json
{
  "status": "ok"
}
```

### Providers

- `GET /api/providers`
- returns available provider choices or routing metadata

Suggested shape:

```json
{
  "providers": [
    {"id": "primary", "label": "Main Gateway Route"}
  ]
}
```

### Single Reply

- `POST /api/chat`
- returns one normalized text reply

Suggested request:

```json
{
  "project": {},
  "session": {},
  "recent_messages": [],
  "message": "..."
}
```

Suggested response:

```json
{
  "request_id": "req_123",
  "reply": "..."
}
```

### Streaming Reply

- `POST /api/chat/stream`
- returns server-sent events

Reserved event shape:

```text
data: {"type":"request","request_id":"req_123"}
data: {"type":"delta","delta":"第一段"}
data: {"type":"delta","delta":"第二段"}
data: {"type":"usage","prompt_tokens":10,"completion_tokens":20,"total_tokens":30}
data: {"type":"done"}
```

### Cancel

- `POST /api/chat/{request_id}/cancel`
- server should attempt to stop downstream generation and mark the request as canceled

Suggested response:

```json
{
  "request_id": "req_123",
  "status": "cancel_requested"
}
```

## Desktop Reservation

The desktop app should already be able to store and derive:

- chat URL
- stream URL
- health URL
- providers URL
- cancel URL template

This keeps the current direct-client architecture compatible with a future gateway migration.

## Evolution Path

### Phase 1

- desktop mostly talks directly to providers
- gateway contract is documented and reserved

### Phase 2

- desktop uses `http_backend` against a single internal gateway
- gateway handles provider keys and basic routing

### Phase 3

- gateway adds true cancellation, business-data enrichment, and policy controls
- desktop becomes a thinner operator client

## Implementation Notes

- prefer FastAPI for the first gateway implementation
- keep request and response schemas close to current desktop dataclasses
- treat `request_id` as the boundary for streaming, logging, and cancellation
- keep the desktop provider UI generic enough that switching from direct provider calls to gateway calls does not require a redesign
