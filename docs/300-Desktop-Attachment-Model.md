# Desktop Attachment Model

## Goal

Move desktop attachment handling from transient composer state to a persistent local model that can:

- keep file references associated with a message
- survive app restart
- render attachment cards inside the conversation history
- stay desktop-local without introducing gateway upload APIs

## Scope

### Included

- local `attachments` table
- local `message_attachments` mapping table
- storing normalized file metadata such as path, name, size, media type, and optional excerpt
- loading message-attached files back into the conversation UI
- attachment chips in the composer with single-item remove support
- drag-and-drop file add support in the composer

### Excluded

- remote upload
- gateway-managed attachment ids
- attachment deduplication across machines
- image thumbnails and binary previews

## Model

- `Attachment`
  - `id`
  - `path`
  - `name`
  - `media_type`
  - `size_bytes`
  - `excerpt`
  - `created_at`

- `message_attachments`
  - `message_id`
  - `attachment_id`
  - `display_order`

## UI Behavior

- selected files are shown as removable chips before send
- sent messages keep attachment cards in the history
- text attachments still contribute bounded excerpts to the prompt
- non-text attachments remain visible as file references in the message card

## Implementation Notes

- keep message `content` as the prompt payload that the assistant actually sees
- keep attachment persistence separate from message content parsing
- prefer path-based local references for this phase
- treat attachment excerpting as a desktop preprocessing step
