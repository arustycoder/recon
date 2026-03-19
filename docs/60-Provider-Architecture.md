# Provider Architecture

## Goal

Implement a simple provider layer inside the desktop application without introducing a heavyweight gateway dependency.

## Supported Providers

- `mock`
- `ollama`
- `openai_compatible`
- `http_backend`

## Selection Rules

The app should select the provider using the following order:

1. `DARKFACTORY_LLM_PROVIDER` when explicitly set
2. `ollama` when local Ollama configuration is present
3. `openai_compatible` when OpenAI-style remote configuration is present
4. `http_backend` when `DARKFACTORY_API_URL` is set
5. fallback to `mock`

## Configuration Contract

### Ollama

- `DARKFACTORY_LLM_PROVIDER=ollama`
- `DARKFACTORY_OLLAMA_URL`
- `DARKFACTORY_OLLAMA_MODEL`

### OpenAI-Compatible

- `DARKFACTORY_LLM_PROVIDER=openai_compatible`
- `DARKFACTORY_OPENAI_BASE_URL`
- `DARKFACTORY_OPENAI_API_KEY`
- `DARKFACTORY_OPENAI_MODEL`

### HTTP Backend

- `DARKFACTORY_LLM_PROVIDER=http_backend`
- `DARKFACTORY_API_URL`
- optional reserved fields for future gateway deployment:
  - `DARKFACTORY_API_STREAM_URL`
  - `DARKFACTORY_API_CANCEL_URL_TEMPLATE`
  - `DARKFACTORY_API_HEALTH_URL`
  - `DARKFACTORY_API_PROVIDERS_URL`

### Mock

- `DARKFACTORY_LLM_PROVIDER=mock`

## Interface Contract

All providers should implement the same reply path:

```text
project + session + recent_messages + current user message
    ↓
provider-specific request
    ↓
normalized reply string
```

For gateway-backed HTTP deployments, the reserved endpoint family is:

- `POST /api/chat`
- `POST /api/chat/stream`
- `POST /api/chat/{request_id}/cancel`
- `GET /api/health`
- `GET /api/providers`

## Response Normalization

- the UI expects a single text reply
- providers should return a normalized string
- the app should prefer structured output:
  - `【结论】`
  - `【原因分析】`
  - `【优化建议】`
  - `【影响评估】`

## Implementation Notes

- keep the provider logic inside `AssistantService`
- avoid introducing provider-specific UI logic
- provider mode should be visible in the status bar for debugging and operator clarity
