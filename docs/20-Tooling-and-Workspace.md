# Tooling And Workspace

## Goal

Define a stable project-management structure for DarkFactory:

- Python dependencies managed by `uv`
- Rust integration added later without reorganizing the repository
- shared conventions for docs, entrypoints, and module boundaries

## Tooling Decisions

### Python

- package manager: `uv`
- environment sync: `uv sync`
- command execution: `uv run ...`
- lockfile: `uv.lock`

### Rust

- reserved for future performance-sensitive or systems-level modules
- managed through a top-level Cargo workspace
- recommended location: `crates/`

## Repository Layout

```text
darkfactory/
├── docs/                  # product, feature, architecture docs
├── src/darkfactory/       # Python desktop application
├── tests/                 # Python tests
├── crates/                # future Rust crates
├── Cargo.toml             # Rust workspace root
├── pyproject.toml         # Python project config
├── uv.lock                # Python dependency lock
└── main.py                # local desktop entrypoint
```

## Responsibility Split

### Python Layer

- Qt desktop UI
- local persistence
- application orchestration
- backend API integration

### Rust Layer

- optional high-performance processing
- domain compute engines
- local services or native extensions
- future orchestrator or secure runtime components

## Rules

- new Python dependencies must be added through `uv`
- Rust crates must live under `crates/`
- each major feature still requires a dedicated doc under `docs/`
- if a feature spans Python and Rust, document the interface boundary explicitly

## Recommended Commands

### Python

```bash
uv sync
uv run python main.py
uv run python -m unittest discover -s tests
```

### Rust

```bash
cargo check
cargo test
```

These commands become relevant when Rust crates are added to `crates/`.
