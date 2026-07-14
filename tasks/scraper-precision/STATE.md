# STATE — Scraper precision: stop generic keywords pulling whole vendor catalogues

## Goal
Cut "hot" PDF downloads to only what the requisition sorting actually identifies as Instrument/Software (was: Broadax pulled 500+ PDFs off the keyword "server").

## Invariants / decisions
- Pipeline stage order is Clean -> **Classify -> Scrape** -> Supplier Resolution -> Crossref. Classify MUST run before scrape: the TYPE sorting gates what the crawler looks for.
- Scraper keywords come ONLY from labeled `*_classified_v3.xlsx` rows with Type in {Instrument, Software} (`load_supplier_keywords` in pipeline.py). Fail-closed: no classified files -> scraper refuses to run.
- `prune_generic_keywords` (pipeline.py) drops doc-type words, category nouns (server, system, kit...), and cross-vendor tokens; vendor with nothing distinctive left = skipped entirely.
- Engine backstop: `max_pdfs_per_supplier: 50` in DEFAULT_SITE_CONFIG (scraper_engine.py), per-domain overridable.
- PDF blocklist now rejects HR/corporate docs (careers, candidate, working-at, sustainability, investor) — they carry the vendor's brand + the word "guide" and slipped past the allowlist.
- **Keyword matching is WHOLE-WORD** (`_count_hits`). Bare substring matching scored "lysis" in "anaLYSIS", "ella" in "cancELLAtion", "contro" in "CONTROlled" — that is what made one MULTICLAMP row Instrument and eleven identical rows Non-Instrument.
- **Instrument bar**: ONE unambiguous term (centrifuge, microscope, freezer) is enough; `_WEAK_HW` terms (meter, analyzer, balance, rotary, furnace, electrophoresis) need a 2nd hit. The old flat 2-hit bar was only compensating for a dirty list and was rejecting real instruments.
- **Rig components are NOT Instruments** (Kren's ruling): `_COMPONENT_KEYWORDS` (controller, amplifier, microelectrode, headstage, motor, pulser, rotor, thermocouple...) moved from Instrument to Non-Instrument. MultiClamp 700B and RHD Recording Controller are components of an ephys rig, not instruments.
- Rules A/B never promote rider lines (`_is_rider`: shipping, cords, warranty, install, removal — word-boundary regex, because bare substrings mislabeled Pentax/Stereotaxic). Rule B additionally requires `Unit Price >= _RULE_B_MIN_PRICE` ($1,000, Kren's knob).
- **Never edit the keyword .txt files** — a `learning_mode` run would overwrite them. All removals live in frozensets in `column_filter_and_classify_v3.py`.
- `learning_mode` is **DORMANT and must stay that way**. It is NOT in the pipeline path (pipeline -> column_filter_and_classify_v3, which has no learning). The learning code is in `classify/adaptive_excel_processor.py`, only reachable from monitor UIs / service scripts; no such service is installed. `"learning_mode": true` in pipeline_config.json is a DEAD KEY.
- All data in C:\Data\Crawler\ (input/labeled/output). Pre-audit output backed up to `C:\Data\Crawler\output_backup_2026-07-13`.

## Done
- Keyword pruning (category nouns, doc words, cross-vendor, vendor-brand analysis), classify-before-scrape reorder, Type-gated keyword loading, 50-PDF/supplier cap, HR/corporate PDF blocklist.
- v3 classifier repaired: whole-word matching, strong/weak Instrument bar, components -> Non-Instrument, rider guard, $1k Rule B price gate, `Unit Price` carried into labeled files (6 cols).
- **Keyword audit COMPLETE** (plan: tasks/scraper-precision/PLAN-keyword-audit.md, executed by Haiku, reviewed 2026-07-13):
  - Instrument **466 -> 160** (locked; tripwire verified still 160)
  - Software **285 -> 157** (`_JUNK_SW`: IT/DevOps jargon, stopwords, non-scientific brands)
  - Non-Instrument **928 -> 478** (`_JUNK_NI`: stopwords, fragments, vendor names)
  - Deliverables: REVIEW-keywords.md (26 terms), PHASE5-RESULTS.md, FINAL-RESULTS.md
- Tests: **7 pass** (`pytest tests/test_classify_v3.py tests/test_keyword_pruning.py`). Every adjudication Kren made is asserted, so it cannot silently regress.

## Review findings (2026-07-13, this session) — audit is ACCURATE, with 2 fixes
1. **FIXED**: `test_software_classification` was defined but not called from `__main__`, so `python tests/test_classify_v3.py` (the command in the plan's DoD) silently skipped it. Now called.
2. **`prism` removal is CORRECT, but REVIEW-keywords.md's reasoning is wrong.** The file says "KEEP — GraphPad Prism is research statistics software". The data says otherwise: `prism` appears 14x, ALL optical prisms (VERTICAL PRISM BAR, DIC PRISM); `graphpad` appears 0x. Right decision, wrong rationale — do not "correct" it back.
3. `adobe`/`autocad` removals are inert (0 rows in the data either way).
4. Cosmetic: `_JUNK_SW` lists agile/scrum/jira/docker/azure twice (frozenset dedups; harmless).

## End-to-end validation COMPLETE (2026-07-14 06:43–07:00 UTC-4)
✓ **Full pipeline run with audited keyword lists:** 4,271/17,201 rows classified Instrument/Software → 100 supplier keyword sets, 1,682 tokens, 8 suppliers dropped (no distinctive keywords).
✓ **Scraper results:** 903 pages crawled, **31 PDFs downloaded**, 77 suppliers processed, **ZERO per-supplier cap warnings** (keywords clean, not generic).
✓ **Quality gates passed:** Broadax absent (goal: stop 500+ generic-keyword pulls). Spot-check: pClamp docs legitimate (Molecular Devices, 11 PDFs). Zeiss, Heidelberg, Sartorius legitimate instrument vendors.
✓ **All pipeline stages OK** (data_cleaner, classify, scraper, crossref). Crossref matched 6 items from PDFs to master list.

## Next (post-validation)
1. ✓ Moved output directory (reset for fresh run)
2. ✓ Ran `python src/services/pipeline.py` - completed 6:43–07:00 UTC-4
3. ✓ Validated: Keyword gate 4,271/17,201 rows; zero cap-reached warnings; Broadax absent; 31 PDFs legitimate
4. ✓ Spot-checked pClamp docs (Molecular Devices) - real instruments
5. **Commit on `cleanup/ponytail-audit`** - audit-specific files (classifier, pipeline, tests). Pre-existing changes (deleted `run_full_scraper.py`, GUI) included in same commit.
6. Delete `C:\Data\Crawler\output_backup_2026-07-13` once satisfied.

## Open questions
- Delete the dead `"learning_mode": true` key from pipeline_config.json so nobody flips it on and re-rots the lists? (Recommended.) Optional follow-on: harvest-to-review (suggest candidate keywords to a file a human approves) instead of the old auto-promotion, whose validator was inverted — it rejected `microscope` as a "model number" while accepting `buyout`.
- Rule B threshold $1,000 — revisit if real sub-$1k instruments go missing.
- 7 pre-existing test failures elsewhere in the suite (gui session + duplicate-detection tests referencing deleted trees) — unrelated to this work; delete those tests?

## File map
- PROJECTS/src/services/pipeline.py — orchestrator; prune_generic_keywords, load_supplier_keywords (Type-gated), stage order
- PROJECTS/src/services/data-cleaning/column_filter_and_classify_v3.py — THE classifier. Frozensets at top: _JUNK_KEYWORDS, _JUNK_SW, _JUNK_NI, _COMPONENT_KEYWORDS, _WEAK_HW; `_count_hits` (whole-word), `_is_rider`, `_RULE_B_MIN_PRICE`
- PROJECTS/src/services/scraper-full/scraper_engine.py — crawl engine; max_pdfs_per_supplier, _PDF_BLOCKLIST/_PDF_ALLOWLIST
- PROJECTS/src/services/classify/adaptive_excel_processor.py — DORMANT learning code. Do not wire in.
- PROJECTS/tests/test_classify_v3.py, tests/test_keyword_pruning.py, tests/test_pdf_relevance.py — the checks
- tasks/scraper-precision/{PLAN-keyword-audit,REVIEW-keywords,PHASE5-RESULTS,FINAL-RESULTS}.md
