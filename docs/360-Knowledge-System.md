# Knowledge System

## Goal

Define how `recon` ingests, indexes, retrieves, cites, and refreshes knowledge so the assistant can answer with grounded sources instead of raw prompt memory alone.

## Scope

### Included

- local files, uploaded files, and URLs as first-class sources
- document parsing and chunking
- searchable metadata
- retrieval with citations
- source freshness and reindex state
- permission-aware source visibility

### Excluded

- full enterprise connector catalog in the first phase
- opaque retrieval with no source attribution
- automatic web crawling beyond explicit sources

## Source Model

Recommended levels:

- `knowledge_source`: user-visible source definition
- `knowledge_document`: normalized document extracted from a source
- `knowledge_chunk`: retrieval unit

Sources may begin as:

- uploaded file
- local path
- saved URL
- future external connector

## Behavior

- ingestion should normalize content into documents and chunks
- retrieval should return both content and citation metadata
- the assistant should surface source labels and snippet-level references when knowledge retrieval materially influences the answer
- users must be able to reindex, disable, or delete a source
- workspace visibility rules must be enforced before retrieval

## Retrieval Rules

- retrieval should combine semantic matching and metadata filtering when available
- profile and workspace settings may define default source groups
- retrieval should stay bounded by token budget and citation quality
- low-confidence retrieval should not silently masquerade as known fact

## Data Impact

Recommended new entities:

- `knowledge_sources`
- `knowledge_documents`
- `knowledge_chunks`
- `retrieval_logs`

Suggested tracked fields:

- source type, label, owner, scope
- content hash and version
- indexing status
- citation metadata
- last indexed time
- last retrieval time

## UI Impact

- users need a source library rather than a hidden attachment-only model
- source detail pages should show ingest status and last refresh time
- retrieved sources should be inspectable from the answer or task result

## Implementation Notes

- metadata may remain in SQLite while vector storage stays pluggable
- URL ingestion should build on the bounded fetch discipline already introduced for link preview
- the first phase should prioritize explicit user-managed sources over automatic crawling

## Relationship To Existing Docs

- complements `docs/290-Attachments-And-Rich-Content.md`
- complements `docs/320-Gateway-Link-Preview.md`
- complements `docs/330-Generic-Assistant-Platform.md`
