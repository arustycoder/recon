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

Suggested next step:

- Connect a real backend endpoint and replace mock responses with live analysis
