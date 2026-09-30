# COALINTEL Step 1 ingestion audit

## Baseline findings

- Backend: FastAPI in `backend/main.py`; SQLAlchemy models in `backend/app/models`; APIs in `backend/app/api`.
- Frontend: current Next.js app in `frontend/app` and reusable components in `frontend/components`; a separate legacy Vite app remains under `frontend/legacy-vite`.
- Storage: `storage_service.py` supports local storage and Supabase; `ingestion_service.py` calculates SHA-256 and persists uploads.
- Existing pipeline: upload -> `process_file_ingestion()` -> storage/`Document` row with `PENDING` -> FastAPI background task -> `processing_pipeline.py` -> parser -> chunks/legacy metric extraction -> PostgreSQL/optional vector index.
- Existing parser: `parsing_service.py` used PyMuPDF, python-docx and pandas, but OCRed every PDF page with fewer than 100 native characters, flattened DOCX/XLSX/CSV output, and did not support images.
- Existing domain coupling: `normalization_service.py` contains coal-report-specific table interpretation, including coordinate/page-layout assumptions. It is now called through `domain_extraction_service.py`; generic parsing no longer makes those decisions.
- Database: PostgreSQL-first with development SQLite fallback; startup uses `Base.metadata.create_all()` and production migrations are SQL files.
- Tests: extensive pytest suite, but the host initially lacked Python packages, pip, and npm. Core Python dependencies were provisioned for verification; frontend build remains not runnable because npm is unavailable.

## Disposition

| Area | Decision | Reason |
|---|---|---|
| `storage_service.py` | KEEP | Existing local/Supabase abstraction and compatibility tests are valuable. |
| `ingestion_service.py` | MODIFY | Added image formats, source metadata, version linkage and canonical initial state while preserving SHA-256 duplicate behavior. |
| `parsing_service.py` | REPLACE internals / KEEP API shims | New common result model and format adapters; old parser entrypoints remain for callers. |
| `processing_pipeline.py` | MODIFY | Persists generic artifacts and state transitions before optional legacy domain extraction. |
| `normalization_service.py` | KEEP behind adapter | Existing Step 0 metric behavior is preserved but is not part of generic ingestion. |
| `Document` model | MODIFY | Added canonical state, source metadata, confidence, warnings and version fields. |
| New artifact models | ADD | Persist pages, evidence blocks, tables/cells and images with provenance. |
| Official source code | ADD | Isolated connector, registry, version-aware sync service and cron/worker scheduler entrypoint. |
| Existing frontend | MODIFY | Added source status/sync panel and image upload affordances; no second frontend created. |
| Legacy Vite frontend | KEEP | Not removed because its callers/deployment ownership were not established. |

## New generic pipeline

Manual upload and official download both call `process_file_ingestion()`, then the same background processing path:

`acquire -> SHA-256/version check -> store -> DocumentResult parser -> page classification -> selective OCR -> generic table/image persistence -> validation -> canonical processing state`

The legacy metric/domain adapter runs only after the generic evidence has been persisted.

## Known limitations

- The Ministry connector discovers same-host downloadable resources from the configured official page and rejects arbitrary hosts. It does not invent URLs or metadata. Website changes may require connector adjustments.
- Tesseract executable availability is environment-specific; missing OCR dependencies produce warnings/review status rather than fabricated text.
- The scheduler is a small 24-hour due-check abstraction plus `scripts/run_official_sync.py`; deployment should invoke that script from the existing worker/cron facility when one is available.
