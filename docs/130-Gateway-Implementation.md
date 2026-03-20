# Gateway Implementation

## Goal

Add a first runnable gateway skeleton so DarkFactory can evolve from direct desktop-to-provider calls toward a centralized service layer.

## Scope

### Included

- FastAPI gateway application
- provider registry with multiple named providers and fallback routing
- skill registry with built-in prompt skills, templates, and request-time arguments
- health, providers, skills, chat, stream, and cancel endpoints
- request listing and detail endpoints for in-memory observability
- persisted request execution metrics and token tracking
- request id management and best-effort cancellation state

### Excluded

- persistent gateway-side request storage
- authentication and RBAC
- enterprise rate limiting
- distributed worker orchestration
- external skill marketplace integration

## Provider Management

- gateway should support more than one configured provider at the same time
- each provider has:
  - `id`
  - `kind`
  - `label`
  - `enabled`
  - `priority`
  - `tags`
  - `default_skill_ids`
  - provider-specific connection settings
- the desktop or caller can request a specific `provider_id`
- requests can choose `provider_strategy=default|fallback`
- gateway should expose `GET /api/providers` for discovery
- gateway should expose `GET /api/providers/{provider_id}/health` for targeted checks

## Skills

- skills are lightweight prompt or context augmenters selected per request
- the first implementation keeps skills server-side and deterministic
- built-in skills should include:
  - `project_context`
  - `structured_output`
  - `ops_guardrails`
- skills may define default parameters and request-time overrides
- requests can choose `skill_mode=merge|request_only`
- gateway should expose `GET /api/skills`

## API Behavior

- `POST /api/chat`
  - returns a single normalized reply
  - converts upstream provider failures into a structured non-500 gateway error response
- `POST /api/chat/stream`
  - emits SSE events
  - must terminate with structured `error` and `done` events when upstream providers fail
- `POST /api/chat/{request_id}/cancel`
  - marks the request as canceled
  - current phase is best-effort; downstream stop behavior depends on provider timing

## Implementation Notes

- gateway should reuse the existing desktop-side `AssistantService` provider client paths
- provider registry and skill registry should stay simple and in-process for the first phase
- configuration should allow env-driven provider definitions so the skeleton is immediately testable
- gateway orchestration should depend on a gateway adapter boundary, even if the default adapter still reuses desktop provider code
- a broken upstream provider stream must never tear down the HTTP response body without an explicit SSE terminal event
- the synchronous chat endpoint should preserve useful upstream error detail instead of surfacing a generic internal server error
