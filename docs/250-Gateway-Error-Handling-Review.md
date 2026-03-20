# Gateway Error Handling Review

## Goal

Summarize the current gateway error-handling model, identify where it is working, and define the next hardening steps needed to make desktop-to-gateway behavior more predictable.

## Current State

### What the gateway now does well

- `POST /api/chat/stream` no longer tears down the response with a broken chunked body when upstream streaming fails
- `POST /api/chat` no longer leaks a generic internal server error for common upstream provider failures
- upstream `429` is treated as a first-class rate-limit signal
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

- the gateway still relies heavily on string-based error classification
- sync and stream paths are closer now, but they are not fully symmetric
- the provider client is still optimized around OpenAI-compatible behavior and does not yet expose a formal internal error type
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

- introduce an internal gateway error classifier object instead of relying only on free-form strings
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
