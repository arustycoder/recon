# Gateway Admin Panel

## Goal

Add an operator-facing management panel for the Recon gateway so provider status, request execution, skill configuration, and gateway health can be inspected and operated without relying on raw API calls.

## Why

The gateway already has meaningful operational behavior:

- provider routing and fallback
- cooldown and breaker state
- skill discovery and phased execution
- persisted request records
- request metrics, tokens, and estimated cost
- provider health grading and manual reset

At this point, raw endpoints are enough for integration, but not enough for day-to-day operation. A management panel becomes the thin control surface that makes the gateway usable by developers, testers, and operators.

## Primary Users

### Developer

- validates provider wiring during local development
- inspects request failures and skill behavior
- resets providers after changing local model or API settings

### Operator / Tester

- checks whether the gateway is healthy before using the desktop app
- confirms which provider handled a request
- inspects latency, token usage, and estimated cost
- resets cooled-down providers after an upstream issue is fixed

### Product / Domain Owner

- understands which skills are active and how requests are shaped
- reviews request-level behavior without reading logs directly

## Non-Goals

- not a full multi-user admin system
- not a security console
- not a billing dashboard
- not a workflow builder
- not a replacement for the desktop chat workbench

## Delivery Form

Two delivery options are possible:

### Option A: Embedded Desktop Panel

- add a new Qt panel inside the existing desktop application
- fastest implementation path
- ideal for the current phase

### Option B: Lightweight Web Admin

- add a minimal web UI served by the gateway
- better long-term separation
- easier for future remote deployment

## Recommendation

Implement in two steps:

1. first ship an embedded desktop panel to accelerate internal use and debugging
2. later extract or mirror the same information architecture into a lightweight web admin

This keeps current iteration speed high while preserving a clean migration path.

## Information Architecture

The panel should have four top-level sections:

1. Overview
2. Providers
3. Requests
4. Skills

An optional fifth section can be added later:

5. Diagnostics

## Section 1: Overview

### Goal

Give the user a fast snapshot of gateway readiness.

### Content

- gateway status
- gateway version
- provider count
- default provider id
- number of providers in `healthy`, `degraded`, `cooldown`, `disabled`, `misconfigured`, `unreachable`
- request volume summary over recent history
- average latency and first-token latency over recent requests
- total prompt/completion/total tokens over recent requests
- estimated total cost over recent requests

### Actions

- refresh gateway state
- open provider section
- open recent failing requests

### Empty / Error States

- if gateway is unreachable, show a dedicated connection-failed state
- if no requests exist yet, show a neutral “no execution history yet” state

## Section 2: Providers

### Goal

Manage provider availability and understand routing health.

### Table Columns

- `id`
- `label`
- `kind`
- `default`
- `enabled`
- `priority`
- `health_status`
- `consecutive_failures`
- `cooldown_remaining_seconds`
- `target summary`
- `default_skill_ids`
- `prompt_cost_per_1k`
- `completion_cost_per_1k`

### Row Details

Selecting a provider should open a detail pane with:

- provider configuration summary
- current health detail text
- breaker state
- recent requests handled by that provider
- recent average latency
- recent token usage and estimated cost

### Actions

- refresh health
- reset provider
- filter by status
- filter by kind
- filter by enabled/disabled

### Status Semantics

The panel should render distinct visual states for:

- `healthy`
- `degraded`
- `cooldown`
- `disabled`
- `misconfigured`
- `unreachable`

Do not collapse these into a single green/red binary, because that removes operational meaning.

## Section 3: Requests

### Goal

Inspect individual executions and debug failures, routing behavior, and cost.

### Table Columns

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
- `created_at`
- `updated_at`

### Filters

- by provider
- by status
- by phase
- by date/time range
- by client request id
- by session id
- by requests with errors only

### Detail View

Selecting a request should show:

- provider route actually used
- attempted provider ids
- skill ids used
- current or final phase
- error detail
- token usage
- estimated cost
- timing data

### Future Expansion

Later the request detail page can include:

- prompt preview
- rendered skill outputs by phase
- request/response payload excerpts
- provider usage records

