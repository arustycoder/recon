# Gateway Error Handling Review

## Goal

Summarize the current gateway error-handling model, identify where it is working, and define the next hardening steps needed to make desktop-to-gateway behavior more predictable.

## Current State

### What the gateway now does well

- `POST /api/chat/stream` no longer tears down the response with a broken chunked body when upstream streaming fails
- `POST /api/chat` no longer leaks a generic internal server error for common upstream provider failures
- upstream `429` is treated as a first-class rate-limit signal
- synchronous chat now has one explicit recovery path for a mid-stream disconnect:
  - if the stream already began and then breaks
  - the gateway can retry once with a non-stream completion request
- provider health can now distinguish:
  - `healthy`
  - `degraded`
  - `cooldown`
  - `rate_limited`
  - `disabled`
  - `misconfigured`
  - `unreachable`
- synchronous chat requests can recover from one class of upstream instability:
  - stream starts
  - peer closes mid-generation
  - gateway retries once with a non-stream completion request

### What the desktop now gets

- when the gateway fails, desktop `http_backend` requests now surface the gateway `detail` field instead of a generic `500`
- that means desktop logs can now preserve concrete upstream signals such as:
  - `404 Not Found`
  - `429 Too Many Requests`
  - `Provider streaming connection closed before the response completed.`

## Reflection

### What worked

- fixing the stream path first was the right call because it eliminated the least readable class of user-facing failure: incomplete chunked reads
- reusing the same provider client logic in desktop and gateway kept behavior aligned enough to iterate quickly
- adding provider health grading before over-engineering retries was useful because it made the runtime state visible
- treating `429` separately was necessary; rate limit is operationally different from generic provider degradation

### What is still weak

- the gateway now has an internal error classifier, but most adapters still feed it plain detail text instead of typed exceptions
- sync and stream paths now share error categories, but recovery policy is still partially distributed across adapters and service code
- the provider client is still optimized around OpenAI-compatible behavior
- some upstream failures still mix two concerns:
  - transport behavior
  - provider semantics

## Current Error Taxonomy

### Stable enough today

- `429 / Too Many Requests`
  - mapped to client-visible `429`
  - provider health becomes `rate_limited`
  - cooldown starts immediately
- `404 / provider-side client errors`
  - mapped to a gateway-managed sync error instead of generic `500`
  - preserved in request logs
- stream interruption after partial output
  - normalized into a provider error
  - can trigger a non-stream retry in sync chat
  - if recovery still fails, provider enters a short cooldown window
- connectivity and timeout failures
  - generally classified as `unreachable`

### Still too implicit

- empty provider replies
- malformed but `200 OK` provider payloads
- long-tail HTTP `4xx` cases other than `404` and `429`
- provider responses that are technically valid but semantically unusable

## Design Gaps

### 1. Too much string matching

The current code mostly infers semantics from error text.

This is pragmatic, but brittle:

- wording can differ across providers
- localization or proxy layers may change messages
- the same root cause may surface with several different strings

### 2. Sync and stream parity is improved, not complete

Current behavior is directionally correct:

- stream path emits structured terminal events
- sync path returns structured HTTP errors

But parity is still incomplete:

- stream has event-level semantics
- sync has status-code semantics
- retries and recovery do not yet share one normalized decision layer

### 3. Provider resilience is still process-local

Cooldown and failure counters are in-memory.

That is acceptable for one-process local deployment, but weak for:

- multiple gateway instances
- restart-heavy environments
- future worker/process isolation

## Comparison To Industry Practice

### OpenAI-style API behavior

Modern API consumers expect:

- stable request IDs
- stable error classes
- predictable streaming termination

DarkFactory is now much closer on those points than before, especially for streaming termination and request inspection.

### Gateway products like LiteLLM Proxy

Mature gateways usually go further by adding:

- explicit provider error normalization
- retry policy per provider and per error class
- rate-limit aware routing and backoff
- richer observability around failure classes

DarkFactory has started this path, but still sits in an embedded, product-first phase rather than a full control-plane phase.

## Recommended Next Steps

### Priority 1

- keep extending the internal gateway error classifier instead of adding new string checks in ad-hoc call sites
- normalize at least these categories:
  - `rate_limited`
  - `upstream_http_error`
  - `upstream_timeout`
  - `stream_interrupted`
  - `empty_response`
  - `misconfigured`

### Priority 2

- centralize retry policy so sync and stream paths consult the same recovery rules
- document exactly which categories are retried, which enter cooldown, and which fail fast
- tighten the distinction between:
  - retryable stream interruption
  - non-retryable upstream HTTP error
  - retryable timeout before any tokens

### Priority 3

- extend provider health/detail APIs so operators can see the last classified error type, not only the last free-form message
- add request summary breakdown by normalized error category

### Priority 4

- move resilience state out of process memory once the gateway becomes multi-process or remotely deployed

## Practical Conclusion

The gateway error-handling model has crossed an important threshold:

- it is no longer leaking raw transport failures by default
- it now preserves meaningful upstream detail
- it distinguishes rate limiting from ordinary degradation

The next milestone is not “more retries”.

It is:

- a cleaner internal error taxonomy
- stronger sync/stream parity
- more explicit operator-facing semantics

Update:

- `docs/260-Gateway-Error-Classification.md` now defines the first classifier-backed version of that taxonomy

## Second Reflection

### Problems materially reduced in this pass

- sync chat and stream chat now speak in the same error vocabulary instead of two unrelated shapes
- adapter boundaries now emit typed gateway provider exceptions instead of only raw runtime failures
- provider health is no longer just “healthy or not”; operators can now see the last classified failure
- request analytics can now answer “what kind of failure is happening” without parsing free-form detail
- desktop-side request logs can now preserve gateway `error_type` as well as text detail

### Problems not actually solved yet

- many provider-specific details still originate as free-form text before they are normalized into typed gateway errors
- there is still no single policy table that says:
  - which error types retry
  - which enter cooldown
  - which fail fast
- desktop UI stores error types, but does not yet provide a dedicated filter or summary by `error_type`

### Practical conclusion after this pass

This version is good enough to stop firefighting raw transport failures.

It is not yet good enough to call the gateway error model “finished”.

The next meaningful step is to make adapters emit typed provider errors directly, so the classifier becomes a mapper of structured signals instead of a parser of strings.

Update:

- adapters now emit `GatewayProviderError`
- provider-client code now emits `AssistantServiceError`
- same-provider sync retry now also uses the shared error policy instead of a local one-off rule
- the next step is narrower:
  - make providers raise richer typed low-level causes before adapter normalization
