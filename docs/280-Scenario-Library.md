# Scenario Library

## Goal

Replace the small fixed quick-button row with a more scalable scenario library that can hold many domain templates without crowding the chat input area.

## Scope

### Included

- a dedicated scenario library panel in the left column
- grouped scene categories
- clickable scene items that populate and send the current prompt
- compatibility with the existing chat/session flow

### Excluded

- user-defined templates
- search
- favorites and recents
- parameterized prompt forms

## UI Behavior

### Placement

- the scenario library sits below the `Project / Session` tree in the left column
- project navigation remains primary
- scene discovery becomes a secondary but always-visible workflow

### Interaction

- category rows organize scenes by topic
- leaf scene rows represent runnable prompt templates
- clicking a scene previews the prompt in the input box
- activating a scene sends it immediately through the current session
- the scenario library is disabled while no session is selected or while a request is running

## Initial Scene Groups

- `供汽与热力`
- `负荷与调度`
- `能效与设备`

## Implementation Notes

- keep the first version tree-based and simple
- reuse the existing message send path instead of building a separate execution path
- treat the scene library as a scalable replacement for fixed quick buttons, not a separate workflow
