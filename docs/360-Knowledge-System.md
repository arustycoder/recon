# Knowledge System

## Goal

Define how the assistant ingests, indexes, retrieves, cites, and refreshes external knowledge so answers can be grounded in managed sources.

This document assumes the system architecture in `docs/330-Generic-Assistant-Platform.md` and the request and policy constraints described in `docs/420-Request-Runtime.md` and `docs/370-Safety-And-Permissions.md` [1][2][3].

## Scope

### Included

- files, URLs, notes, and future connectors as sources
- parsing, normalization, and chunking
- metadata-aware retrieval
- source citations
- freshness and reindex state
- permission-aware visibility

### Excluded

- opaque retrieval with no attribution
- uncontrolled web crawling
- connector-specific implementation details

## Core Objects

### Collection

A logical group of sources visible to a workspace, team, or profile.

### Source

A user-visible knowledge asset such as a file, URL, or external connector target.

### Document

Normalized content extracted from a source.

### Chunk

The retrieval unit used during search and grounding.

## Lifecycle

1. source registration
2. content extraction
3. normalization
4. chunking and indexing
5. retrieval and citation
6. refresh, archive, or deletion

## Retrieval Rules

- retrieval should combine semantic relevance with metadata filters when available
- retrieval must honor workspace and policy visibility
- low-confidence retrieval should not be presented as fact
- any answer materially shaped by retrieval should expose citations
- source freshness should be inspectable at the source level
- retrieval should not bypass policy just because a source is highly relevant [3]

## Data Impact

Recommended entities:

- `knowledge_collections`
- `knowledge_sources`
- `knowledge_documents`
- `knowledge_chunks`
- `retrieval_events`

Suggested fields:

- owner and scope
- source type
- content hash and version
- indexing status
- sensitivity label
- citation metadata
- last indexed time
- last retrieved time

## Client Impact

- users need a source library, not only raw attachment storage
- retrieval-driven answers should expose source labels and snippets
- source pages should show ingest status, freshness, and visibility

## References

[1] `docs/330-Generic-Assistant-Platform.md`

[2] `docs/420-Request-Runtime.md`

[3] `docs/370-Safety-And-Permissions.md`
