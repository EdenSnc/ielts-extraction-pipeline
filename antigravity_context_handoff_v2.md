# Context handoff — IELTS PDF extraction pipeline (new session, prior history lost)

You're picking up an in-progress pipeline. Read this fully before touching anything or re-running work that's already done.

## Goal
Extract 23 IELTS PDFs (text + cropped visual assets + structured chart/table data) into a single validated JSON dataset to seed a mock IELTS testing platform's backend.

## Hardware constraints — non-negotiable
- Local machine: Windows, CPU-only for practical purposes. Local is for file I/O, PDF rendering/splitting, single-file debugging, and lightweight scripts only.
- ALL layout detection, OCR at scale, and VLM inference runs on Kaggle (free tier: T4x2 GPU). Never attempt these locally as a batch engine.
- Kaggle auth: token-based (KGAT_ format), saved at C:\Users\Admin\.kaggle\access_token. Account is phone-verified and identity-verified (Persona) — if any tool reports an "unverified account" error, that diagnosis is wrong; dig further.
- `kaggle` python package needed an upgrade (`pip install --upgrade kaggle`) to fix a version-skew bug parsing the newer token format — check this was actually applied.
- Kernel push has a hard 1MB source-size API limit — strip notebook outputs before pushing, or it 400s.

## Containment — strict, non-negotiable
All pipeline code lives ONLY in `C:\Users\Admin\Documents\IELTS-PDFS\pipeline`. A prior session accidentally edited files in an unrelated project (a landing page site, `IELTS-Lab-Oran-main`) — manually reverted by the user already. Never touch anything outside the pipeline folder, for any reason, regardless of what context seems to justify it.

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
- **Layout detection**: DocLayout-YOLO (`DocStructBench` weights) on Kaggle T4x2, using `doclayout_yolo.YOLOv10`'s own native API directly — NOT wrapped through vanilla `ultralytics.YOLO` (see Phase 2 debugging history below for why).
- **OCR/text extraction**: docTR primary, Surya fallback. Surya (0.20.0+) auto-detects hardware: NVIDIA GPU → `vllm` backend (fine on Kaggle), no GPU → `llamacpp` backend requiring a compiled binary (this is real, verified by inspecting the actual package — don't fight it, never run Surya locally on the Windows CPU box).
- EasyOCR rejected — weaker than Surya/docTR/PaddleOCR on dense document text specifically.
- PaddleOCR/PP-StructureV2: table-structure recovery only, not general OCR.
- **Visual interpretation**: Qwen2.5-VL on Kaggle T4x2. **No paid APIs anywhere** — explicitly declined by user, Kaggle-only, final.

## Schema
Finalized, flat/relational-DB-friendly (one record per section, maps to SQL tables with FKs). File: `ielts_dataset_schema.json` — get the latest copy from the user, don't assume you have the current one. Key fields and why:
- `book_type` on every test record (denormalized, avoids a join).
- `question_number_start`/`question_number_end` — Cambridge's "choose TWO letters" format shares one answer pair across two question numbers.
- `content_type: scoreable_question | instructional_non_scoreable` — Trainer/Official Guide books have real non-gradeable pedagogical content; don't force it into question_type or drop it.
- `pdf_page_index` + `printed_page_number` on documents AND visual assets — these differ by an offset (front matter shifts them). Only `printed_page_number` should ever be shown to a human/UI.
- `stripped_watermark_patterns`/`ocr_substitution_warnings` on every provenance block.
- `page_boundary_anomaly_flag` — tuned threshold: only fires on near-identical word counts repeated across 3+ consecutive pages at a high baseline (>10,000 words), or a 10x+ jump landing on an already-high baseline (>1,500 words). Do NOT flag normal sparse-question-page vs dense-passage-page alternation (30-150 words vs 300-600 words) — that's normal book structure. A looser threshold was tried and correctly rejected for false positives.

## Phase 0 & 1 — done and stable
Triage, page rendering, OCR routing, anomaly detection, dual page-numbering all implemented and validated on `13.PDF`. Not in question.

## Phase 2 — Kaggle layout detection — in progress, NOT yet fully verified

### Debugging history (all real, verified against actual package internals along the way — don't re-diagnose these from scratch)
| Run | Error | Root cause / fix |
|---|---|---|
| v11-v12 | `CUDA error: no kernel image is available` | Kaggle was defaulting to a P100 (CUDA sm_60), dropped by PyTorch 2.5+. Fixed with explicit `--accelerator NvidiaTeslaT4` flag on kernel push. |
| v12 | `AttributeError: 'Conv' object has no attribute 'bn'` | `ultralytics.YOLO.fuse()` strips batch-norm attrs incompatibly with this model. |
| v13 | `AttributeError: 'dict' object has no attribute 'shape'` | `ultralytics`' NMS postprocessor expects a tensor; `doclayout_yolo`'s forward() returns a dict — fundamentally incompatible wrapper usage. |
| v14 | Fixed | Switched to `doclayout_yolo.YOLOv10` directly (its own public API, own postprocessing), dropped `ultralytics` wrapper entirely. |
| v14 result | Real result, page 20 of 13.PDF: 13 overlapping boxes detected. Problem found on review: every box covering actual question text (items 8-13) scored 0.319-0.485 confidence, while boilerplate (header/title/instructions) scored 0.65-0.84. **A flat confidence threshold of 0.5 would have deleted all real content and kept only boilerplate** — this was caught before it shipped to batch. Root issue: box #6 covered the entire Q8-13 block as one region while boxes #7-13 separately detected each individual question line — overlapping multi-granularity detections of the same class, not noise. |
| v15/v16 | Claimed fix | IoU containment dedup (drop boxes >90% contained inside a larger same-class box) implemented, claimed to reduce page 20 from 13→6 boxes. **Confirmed the 10-class DocStructBench taxonomy includes `title`, `figure`, `table`, etc. (full list: title, plain text, abandon, figure, figure_caption, table, table_caption, table_footnote, isolate_formula, formula_caption) — `title` fired at 0.924 confidence on a real section header, confirmed genuine.** Also claimed successful `figure` detection on page 30 (map, 0.849 conf) and page 52 (bar chart, 0.951 conf). |

### ⚠️ UNRESOLVED — this is where you actually pick up
The v15/v16 "success" report was sent back with **evidence that didn't match the claims**:
- The page-20 annotated image attached was byte-for-byte the SAME FILE as the earlier v14 image (same filename, same 13 overlapping boxes) — not new evidence of the claimed 6-box dedup result.
- The page 30 and page 52 annotated images were referenced by local file path but never actually attached/shared for review.
- The new 6-box coordinate table used a roughly 1/3-scale coordinate range compared to the old 13-box table, unexplained (possibly a DPI difference between renders, but not confirmed).

**This was rejected. Nothing about IoU dedup or the figure crops on pages 30/52 has been visually verified yet**, even though the underlying claims (10-class taxonomy, title firing, containment logic) may well be real — the class-taxonomy claim in particular is plausible and specific enough to likely be genuine, but the actual dedup RESULT and the actual figure CROPS still need real, current, matching visual proof before anyone signs off.

### Your first task
Get and show ACTUAL CURRENT annotated images (not reused old files, not missing references) for:
1. Page 20 of `13.PDF` post-dedup — should show ~6 non-overlapping boxes, not the old 13.
2. Page 30 (map diagram) — tight figure crop.
3. Page 52 (bar chart) — tight figure crop.

Only after those check out visually does batch ingestion across the remaining 22 PDFs become a reasonable next step. Do not propose or start batch ingestion before this.

## How to work with the user going forward
- Phase-gate discipline: show a sample (1-2 files) before scaling to all 23, at every phase.
- **When reporting results, attach actual current evidence (fresh screenshots/images/raw output), not descriptions of evidence or reused old files.** This project has had multiple instances of confident "✅ verified" claims that didn't hold up against the actual attached evidence — always assume the human reviewer will check the raw artifact, not just the summary, because they have been doing exactly that.
- When something fails, get the actual raw error/traceback/HTTP response before proposing a root cause. This project has had both confidently-wrong explanations (Kaggle "unverified account" story — false, account was fully verified) and confidently-right ones (Surya/llama.cpp backend claim — true, verified by inspecting the actual package) — there's no shortcut here, every claim gets checked against real evidence before being accepted, in either direction.
- Don't make architectural or schema decisions unilaterally; flag tradeoffs and wait for confirmation.
