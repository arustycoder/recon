# Environment Config

## Goal

Let DarkFactory run with provider configuration from a local `.env` file, without requiring users to export environment variables manually in the shell.

## Scope

### Included

- automatically load `.env` from the repository root at startup
- support DarkFactory-specific variable names
- support generic OpenAI-style variable names for OpenAI-compatible providers

### Excluded

- settings UI for editing `.env`
- encryption or secret vault integration
- multi-profile environment switching

## Supported Variables

### Preferred DarkFactory Names

- `DARKFACTORY_LLM_PROVIDER`
- `DARKFACTORY_OLLAMA_URL`
- `DARKFACTORY_OLLAMA_MODEL`
- `DARKFACTORY_OPENAI_BASE_URL`
- `DARKFACTORY_OPENAI_API_KEY`
- `DARKFACTORY_OPENAI_MODEL`
- `DARKFACTORY_API_URL`
- `DARKFACTORY_API_STREAM_URL`
- `DARKFACTORY_API_CANCEL_URL_TEMPLATE`
- `DARKFACTORY_API_HEALTH_URL`
- `DARKFACTORY_API_PROVIDERS_URL`

### Compatible OpenAI-Like Names

These should map automatically to the OpenAI-compatible provider path:

- `OPENAI_BASE_URL`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`

## Resolution Rules

- if a DarkFactory-specific variable is present, it wins
- otherwise compatible OpenAI-style variables may be used
- `.env` loading should not override already exported shell variables

## Expected User Flow

1. create or edit `.env`
2. put provider settings in the file
3. run:

```bash
uv run python main.py
```

The app should pick up the configuration automatically.
