# Task 3 — Table Extraction Acceptance Matrix

The acceptance suite checks generic structure and provenance only. It does not
assign coal-domain meaning to a table based on its filename, page, coordinates,
or position.

| Fixture | Expected structure | Extracted structure | Provenance | Confidence / warnings | Result |
|---|---|---|---|---|---|
| Native bordered numeric PDF | Header plus 2 data rows; blanks, `781.05`, `781.50`, `0.781`, `78.105`, `-5`, and comma-formatted value preserved | 1 table; 3 columns; all raw strings preserved | Page 1, table 1, row/column indexes, source row/column, table bbox, cell bbox for all 9 cells | `NATIVE_TABLE`, 0.90; no warnings | PASS |
| Native borderless PDF | Three aligned rows and columns without ruled lines | 1 table recovered by bounded PyMuPDF text strategy; detector may expose empty spacer rows | Page 1/table 1 and cell indexes; cell geometry only where library supplies it | Text-strategy warning; confidence capped at 0.80 | PASS |
| Two-page repeated-header PDF | Each source page remains independently addressable; repeated headers are retained | 2 table results, page 1/table 1 and page 2/table 1; headers retained | Page number, table number, bbox, cell bboxes per page | Native; no join/removal of repeated evidence | PASS |
| Multiple native tables on one page | Two separate tables, not concatenated | 2 tables on page 1, table numbers 1 and 2 | Independent table bboxes and cell provenance | Native; no warnings | PASS |
| Units and footnote PDF | Unit stays in source header; footnote stays page text; no semantic interpretation | Header `Production (MT)` and footnote text preserved | Page/table/cell provenance plus page text evidence | Native; no fabricated title/meaning | PASS |
| XLSX multi-sheet / merged / formula fixture | Sheet names, cell coordinates, raw formula, displayed value field, blank cells, merged range | `Production` and `Despatch` tables; `B3`, `C3`, `D17`, merged `A1:B1`, blank cells retained | Workbook→sheet→coordinate→row/column→raw value; formula/displayed fields | `NATIVE_XLSX`, 0.99; formula cached value may be unavailable when workbook has no cached result | PASS |
| CSV table | Header/data rows and blank field preserved | Structured table and coordinate-addressed cells | Sheet-independent table plus CSV cell coordinate/row/column | `NATIVE_CSV`; no warnings | PASS |
| Clean scanned/image table | OCR evidence preserved; no invented row/column structure unless reliable | Page classified `SCANNED`, actual Tesseract OCR text/word blocks produced; no fabricated `TableResult` | Page number, OCR method, confidence, word bboxes | Actual OCR; table reconstruction deferred/reviewable | PASS |
| Corrupt PDF | Explicit failure; no false READY/table output | Parser raises explicit parse failure | No partial table result emitted by parser | Failure is visible to pipeline caller | PASS |
| Local Ministry report smoke fixtures (`MoC_Annual_Report_2023-24_Chap2_Production.pdf`, `MoC_Production_Supplies_2023-24.pdf`) | Existing official-style tables should remain parseable without coal-specific parser assumptions | 12 pages/16 tables and 8 pages/8 tables respectively; native cell records emitted | Per-page/table/cell records and bboxes emitted; no URL/live-source dependency | Native extraction; first report emitted 3 parser warnings for review | PASS |

## Exact provenance available today

For native PDFs, the current PyMuPDF path exposes document/page/table bboxes and
cell bboxes. Cell records preserve zero-based `row_index`/`column_index`,
one-based `source_row`/`source_column`, raw value, method, and both `bbox` and
`bounding_box` compatibility keys. XLSX records preserve worksheet name,
coordinate, row, column, raw/formula value, displayed-value field, blank flag,
and merged ranges. CSV records preserve table-relative and source row/column
coordinates.

## Known limits

PyMuPDF does not always return a reliable cell bbox for merged or inferred text
cells; those cells retain `None` geometry and a warning rather than fabricated
coordinates. Borderless detection can include detector spacer rows and is
therefore confidence-limited. Scanned-table OCR evidence is preserved, but
generic row/column reconstruction is intentionally not asserted by Task 3 when
layout evidence is insufficient. Formula recalculation/cached values are only
available when the workbook itself contains them; the parser does not invent a
calculated result.

## Legacy table failures

The three legacy failures were a genuine implementation regression, not stale
expectations or an environment issue. The domain adapter's metric emission was
outside the data-row loop, so only the last row was emitted. The compatibility
boundary now runs that existing adapter once per source data row, and the three
legacy tests pass without changing their assertions. The fixed coordinate-based
table naming was also removed; semantic naming is now derived only from explicit
table/header text, not page position.
