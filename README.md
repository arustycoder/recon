# DarkFactory

Python + Qt desktop project scaffold for an energy-domain conversational workbench.

Tooling:

- Python dependency management: `uv`
- Future systems modules: Rust workspace under `crates/`

Current status:

- Git repository initialized
- Base project folders created
- Product and engineering plan saved in `docs/00-Plan.md`
- Repository conventions saved in `AGENTS.md`
- First MVP workbench implemented with local SQLite persistence and a mock assistant
- Tooling and workspace rules saved in `docs/20-Tooling-and-Workspace.md`
- In-app provider settings, health checks, chat cancel flow, and session auto-titles implemented

Run locally:

```bash
uv sync
uv run python main.py
```

Run gateway locally:

```bash
uv run darkfactory-gateway
```

Run tests:

```bash
uv run python -m unittest discover -s tests
```

Behavior:

- default mode uses a built-in mock assistant
- if `DARKFACTORY_API_URL` is set, the app will POST chat requests to that endpoint
- if local or remote model provider variables are set, the app can talk directly to those providers
- saved desktop settings override bootstrap defaults from `.env` on subsequent launches

Desktop features:

- provider settings dialog under `工具 -> 模型设置`
- connection test before saving provider settings
- configurable request timeout
- visible waiting and slow-request states in chat
- streamed assistant output when the provider supports it
- `停止等待` action for long-running model calls
- local request logs stored in the SQLite database
- request log viewer under `工具 -> 请求日志`
- automatic session titling for generic new sessions
- HTTP backend settings already reserve gateway URLs for `chat / stream / cancel / health / providers`
- gateway now exposes provider health, skill discovery, and recent request inspection endpoints
- gateway persists request state, supports cooldown-aware provider fallback, and runs phased skills
- gateway request APIs now support filtered listing and summary aggregation
- gateway now records request metrics/costs, exposes graded provider health, and uses an adapter boundary for provider execution

Provider examples:

```bash
# local ollama
export DARKFACTORY_LLM_PROVIDER=ollama
export DARKFACTORY_OLLAMA_URL=http://127.0.0.1:11434/v1
export DARKFACTORY_OLLAMA_MODEL=qwen2.5:latest

# openai-compatible backend
export DARKFACTORY_LLM_PROVIDER=openai_compatible
export DARKFACTORY_OPENAI_BASE_URL=http://127.0.0.1:8000/v1
export DARKFACTORY_OPENAI_API_KEY=dummy-or-real-key
export DARKFACTORY_OPENAI_MODEL=my-model
```

`.env` support:

- the app loads `.env` from the repository root automatically
- shell environment variables still take precedence over `.env`
- for OpenAI-compatible providers, these generic keys are also supported:
  - `OPENAI_BASE_URL`
  - `OPENAI_API_KEY`
  - `OPENAI_MODEL`

Windows packaging:

```powershell
uv sync --group dev
powershell -ExecutionPolicy Bypass -File scripts/package_windows.ps1
```

Notes:

- the packaging script is meant to run on a Windows build machine
- it builds the executable with `PyInstaller`
- if Inno Setup 6 is installed, it also builds a Windows installer

Docs:

- `docs/80-Settings-And-Operations.md`
- `docs/90-Session-Summaries.md`
- `docs/100-Packaging-And-Installer.md`
- `docs/110-Request-Logs-And-Streaming.md`
- `docs/120-Gateway-and-Service-Layer.md`
- `docs/130-Gateway-Implementation.md`
- `docs/140-Multi-Provider-Routing.md`
- `docs/150-Skill-Pipeline.md`
- `docs/160-Gateway-Review.md`
- `docs/170-Gateway-Observability.md`
- `docs/180-Provider-Resilience.md`
- `docs/190-Skill-Execution-Phases.md`
- `docs/200-Gateway-Request-Analytics.md`
- `docs/200-Gateway-Metrics-And-Costs.md`
- `docs/210-Provider-Health-And-Reset.md`
- `docs/220-Gateway-Adapter-Boundary.md`
- `docs/230-Gateway-Admin-Panel.md`

Provider comparison:

```bash
uv run python scripts/compare_providers.py
```

This runs a small direct comparison between `mock` and the currently configured local or compatible provider, and prints first-chunk latency, total latency, stream mode, and any reported token usage.
