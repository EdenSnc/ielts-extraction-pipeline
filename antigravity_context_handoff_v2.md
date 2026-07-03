# Context handoff — IELTS PDF extraction pipeline (new session, prior history lost)

You're picking up an in-progress pipeline. Read this fully before touching anything or re-running work that's already done.

## Goal
Extract 23 IELTS PDFs (text + cropped visual assets + structured chart/table data) into a single validated JSON dataset to seed a mock IELTS testing platform's backend.

## Hardware constraints — non-negotiable
- Local machine: Windows, CPU-only for practical purposes. Local is for file I/O, PDF rendering/splitting, single-file debugging, and lightweight scripts only.
- ALL layout detection, OCR at scale, and VLM inference runs on Kaggle (free tier: T4x2 GPU). Never attempt these locally as a batch engine.
- Kaggle auth: token-based (KGAT_ format), saved at C:\Users\Admin\.kaggle\access_token. Account is phone-verified and identity-verified (Persona) — if any tool reports an "unverified account" error, that diagnosis is wrong; dig further.
- `kaggle` python package needed an upgrade (`pip install --upgrade kaggle`) to fix a version-skew bug parsing the newer token format — check this was actually applied.
- Both polling scripts (`pipeline/poll_kernel.py` and `pipeline/poll_vlm_kernel.py`) now invoke Kaggle via the explicit `KAGGLE_CLI` executable path + explicit `env` (`KAGGLE_KEY` from `C:\Users\Admin\.kaggle\access_token`, `KAGGLE_USERNAME='senoucielamine'`) rather than a bare `kaggle` shell command, to avoid PATH/version-skew failures.
- Kernel push has a hard 1MB source-size API limit — strip notebook outputs before pushing, or it 400s.
- `PYTHONIOENCODING=utf-8` must be set in Kaggle run logs/commands to prevent charmap encoding errors when dealing with Unicode statuses or output.

## Containment — strict, non-negotiable
All pipeline code lives ONLY in `C:\Users\Admin\Documents\IELTS-PDFS\pipeline` and the repository root. A prior session accidentally edited files in an unrelated project (`IELTS-Lab-Oran-main`) — manually reverted by the user already. Never touch anything outside the pipeline folder or root repo folders for any reason, regardless of what context seems to justify it.

## Corpus — 23 PDFs, already triaged (verified against actual files, not assumed)
Located at `C:\Users\Admin\Documents\IELTS-PDFS`, 4 subfolders (cambridge academic / general training / ielts trainer / official cambridge guide).
- **10 digital** (>85% pages have real embedded text) → direct PyMuPDF extraction, no OCR.
- **10 have a pre-existing glyphless-font OCR layer** → discard it, run full OCR pipeline regardless. Decided: no cross-checking against the old layer, keep it simple.
- **2 fully scanned**, no text layer.
- **1 hybrid — `19.pdf`**: pages 0-19 are real digital front-matter/publisher-excerpt text, pages 20-139 are scanned images with zero extractable text. Route the whole file through the full OCR pipeline.
- **`18gt.pdf` anomaly**: OCR layer reports a near-identical, suspiciously large word count repeated across many pages — looks like a duplicated/looping text layer bug. Needs a manual page-image spot check before trusting its output.

## Known corpus-specific corruption (verified real)
- **`20.pdf`**: diacritic→digit OCR corruption ("kākāpō" → "kakap6"). Watch for macron-vowel-to-digit pattern broadly.
- **`20.pdf`**: pirate-site watermark ("thudang.com") embedded as literal extractable text on 183/183 pages — must be stripped from body text, logged as stripped.
- **`18gt.pdf`/`19.pdf`**: "@cambridge_library" watermark on cover/early pages.
- **Official Cambridge Guide**: "tailieutienganh.net" watermark on ~41/398 pages.
- All need a denoising pass before text is committed, with what was stripped logged for audit (`stripped_watermark_patterns`/`ocr_substitution_warnings` fields exist in schema for this).

