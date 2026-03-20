# DarkFactory Plan

## 1. Project Positioning

- Internal codename: `DarkFactory`
- Product direction: `Energy AI Console`
- Target users: power and energy domain staff, including technical and management roles without IT backgrounds
- Delivery form: Windows native desktop application based on Python and Qt

## 2. Core Product Goal

Build a project-based conversational workbench for energy operations analysis:

- Left side shows multiple `Project` items
- Each `Project` contains multiple conversation `Session` items
- Right side shows structured domain dialogue
- Bottom area provides quick actions and message input
- Left column includes a scenario library for scalable prompt templates
- Output is domain-specific and structured, not general chat

## 3. MVP Scope

### Included

- Windows desktop GUI
- Project tree
- Session management
- Multi-turn chat history
- Quick action buttons
- Structured answer rendering
- Local persistence
- API integration layer for model access
- Local LLM integration for direct chat in the desktop app
- OpenAI-compatible backend integration for remote chat providers
- In-app settings page for provider configuration
- Provider connection health checks
- Local request logging and latency tracking
- Request cancel interaction for long-running model calls
- Automatic session title and summary generation
- Gateway / service-layer protocol reserved for future deployment
- Gateway request persistence, provider resilience, and phased skill execution
- Gateway-side metrics, provider health grading/reset, and adapter abstraction
- Gateway admin panel for provider, request, skill, and overview inspection
- Stable streaming error handling for direct providers and gateway SSE responses
- Gateway error taxonomy, sync/stream parity, and provider-specific resilience rules
- Windows installer packaging requirement

### Excluded

- Multi-user support
- Permission system
- Multi-agent visualization
- Complex settings center
- Automatic scheduling
- Real-time plant integration in the first cut

## 4. Recommended Tech Stack

### Desktop

- Python 3.12+
- PySide6
- Qt Widgets

### Data and State

- SQLite for local persistence
- Dataclasses or Pydantic for domain models

### Networking

- `httpx` for backend requests
- OpenAI-compatible request flow for local and remote model providers
- gateway-friendly HTTP protocol for `chat / stream / cancel / health`
- gateway-side multi-provider routing and skill orchestration

### Packaging

- Development packaging: `PyInstaller`
- Release packaging: `Nuitka`

## 5. High-Level Architecture

```text
MainWindow
├── ProjectTreePanel
└── ChatPanel
    ├── TopInfoBar
    ├── MessageList
    ├── QuickActions
    └── InputBar

Desktop App
   ↓
Local Service Layer
   ↓
Local LLM / Gateway / Your Backend API
   ↓
Model / Business Logic / Data Source
```

## 6. Core Data Model

### Project

- `id`
- `name`
- `plant`
- `unit`
- `expert_type`
- `created_at`

### Session

- `id`
- `project_id`
- `name`
- `summary`
- `updated_at`

### Message

- `id`
- `session_id`
- `role`
- `content`
- `created_at`

## 7. GUI Plan

### Left Panel

- `QTreeWidget`
- Project nodes
- Session child nodes
- Context menu for create, rename, delete

### Right Panel

- Current project and session info
- Scrollable message list
- Input box and send button

### Interaction Rules

- Clicking a session loads its history
- Sending a message appends a user item immediately
- Assistant response is shown with loading state
- Structured result blocks should be encouraged:
  - `结论`
  - `原因分析`
  - `优化建议`
  - `影响评估`

## 8. Delivery Phases

### Phase 1: Project Skeleton

- Create repository structure
- Add packaging metadata
- Add logging and config placeholders

### Phase 2: GUI Shell

- Build main window
- Build left tree and right chat panel
- Implement view switching and empty states

### Phase 3: Local Persistence

- Add SQLite schema
- Save and load projects, sessions, and messages
- Restore recent session state

### Phase 4: Conversation Flow

- Implement send flow
- Add backend client
- Add local LLM client path for desktop-side inference
- Add OpenAI-compatible backend client path
- Add a visible settings entry point for model configuration
- Add provider health check actions
- Add local request logging with latency and error capture
- Add request timeout and error handling
- Add request cancel interaction for long-running calls
- Render structured assistant results
- Reserve gateway protocol endpoints for future server-side cancellation and orchestration
- Add provider profiles, fallback routing, and skill templating in the gateway layer
- Add persistent gateway request records, cooldown-aware routing, and phase-based skills
- Add gateway-side metrics/cost tracking, graded provider health, and adapter abstraction
- Add a first gateway admin panel for operational inspection and provider reset
- Normalize upstream streaming errors so desktop and gateway callers receive structured failures instead of broken chunked responses
- Consolidate gateway error handling so sync and stream paths expose consistent upstream semantics
- Persist normalized gateway `error_type` values and expose them in provider health and request summaries
- Introduce typed gateway provider errors and a first shared retry/cooldown policy table

### Phase 5: Domainization

- Add prompt templates
- Add project-level domain context
- Add quick questions for common scenarios
- Auto-generate session titles from the first meaningful user prompt

### Phase 6: Windows Delivery

- Add app icon and version info
- Package executable
- Build a distributable Windows installer package
- Add repeatable packaging scripts for developers
- Define installation path, shortcuts, and upgrade behavior
- Validate clean startup on Windows

## 9. MVP Acceptance Criteria

- User can create multiple projects
- Each project can contain multiple sessions
- Session history persists after restart
- Quick buttons can create useful domain prompts
- Responses are rendered clearly and consistently
- If local LLM is configured, users can chat with it directly in the dialogue window
- If an OpenAI-compatible backend is configured, users can chat with it directly in the dialogue window
- Users can update provider settings from the desktop app
- Users can run a provider connection test before sending a message
- The app stores local request logs with status and latency
- Users can cancel waiting for a long-running reply
- New generic sessions get a meaningful auto-generated title
- App can be packaged into a Windows executable
- App can be packaged into a Windows installer for end-user delivery

## 10. Key Risks

- Turning into a generic chatbot instead of a domain console
- Exposing API keys in the desktop client
- Returning unstructured answers that users do not trust
- Pulling in too much real-time integration too early
- Local LLM resource usage may affect responsiveness on low-spec machines
- Different OpenAI-compatible backends may vary in API fidelity and response shape

## 11. Immediate Next Steps

1. Create the Qt widget skeleton
2. Define local SQLite schema
3. Implement project and session CRUD
4. Implement message send and response flow
5. Wire in backend API contract
6. Add local LLM provider support for direct desktop chat
7. Add OpenAI-compatible provider support for remote desktop chat
8. Expand gateway routing, skill management, and service-side observability
