# Local LLM

## Goal

Allow DarkFactory users to chat with either:

- a locally running LLM
- an OpenAI-compatible backend

directly from the desktop conversation window.

## Why

- reduce dependence on remote services during early adoption
- support offline or controlled-network deployment scenarios
- let users validate the workbench with a real model before backend integration is complete

## Scope

### Included

- local LLM mode as a first-class assistant mode
- OpenAI-compatible backend mode as a first-class assistant mode
- desktop-side request path to a locally running model service
- desktop-side request path to an OpenAI-compatible API
- configuration through environment variables in the first cut
- response display through the existing chat window
- a simple provider abstraction inside the desktop app

### Excluded

- model download and installation UI
- advanced runtime tuning UI
- multi-model routing UI
- GPU diagnostics and hardware monitoring
- embedded LiteLLM dependency in the desktop client

## First Supported Shape

The first implementation should assume a local service such as `Ollama` is already running on the same machine.

Recommended initial contract:

- provider: `ollama`
- base URL: `http://127.0.0.1:11434/v1`
- request shape: OpenAI-compatible chat request when possible

## OpenAI-Compatible Backend

The first remote-provider shape should assume an API that follows an OpenAI-style chat or responses interface.

Recommended initial contract:

- provider: `openai_compatible`
- base URL: configurable
- model: configurable
- authentication: bearer token or empty when not required

## Provider Strategy

The first implementation should stay intentionally simple.

Desktop-side providers:

- `mock`
- `ollama`
- `openai_compatible`
- `http_backend`

Recommended selection order:

1. explicit `DARKFACTORY_LLM_PROVIDER`
2. local `ollama`
3. `openai_compatible`
4. custom `http_backend`
5. fallback `mock`

## Why Not LiteLLM In The Desktop App

For this phase, the desktop app should not embed `LiteLLM`.

Reasons:

- the client should stay lightweight
- current provider count is small
- `ollama` and many remote services can already be accessed through OpenAI-compatible APIs
- provider routing logic is still simple enough to keep in the app

If provider count grows later, `LiteLLM Proxy` can be introduced as a separate gateway layer instead of becoming a desktop dependency.

## UX Expectations

- users continue using the same conversation window
- no separate "developer console" should be required
- the UI should show the current assistant mode clearly:
  - `Mock`
  - `Local LLM`
  - `OpenAI-Compatible`
  - `HTTP Backend`

## Configuration Direction

Suggested first-pass environment variables:

- `DARKFACTORY_LLM_PROVIDER`
- `DARKFACTORY_OLLAMA_URL`
- `DARKFACTORY_OLLAMA_MODEL`
- `DARKFACTORY_OPENAI_BASE_URL`
- `DARKFACTORY_OPENAI_API_KEY`
- `DARKFACTORY_OPENAI_MODEL`
- `DARKFACTORY_API_URL`

## Prompting Rules

- inject project context:
  - plant
  - unit
  - expert type
- include recent messages for continuity
- keep output structured for domain trust

## Risks

- local models may be slower than remote APIs
- weaker models may reduce output quality
- long responses can block the UI if threading is not handled correctly
- provider-specific protocol differences may require normalization logic

## Implementation Notes

- local LLM mode should reuse the existing assistant service abstraction
- OpenAI-compatible mode should reuse the same abstraction and message pipeline
- provider selection should remain configuration-driven
- desktop app behavior should stay consistent regardless of reply source
- prefer one normalized message pipeline for all providers
- only add a gateway dependency later if provider management becomes meaningfully more complex