## Tool stack (decided, with reasons — don't re-litigate)
- **Layout detection**: DocLayout-YOLO (`DocStructBench` weights) on Kaggle T4x2, using `doclayout_yolo.YOLOv10`'s own native API directly — NOT wrapped through vanilla `ultralytics.YOLO`.
- **OCR/text extraction**: docTR primary, Surya fallback. Surya (0.20.0+) auto-detects hardware: NVIDIA GPU → `vllm` backend (fine on Kaggle), no GPU → `llamacpp` backend requiring a compiled binary (never run Surya locally on the Windows CPU box).
- EasyOCR rejected — weaker than Surya/docTR/PaddleOCR on dense document text specifically.
- PaddleOCR/PP-StructureV2: table-structure recovery only, not general OCR.
- **Visual interpretation**: `Qwen/Qwen2-VL-2B-Instruct` run on Kaggle T4x2. **No paid APIs anywhere** — explicitly declined by user, Kaggle-only, final.

## Schema
Finalized, flat/relational-DB-friendly (one record per section, maps to SQL tables with FKs). File: `ielts_dataset_schema.json`. Key fields:
- `book_type` on every test record (denormalized, avoids a join).
- `question_number_start`/`question_number_end` — Cambridge's "choose TWO letters" format shares one answer pair across two question numbers.
- `content_type: scoreable_question | instructional_non_scoreable` — Trainer/Official Guide books have real non-gradeable pedagogical content; don't force it into question_type or drop it.
- `pdf_page_index` + `printed_page_number` on documents AND visual assets — these differ by an offset (front matter shifts them). Only `printed_page_number` should ever be shown to a human/UI.
- `stripped_watermark_patterns`/`ocr_substitution_warnings` on every provenance block.
- `page_boundary_anomaly_flag` — tuned threshold: only fires on near-identical word counts repeated across 3+ consecutive pages at a high baseline (>10,000 words), or a 10x+ jump landing on an already-high baseline (>1,500 words). Do NOT flag normal sparse-question-page vs dense-passage-page alternation (30-150 words vs 300-600 words).
- `answer_constraints` now contains `must_be_from_text` (extracted from instruction text).
- `AnswerRecord` contains `variants` (pre-expanded acceptable strings), `needs_review` (flagged for human verification on ambiguity/exclusions), and `review_reason`.

## Completed Phases

### Phase 0 & 1 — Done and stable
Triage, page rendering, OCR routing, anomaly detection, dual page-numbering all implemented and validated on `13.PDF`.

### Phase 2 — Layout Detection (Fully Resolved & Verified)
- Switched to `doclayout_yolo.YOLOv10` directly to fix CUDA errors and NMS post-processing bugs.
- Confirmed DocStructBench 10-class taxonomy (title, text, abandon, figure, figure_caption, table, etc.).
- Same-class and cross-class (e.g. abandon vs title overlap on running headers) deduplication confirmed and verified on:
  - Page 20 (questions deduped cleanly at full resolution, resolving scale-down confidence drop issues).
  - Page 30 (map crop verified).
  - Page 52 (bar chart crop verified).
- Tier 1 rendering preparation complete: General Training representative `13gt.pdf` split/rendered to image files.

### Phase 4 — VLM Visual Interpretation (Baseline Complete)
- Running local script `crop_assets.py` to extract cropped visual assets from full-res page images based on layout coords.
- Pushing crops to Kaggle via `upload_dataset_patch.py` (`ielts-13-crops-v1`).
- Kaggle kernel running `vlm_interpretation.ipynb` using `Qwen/Qwen2-VL-2B-Instruct` successfully processes crops (transcription, classification, structured JSON extraction).
- Results downloaded to `vlm_pipeline/vlm_interpretation_results.json`.

