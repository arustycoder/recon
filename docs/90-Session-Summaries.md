# Session Summaries

## Goal

Keep the project tree readable by turning generic session names into topic-oriented labels automatically.

## Scope

### Included

- generate a short title from the first meaningful user request
- persist that title back to the current session when the name is still generic
- store a lightweight session summary field for later use

### Excluded

- model-generated summaries
- periodic summary refresh after every turn
- long-form conversation recap pages

## Behavior

- if a session is still named like `默认对话` or `新对话`, the first meaningful user message should rename it
- the generated title should stay short and readable in the tree
- the summary field should reuse the same short text in the first implementation
- explicit user renames should win over automatic naming

## Data Impact

- use the existing `sessions.summary` field
- update `sessions.name` only when the current name is generic

## Implementation Notes

- keep the first implementation heuristic and local
- do not spend an extra model request just to name the session
- prefer stable, deterministic naming over cleverness
