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
Your Backend API
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
- Three quick buttons in MVP:
  - `蒸汽不足`
  - `负荷优化`
  - `能效诊断`
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
- Add request timeout and error handling
- Render structured assistant results

### Phase 5: Domainization

- Add prompt templates
- Add project-level domain context
- Add quick questions for common scenarios

### Phase 6: Windows Delivery

- Add app icon and version info
- Package executable
- Validate clean startup on Windows

## 9. MVP Acceptance Criteria

- User can create multiple projects
- Each project can contain multiple sessions
- Session history persists after restart
- Quick buttons can create useful domain prompts
- Responses are rendered clearly and consistently
- App can be packaged into a Windows executable

## 10. Key Risks

- Turning into a generic chatbot instead of a domain console
- Exposing API keys in the desktop client
- Returning unstructured answers that users do not trust
- Pulling in too much real-time integration too early

## 11. Immediate Next Steps

1. Create the Qt widget skeleton
2. Define local SQLite schema
3. Implement project and session CRUD
4. Implement message send and response flow
5. Wire in backend API contract