#### VLM structured_data quality fixes (COMPLETE & VERIFIED against re-run results)
Two confirmed bugs in the previous run were traced and fixed in `pipeline/rebuild_vlm_nb.py`, and `vlm_pipeline/vlm_interpretation.ipynb` was regenerated from it:
- **Token truncation** (page 15 flowchart returned only 1 step): `max_new_tokens` raised 512 -> 1536.
- **Map prompt placeholder echo** (page 30 `approx_location` = `"Top-Left | Center | Bottom-Right"`): the prompt's example JSON *was* the placeholder, so the model copied it. Rewrote the map `struct_prompt` to use a single concrete example (`"Center"`) plus an explicit enum of the only allowed location values.
- **Validation wrapper**: added `validate_structured_data(asset_type, structured_data, alt_text)` in the notebook; every result now carries `needs_review` + `review_reason` and prints a WARNING when a known failure mode is detected (empty/placeholder steps, `"|"`/out-of-enum map locations, empty/placeholder chart series).
- Added `pipeline/check_vlm_results.py` verification helper (reads the Windows results path; on the Linux VM the same logic is run against the repo-relative `vlm_pipeline/vlm_interpretation_results.json`).

**Verified against the re-run results now on master** (`vlm_pipeline/vlm_interpretation_results.json`, regenerated on Kaggle after the fixes):
- Page 15 (flowchart): **3 steps** (was 1) — `step_1` Select seeds..., `step_2` Decide on the type of seeds..., `step_3` After about 3 weeks, record the plant's growth. `needs_review=False`.
- Page 30 (map): **2 labels** with real single-value locations — `'City Hospital 2007' -> 'Top-Left'`, `'City Hospital 2010' -> 'Bottom-Right'` (no more `"Top-Left | Center | Bottom-Right"` placeholder). `needs_review=False`.
- Page 19 (table) and Page 52 (bar_chart): `structured_data` present, `needs_review=False`.

The VLM JSON extraction wrapper + validation (Next Steps **Item 3**) is **complete** — token-truncation and map-placeholder bugs are gone and the validation wrapper confirms no `needs_review` flags on the current corpus sample.

### Answer Key and Word Limit Parsing (Fully Resolved & Verified)
- `answer_key_parser.py` (v3) uses a tokeniser with look-ahead to handle Cambridge two-column split-line format (`<number>\n<answer>`) and `IN EITHER ORDER` pairs.
- Added coordinate-based spatial entry point `parse_answer_key_page(page)` which splits blocks by x-midpoint and sorts by y0 to prevent reading-order column interleaving.
- Integrated `answer_key_expander.py` which expands parenthetical optional prefix/suffixes (`(the) hospital` -> `['hospital', 'the hospital']`) and slash alternatives, and flags exclusions like `(not ...)` or cross-slash context ambiguity for human review.
- `word_limit_parser.py` extracts max_words, allow_numbers, and `must_be_from_text` (via search for "from the passage/text" in instructions) into `AnswerConstraint`.
- All unit and integration tests (31/31 for parser, 6/6 for expander, 6/6 for word limit) pass and are committed to `master`.

## Current Work & Next Steps
1. **Bounding-box padding**: Implement 10-20px padding (clamped to page bounds) where asset cropping occurs.
2. **Watermark fuzzy-matching**: Implement fuzzy-matching blocklist for watermarks, gated on appearance frequency across multiple pages.
3. **Robust VLM JSON extraction wrapper + Pydantic validation**: Done — `validate_structured_data` (plain-dict validation, not Pydantic) is implemented, wired into results via `needs_review`/`review_reason`, and verified against the re-run results (see Phase 4 above). Optional future work: formalize with Pydantic models.
4. **Question-number monotonic sequence check**: 1-40 unbroken sequence check for Phase 5.
5. **Exclusion-pattern flag**: Human review flags for lines containing `(not ...`.
6. **Tier 1 scaling**: Scale layout detection and extraction to General Training (`13gt.pdf`), Trainer, and Official Guide representative samples.
