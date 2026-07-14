# PLAN — Audit the Software and Non-Instrument keyword lists

**For the executing agent (Haiku): read this whole file before editing anything.**
This is a mechanical cleanup with ONE hard rule: you do not invent taxonomy.
When a keyword's category is a judgment call, you put it in the REVIEW list and
move on. You never guess.

## Background — why this exists

`classify_item` in `src/services/data-cleaning/column_filter_and_classify_v3.py`
scores each requisition line against three keyword lists (Instrument / Software /
Non-Instrument) and labels it. That label gates the whole pipeline: only
Instrument and Software rows produce scraper keywords, so a bad keyword list
means the crawler either downloads a vendor's whole catalogue or skips them.

The **Instrument list is DONE** — audited 2026-07-13, 466 terms -> 160. Do not
touch it, and do not touch `_COMPONENT_KEYWORDS` or `_WEAK_HW`.

The **Software (209) and Non-Instrument (518) lists are NOT audited.** They carry
the same three kinds of pollution the Instrument list had, because
`learning_mode` auto-promoted anything it saw 5+ times:

1. **Word fragments** — `cond`, `coded`, `assy`, `secu`, `repl`, `obser`, `insta`.
   (These used to match as substrings; matching is whole-word now, so they are
   mostly inert — but they are still noise and some are real words.)
2. **Generic English / stopwords** — Software: `above`, `below`, `list`, `price`.
   Non-Instrument: `been`, `have`, `only`, `once`, `your`, `will`, `need`, `next`,
   `over`, `four`, `eight`, `three`, `kind`, `great`, `ideal`, `comes`, `away`.
3. **Off-domain vocabulary** — Software is full of IT/DevOps terms that never
   appear in a scientific-equipment requisition: `agile`, `scrum`, `jira`,
   `docker`, `saas`, `paas`, `iaas`, `gdpr`, `hipaa`, `itil`, `cobit`, `mtbf`,
   `mttr`, `azure`, `slack`, `teams`, `webex`, `skype`, `redis`, `mysql`, `json`,
   `yaml`, `toml`, `soap`, `unix`, `linux`, `macos`.
4. **Brand/vendor names** — Non-Instrument: `axon`, `sony`, `cisco`, `zebra`,
   `barco`, `bofa`, `capsa`. Software: `dell`, `adobe`, `prism`, `visio`.
   (Careful: some brands ARE the product — see Rule S3.)

### The live bug this fixes

`classify_item` returns Software only when `sw_score >= 1 AND sw_score > ni_score`.
Junk in the Non-Instrument list inflates `ni_score`, which **suppresses correct
Software labels**. A pCLAMP line that hits one Software term and two junk
Non-Instrument terms (`only`, `your`) is labelled Non-Instrument and never
reaches the scraper. Cleaning the NI list is therefore not cosmetic.

## Ground rules

- **Never edit the `.txt` keyword files.** A future `learning_mode` run rewrites
  them and your work vanishes. All removals go into the frozensets in
  `column_filter_and_classify_v3.py`, which is why they exist.
- **Every phase ends green.** Run `python tests/test_classify_v3.py` and
  `python tests/test_keyword_pruning.py`. If either fails, you broke something —
  fix it or revert that keyword, do not edit the test to make it pass. The one
  exception: adding NEW asserts for behavior this plan asks you to add.
- **Escalate, do not guess.** Anything you are not sure about goes in
  `REVIEW-keywords.md` (see Phase 4) for Kren. A wrong keyword is worse than a
  missing one, because it silently mislabels every future requisition.
