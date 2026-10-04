# DukaanIQ Architecture — Phase 1

## Target flow

Browser UI → FastAPI API → Data Contract / Validation → Analytics Engine → AI Tool Layer → AI Analyst / RAG → JSON responses → Existing Dashboard + Chat UI

## Principles

1. Python is the source of truth for business metrics.
2. The AI interprets calculated results; it does not invent metrics.
3. The frontend consumes backend APIs and should not duplicate business calculations.
4. Inventory/profit capabilities are enabled only when the uploaded data actually contains the required fields.
5. Existing frontend routes remain backward-compatible during migration.

## Backend boundaries

- `app.py`: HTTP/API orchestration and active dataset lifecycle.
- `data_contract.py`: canonical CSV schema, aliases, normalization, validation, capability detection.
- `analytics.py`: deterministic business calculations.
- `ai.py`: AI-facing interpretation layer; to be migrated to tool calling in a later phase.

## Migration strategy

The current analytics layer expects the original Online Retail column names. Phase 2 introduces a canonical DukaanIQ schema and a compatibility adapter so the existing dashboard continues working while analytics is migrated incrementally.
