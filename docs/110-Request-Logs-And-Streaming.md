# Request Logs And Streaming

## Goal

Improve operator confidence and chat responsiveness by adding:

- a request log viewer for local diagnostics
- real streaming output for providers that support incremental tokens

## Scope

### Included

- read-only request log viewer backed by local SQLite records
- streaming assistant output in the existing message list
- graceful fallback to non-streaming behavior when a provider does not support streaming
- graceful fallback or normalized failure handling when a provider closes the stream early or times out before the first chunk
- cancellation that ignores late streaming chunks and final replies

### Excluded

- exporting logs to external systems
- token-level usage analytics
- markdown rendering during streaming
- server-side abort guarantees for every provider

## UI Behavior

### Request Log Viewer

- accessible from the tools menu
- shows recent request rows with:
  - timestamp
  - provider
  - model or endpoint
  - status
  - normalized error type when available
  - latency
  - detail
- optimized for quick troubleshooting instead of full reporting
- supports simple provider and status filters
- supports error-type filtering for normalized gateway/backend failures
- supports clearing either all logs or the currently filtered slice

### Streaming Chat

- after send, the assistant placeholder should begin filling with real streamed text when available
- slow-request messaging should still work before the first chunk arrives
- once streaming starts, the chat should keep appending content into the same assistant card
- if no stream is available, the UI should keep the existing single-reply behavior
- capture and display first-token latency and final total latency in request diagnostics

## Provider Impact

- OpenAI-compatible and Ollama paths should prefer streaming requests when possible
- if an OpenAI-compatible stream breaks before the first chunk, retry once with a non-stream request
- if a stream breaks after partial output, raise a normalized provider error instead of surfacing a raw chunked-read exception
- HTTP backend should prefer the gateway `/api/chat/stream` SSE endpoint when available
- if the HTTP backend stream fails before any useful output arrives, retry once with the synchronous `/api/chat` endpoint
- mock mode may simulate a short streaming sequence for UX consistency

## Implementation Notes

- keep a normalized stream event shape inside the desktop app
- run streaming in worker threads, never on the Qt UI thread
- treat streamed content as transient until the request completes successfully
- write one final request log record per completed, errored, or canceled request
- when token usage is reported by the provider, persist it alongside the request log
- when the gateway returns a normalized `error_type`, persist it alongside the desktop-side request log
- avoid leaking low-level transport errors such as incomplete chunked reads directly into the user-facing UI