- Work from `C:\Projects\Crawler\PROJECTS`. Data is in `C:\Data\Crawler\`.

## Phase 1 — Triage script (mechanical, no judgment)

Write `tools/audit_keywords.py` (new file, throwaway is fine) that loads the
cleaned lists via `load_and_clean_keywords()` and buckets every Software and
Non-Instrument term into:

- **STOPWORD** — appears in `nltk`-style common-English; no external dep needed,
  just hardcode a list: articles, pronouns, prepositions, auxiliaries, numbers
  spelled out, vague adjectives (`great`, `ideal`, `heavy`, `small`, `full`).
- **FRAGMENT** — not a word and not a known abbreviation. Heuristic: length <= 5,
  alphabetic, and not in the domain-abbreviation allowlist you build in Phase 2.
- **IT_JARGON** (Software list only) — the DevOps/enterprise-IT vocabulary listed
  above. Hardcode the set; it is finite.
- **BRAND** — a company name, not a product category.
- **KEEP** — everything else.

Print each bucket, with a count. Commit nothing yet. This script is your evidence;
paste its output into your report.

## Phase 2 — Software list (209 -> expect ~90-120)

The Software list should contain ONLY things that indicate **purchased
software/licences in a research or clinical procurement context**.

- **S1 — Remove all IT_JARGON.** No requisition line for lab software says
  "kubernetes" or "scrum". Add them to a new `_JUNK_SW` frozenset.
- **S2 — Remove STOPWORD and FRAGMENT buckets.** Add to `_JUNK_SW`.
- **S3 — Brands: KEEP the ones that are scientific software, REMOVE generic
  vendor names.** Keep: `matlab`, `labview`, `flowjo`, `graphpad`, `prism`,
  `imagej`, `origin`, `sigmaplot`, `pclamp`, `clampex`, `clampfit`, `imaris`,
  `metamorph`, `zen`. Remove: `dell`, `cisco`, `slack`, `skype`, `webex` (these
  are hardware vendors or comms tools, not purchased research software).
  **`adobe`/`autocad`/`visio`/`revit` are a judgment call → REVIEW list.**
- **S4 — Keep the generic licence vocabulary**: `license`, `licence`,
  `subscription`, `activation`, `seat`, `perpetual`, `maintenance renewal`,
  `software`, `module`, `upgrade`. These are the words that actually catch
  software lines.
- Verify: `PCLAMP 11 SOFTWARE FOR WINDOWS ...` must still classify **Software**.
  `9600-0012 INCUCYTE SCRATCH WOUND SOFTWARE MODULE` must still classify
  **Software**. Add both as asserts to `tests/test_classify_v3.py`.

## Phase 3 — Non-Instrument list (518 -> expect ~350-420)

The Non-Instrument list is a **catch-all and it is allowed to be broad** — that
is its job. Be far more conservative here than in Phase 2. Only remove:

- **N1 — STOPWORDs.** `been`, `have`, `only`, `once`, `your`, `will`, `need`,
  `next`, `over`, `four`, `eight`, `three`, `kind`, `great`, `ideal`, `comes`,
  `away`, `been`, `less`, `more`, `down`, `back`, `left`, `front`, `side`.
  These match half of all English text and inflate `ni_score` against Software.
  Add to a new `_JUNK_NI` frozenset.
- **N2 — FRAGMENTs**: `assy`, `secu`, `repl`, `obser`, `insta`, `prev`, `clin`,
  `univ`, `vert`, `appl`, `wqith` (sic), `onec`, `ucant`, `boxe`, `isola`.
- **N3 — BRANDs**: `sony`, `cisco`, `zebra`, `barco`, `bofa`, `capsa`, `joel`,
  `jess`, `york`, `rice`, `nomad`, `axon`.
  **`axon` matters** — it is Molecular Devices' electrophysiology brand and
  having it in Non-Instrument may be deliberate (their amplifiers ARE
  Non-Instrument per Kren's ruling). Put `axon` in REVIEW, do not remove it.
- **DO NOT REMOVE** the real non-instrument vocabulary even though it looks
  generic: `cable`, `chair`, `desk`, `plate`, `tube`, `vial`, `rack`, `glove`,
  `screw`, `valve`, `waste`, `paper`, `tape`. These are correct and load-bearing.
- Verify: `Office desk` -> Non-Instrument. `Power Cord 110V` -> Non-Instrument.
  `RHD 512-channel Recording Controller` -> NOT Instrument (already asserted).

## Phase 4 — REVIEW list for Kren (this is a deliverable, not a footnote)

Create `tasks/scraper-precision/REVIEW-keywords.md`. One line per term you did
not confidently bucket, in three sections (Software / Non-Instrument / Unsure
which list). For each: the term, which list it is in now, why it is ambiguous,
and your recommendation. Expect 20-40 terms. This file is the point of the whole
exercise — it is where the domain judgment Kren has (and you do not) gets
applied. Do not pad it with terms you could have decided yourself, and do not
bury a real ambiguity in the KEEP bucket to keep it short.

## Phase 5 — Measure, then stop

Run the classify stage only — **do not run the scraper**, it hits real vendor
websites:

    python src/services/pipeline.py --only-classify

Report, as a table, before vs after:
- keyword list sizes (Instrument must still be 160 — if it changed, you touched
  something you should not have)
- the `[v3] Results` type counts per file
- the keyword-gate line from
  `python -c "..."` calling `load_supplier_keywords(r'C:\Data\Crawler\labeled')`
  (supplier count + token count)

Then **stop and hand back to Kren** with: the diff, the REVIEW file, the table,
and the triage script output. Do not run the full pipeline. Do not commit.

## Definition of done

- [ ] `_JUNK_SW` and `_JUNK_NI` frozensets added, wired into `is_too_broad`
- [ ] Instrument list still exactly 160 terms
- [ ] `tests/test_classify_v3.py` and `tests/test_keyword_pruning.py` both green
- [ ] New asserts: pCLAMP and INCUCYTE lines still classify Software
- [ ] `REVIEW-keywords.md` written, 20-40 terms, with recommendations
- [ ] Before/after table reported
- [ ] Nothing committed, scraper never run

## Files

- `src/services/data-cleaning/column_filter_and_classify_v3.py` — the only file
  you edit. Frozensets live near the top: `_JUNK_KEYWORDS`, `_COMPONENT_KEYWORDS`,
  `_WEAK_HW`, and `is_too_broad()` inside `load_and_clean_keywords()`.
- `src/services/classify/software_keywords.txt`,
  `non_instrument_keywords.txt`, `research_instrument_keywords.txt` — READ ONLY.
- `tests/test_classify_v3.py` — the adjudications Kren has already made. Sacred.
