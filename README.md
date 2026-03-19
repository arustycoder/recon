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
- `停止等待` action for long-running model calls
- local request logs stored in the SQLite database
- automatic session titling for generic new sessions

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
