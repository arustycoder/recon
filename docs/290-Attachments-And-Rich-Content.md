# Attachments And Rich Content

## Goal

Improve the chat composer and message rendering so users can:

- select local files from the input area
- send file references together with the current prompt
- view clickable hyperlinks directly inside messages
- read markdown-style tables as real table-like content instead of plain text

## Scope

### Included

- a plus-button attachment entry on the left side of the chat input
- local multi-file selection from the desktop app
- a visible attachment summary above the input area before send
- local extraction of small text-file excerpts for prompt context
- hyperlink rendering for `http`, `https`, and local `file://` links
- markdown table rendering inside message cards

### Excluded

- binary file upload to the gateway
- image preview and multimodal model input
- drag-and-drop upload
- attachment lifecycle APIs on the gateway
- rich spreadsheet editing in the desktop app
- gateway-managed hyperlink preview implementation in this phase

## Attachment Behavior

- selected files are shown in the composer before send
- text-like files may contribute a bounded excerpt to the outgoing user message
- binary or unsupported files are sent as structured references only
- the first version keeps attachment handling desktop-local and does not introduce a gateway upload protocol

## Rich Content Rendering

- messages should continue to default to safe text rendering
- links should be clickable
- markdown tables should be converted into a readable HTML table layout
- unsupported markdown features should degrade gracefully to plain text
- richer remote hyperlink preview should be handled by the gateway in a later phase rather than fetched directly by the desktop client

## Implementation Notes

- keep the stored message model text-first in the current phase
- escape arbitrary message text before converting supported rich features
- cap attachment text extraction to avoid oversized prompt payloads
- prefer explicit UI hints over silent attachment injection
