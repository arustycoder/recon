# Gateway Link Preview

## Goal

Add a gateway-managed hyperlink preview feature so the desktop app can render richer link cards without fetching remote pages directly.

## Scope

### Included

- a dedicated gateway endpoint for link preview
- bounded remote fetch for supported `http` and `https` URLs
- extracted preview metadata such as title, content type, and short summary
- gateway-side timeout, size limit, and domain restrictions
- desktop consumption of preview data in later implementation phases

### Excluded

- full-page ingestion into model context by default
- arbitrary binary download
- browser automation
- unrestricted crawling
- desktop-side direct remote fetch as the primary implementation path

## Why Gateway

The gateway is the correct place for this capability because it can centralize:

- network egress policy
- domain allowlist / denylist rules
- timeout enforcement
- response size limits
- HTML cleaning and metadata extraction
- request logging and abuse controls

Keeping this in the desktop client would spread network policy and parsing logic across every operator machine.

## Proposed API

### Endpoint

- `POST /api/link-preview`

### Request

```json
{
  "url": "https://example.com/report"
}
```

### Response

```json
{
  "status": "ok",
  "url": "https://example.com/report",
  "title": "March Operations Report",
  "summary": "A short bounded summary extracted from the target page.",
  "content_type": "text/html",
  "fetched_via": "gateway"
}
```

### Error Response

```json
{
  "status": "error",
  "error_type": "preview_timeout",
  "detail": "Preview fetch exceeded the configured timeout."
}
```

## Desktop Behavior

In the future desktop implementation:

- plain links may still render immediately as clickable anchors
- if preview is enabled, the desktop should call the gateway for preview metadata
- the desktop should render a `Link Card` using preview data when available
- preview failure should degrade to a normal clickable link, not block message rendering

## Gateway Constraints

The gateway preview implementation should enforce:

- short timeout, for example `3-5s`
- bounded response size, for example `<= 256 KB` text extraction budget
- `http` and `https` only
- no local file, loopback, link-local, or private-address targets unless explicitly allowed
- no recursive fetch
- HTML/text-focused extraction only

These rules are important to reduce SSRF and oversized-content risk.

## Security Notes

This feature has clear abuse potential if implemented loosely. The gateway must protect against:

- SSRF into local or internal network targets
- very large responses
- slow remote responses
- redirect chains into blocked destinations
- content types that are not useful for preview rendering

The gateway should default to deny and only allow the narrow fetch profile needed for link-card previews.

## Implementation Notes

- start with metadata extraction only:
  - page title
  - content type
  - bounded text summary
- keep preview generation outside the core chat path so link preview failures do not fail a normal chat request
- store preview fetch results in request logs or dedicated gateway preview logs only if operationally useful
- do not expand this phase into generic web browsing; keep it narrowly scoped to message-card enrichment