## Section 4: Skills

### Goal

Make the skill layer understandable and inspectable.

### Table Columns

- `id`
- `label`
- `phase`
- `enabled_by_default`
- `parameter_keys`
- `description`

### Detail View

Selecting a skill should show:

- raw template
- phase
- default parameters
- where it is enabled:
  - global default
  - provider default
  - request-only
- example rendered output against sample request context

### Actions

The first version may be read-only.  
Later versions may support:

- enable/disable by provider
- parameter presets
- validation preview

## Optional Section 5: Diagnostics

### Goal

Collect low-level gateway signals without requiring log file inspection.

### Candidate Content

- SQLite database path
- record counts
- last migration/init time
- recent provider reset events
- recent cooldown events
- request persistence status
- adapter type in use

## UI Recommendation

### For Embedded Desktop

Use a `QTabWidget` or sidebar split:

- left navigation for sections
- right stacked detail view

Recommended layout:

```text
Gateway Admin
├── Overview
├── Providers
├── Requests
└── Skills
```

### For Web Admin

Use a simple admin shell:

- top summary cards
- filterable tables
- right-side detail drawer or separate detail page

Keep it utilitarian. This is an operations surface, not a marketing page.

## Data Sources

The panel should consume existing gateway APIs first.

### Existing APIs

- `GET /api/health`
- `GET /api/providers`
- `GET /api/providers/{provider_id}/health`
- `POST /api/providers/{provider_id}/reset`
- `GET /api/skills`
- `GET /api/requests`
- `GET /api/requests/{request_id}`

### Likely New APIs

To keep the panel responsive and avoid client-side over-aggregation, add these later:

- `GET /api/overview`
- `GET /api/providers/{provider_id}/requests`
- `GET /api/requests/stats`

## State Refresh Strategy

### Overview

- auto-refresh every 10 to 30 seconds is acceptable

### Providers

- manual refresh by default
- optional auto-refresh when the page is visible

### Requests

- polling every 5 to 10 seconds for recent activity is acceptable in the first phase

### Skills

- mostly static
- refresh only on demand in the first phase

## Error Handling

The panel should distinguish:

- gateway unreachable
- gateway reachable but provider unavailable
- gateway reachable but request history empty
- gateway reachable but a specific request record missing

Avoid generic “something went wrong” messaging when a more precise operational state exists.

## Security Boundary

The first version may run without authentication because the current gateway itself is not yet a multi-user service.

However, the design should assume that later:

- health and requests may be read-only for most users
- provider reset is an operator action
- config mutation is an admin action

So the panel should keep destructive or state-changing actions visually distinct from read-only inspection.

## Logging And Audit Expectations

The panel itself does not replace logging, but it should make critical actions visible:

- provider reset
- request failure trends
- repeated cooldown events
- providers staying in `misconfigured` or `unreachable`

Later phases should persist operator actions such as reset.

## Performance Expectations

- list pages should remain usable with at least a few thousand request records
- default views should page or limit recent requests
- expensive aggregation should move server-side when request volume grows

## Phased Implementation

### Phase 1: Read-Only Embedded Panel

- overview
- providers list and health
- request list and detail
- skills list and detail
- manual provider reset

### Phase 2: Server-Side Summaries

- add overview/stats APIs
- add better filtering and aggregation
- add provider-specific request views

### Phase 3: Operational Controls

- breaker reset history
- request export
- provider-specific diagnostics
- skill preview sandbox

### Phase 4: Optional Web Admin

- reuse the same information architecture
- expose it independently of the desktop app

## Acceptance Criteria

- user can inspect all providers and their current health grade
- user can reset a cooled-down provider from the panel
- user can inspect recent gateway requests including metrics and estimated cost
- user can inspect skills and their execution phases
- user can distinguish gateway-level errors from provider-level errors
- the panel remains useful even when there are zero requests or one misconfigured provider

## Recommended Next Implementation Step

Implement `Phase 1` as an embedded Qt panel first, and keep it read-only except for provider reset.

This gives the project an immediately useful operational surface without prematurely committing to a standalone web admin architecture.
