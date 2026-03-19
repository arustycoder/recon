# AGENTS.md

## Repository Conventions

### Docs

- All project documentation lives under `docs/`.
- Use numeric prefixes to keep major documents ordered.
- Current baseline planning document:
  - `docs/00-Plan.md`
- Tooling and workspace conventions:
  - `docs/20-Tooling-and-Workspace.md`

### Feature Documentation

- Every major feature must add a dedicated document under `docs/`.
- Create the document before or together with the implementation.
- Recommended naming format:
  - `docs/10-Project-Tree.md`
  - `docs/20-Chat-Panel.md`
  - `docs/30-Storage.md`
- The document should explain:
  - feature goal
  - scope
  - UI or behavior
  - data model or API impact
  - implementation notes

### Maintenance

- When a major feature changes materially, update its matching document.
- If a feature supersedes an older design, revise the existing doc instead of creating duplicate documents unless versioning is necessary.

### Workspace Structure

- Python application code lives under `src/darkfactory/`.
- Python dependencies are managed with `uv`.
- Future Rust code must live under `crates/`.
- Cross-language features should keep UI and app flow in Python unless there is a clear performance or systems reason to move logic into Rust.
