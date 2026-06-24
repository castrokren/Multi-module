# IMPLEMENTATION PLAN: Phase 2 Classifier Hybrid (Keywords + Context)

**Plan ID:** IMPL-phase2-classifier  
**Duration:** 4 weeks (concurrent tracks)  
**Team Lead Coordinator:** Kren Castro  
**Created:** 2026-06-23  
**Based on Spec:** `2026-06-23-phase2-classifier-hybrid-plan.md`

---

## PHASE 0: Documentation Discovery Summary

### Existing Classifier Architecture (v3)
- **File:** `src/services/data-cleaning/column_filter_and_classify_v3.py`
- **Keyword Files:** `docs/guides/documents/<type>_keywords.txt` (3 files)
  - `research_instrument_keywords.txt` (263 keywords, includes Phase 1 additions)
  - `software_keywords.txt`
  - `non_instrument_keywords.txt`
- **Classification Logic:**
  - Loads keywords, removes conflicts (duplicates across categories)
  - Counts keyword matches in text
  - Thresholds: 2+ for Instrument, 1+ for Software, 1+ for Non-Instrument
  - Priority order: Instrument > Software > Non-Instrument
  - Returns "Unknown" if no threshold met

### Phase 1 Additions (Lines 221-263 in research_instrument_keywords.txt)
- Medical Imaging: ultrasound, x-ray, ct scanner, manometry, ecg
- Specialized Lab: sample loop, hplc connector, peek tubing
- Training Equipment: simulation trainer, anatomical model
- Power Systems: ups system, power management
- Transducers: acoustic transducer, pressure transducer, air sensor

### Current State
- **Test Dataset:** 5,727 items total
- **After Phase 1:** 1,134 Unknown items (19.8%)
- **Phase 2 Target Dataset:** 706 Unknown items (remaining after Phase 1 deployment)
- **Phase 2 Goal:** Reduce Unknown to <400 items (<15% of total), 25%+ Instrument

### Allowed APIs & Patterns (Phase 2a & 2b)
1. **Keyword file format:** One keyword per line, lowercase, comments with `#`, organized by category
2. **Conflict detection:** Load 3 files, find intersections (set operations)
3. **Keyword matching:** Simple substring match (`if kw in text`)
4. **Threshold logic:** Score-based classification (see lines 82-91 in v3)
5. **Context rules:** Will be new (Phase 2b design), to be integrated after Phase 2a keywords validated

---

## PHASE 1: WEEK 1 TASKS — Pattern Segmentation & Keyword Extraction

### Week 1 Goal
Analyze 706 Unknown items, segment by research equipment category, extract 100-150 preliminary keyword candidates.

### Day 1-2: Pattern Segmentation

**Responsible:** Data Analyst + Domain Expert (Research Equipment)

**Input Data:**
- 706 Unknown items from Phase 1 deployment (requires extraction from test dataset)
- Item descriptions and metadata

**Tasks:**

1. **Extract Unknown Items Dataset (Day 1, 2 hrs)**
   - From Phase 1 test results, identify all items still classified as "Unknown"
   - Create CSV with: Req ID, Supplier Name, Item Description, metadata
   - Store in `scratchpad/phase2_unknown_items_706.csv`
   - **Verification:** Row count = 706, columns include Item Description

2. **Segment by Pattern (Day 1-2, 4 hrs)**
   - Group Unknown items into research equipment categories:
     - Lab equipment (centrifuges, evaporators, distillers, balance scales)
     - Analytical instruments (spectrometry, chromatography components)
     - Measurement/testing devices (meters, gauges, probes, sensors)
     - Data collection hardware (controllers, interfaces, data loggers)
     - Calibration/reference standards
     - **EXCLUDE:** Medical equipment (Phase 1), generic services
   - Count items per category
   - Identify top 50-100 patterns (most frequent descriptions)
   - **Output:** `scratchpad/phase2_pattern_segments.txt` (category + item count + top patterns)
   - **Verification:** Total items = 706, categories cover 100% of data

3. **Domain Expert Validation (Day 2, 2 hrs)**
   - Review segmentation: Does research equipment focus make sense?
   - Flag items that might not belong (should they be medical? service items?)
   - Approve category boundaries for extraction phase
   - **Output:** Approval notes, any category adjustments

### Day 3-4: Keyword Extraction

**Responsible:** Data Analyst

**Tasks:**

1. **Extract Keyword Candidates (Day 3-4, 6 hrs)**
   - For each research equipment category:
     - Scan item descriptions for key technical terms
     - Extract multi-word phrases: "sample loop", "ultrasonic cleaner", "lyophilizer"
     - Extract single technical terms: "centrifuge", "viscometer", "rheometer"
     - Rank by frequency (count occurrences across Unknown items)
     - Remove overly generic terms: "equipment", "unit", "system" (unless specific: "ultrasound system")
   - Create ranking: High-frequency (10+ items), Medium (5-9), Low (2-4), Single (1)
   - **Output:** `scratchpad/phase2_keyword_candidates_ranked.txt`
     - Format: keyword | category | frequency | source_items_sample
   - **Verification:** 150-200 candidates extracted, ranked by frequency

2. **Category Organization (Day 4, 2 hrs)**
   - Group candidates by research equipment subcategory
   - Organize with section headers (matching Phase 1 structure)
   - Note: Multi-word keywords preferred (e.g., "sample loop" not just "sample")
   - **Output:** `scratchpad/phase2_keywords_organized.txt`

### Week 1 Deliverables Checklist

- [ ] Unknown items dataset extracted (706 items, CSV format)
- [ ] Pattern segmentation complete (5-6 research equipment categories)
- [ ] Keyword candidates extracted (150-200 keywords ranked by frequency)
- [ ] Keywords organized by subcategory (Phase 1 structure followed)
- [ ] Domain expert approval on category boundaries
- [ ] Team sync meeting: Review Week 1 findings, adjust scope if needed

**Decision Gate - End of Week 1:**
- Unknown items properly segmented? → YES/NO
- Keyword candidates ready for validation? → YES/NO
- **If YES:** Proceed to Week 2 validation & conflict resolution
- **If NO:** Identify blocker, adjust approach

---

## PHASE 2: WEEK 2 TASKS — Validation, Conflict Resolution, Deployment Readiness

### Week 2 Goal
Validate keyword candidates, resolve conflicts with Phase 1 keywords, prepare Phase 2a deployment package.

### Day 5-6: Conflict Detection & Resolution

**Responsible:** Implementation Lead + Domain Expert

**Tasks:**

1. **Conflict Detection (Day 5, 3 hrs)**
   - Load Phase 1 keyword files: `research_instrument_keywords.txt`, `software_keywords.txt`, `non_instrument_keywords.txt`
   - Compare Phase 2 candidates against all three files
   - Identify conflicts:
     - Keywords already in Phase 1 (remove duplicates)
     - Keywords appearing in multiple categories (conflicting)
     - Overly-broad single-word keywords (< 4 chars, non-scientific: prefer multi-word)
   - **Output:** `scratchpad/phase2_conflicts_identified.txt`
     - Format: keyword | conflict_type | action (KEEP/REMOVE/MODIFY)
   - **Verification:** 100% of candidates evaluated, conflicts documented

2. **Conflict Resolution (Day 5-6, 4 hrs)**
   - For each conflict:
     - If duplicate: Remove from Phase 2 (already in Phase 1)
     - If cross-category: Keep in most specific category OR use multi-word variant to disambiguate
     - If too-broad: Remove unless domain-specific (e.g., "pcr", "nmr" = scientific acronyms, keep)
   - Finalize clean keyword list (unique to Phase 2, no conflicts)
   - **Output:** `scratchpad/phase2_keywords_final_clean.txt`
   - **Verification:** Zero conflicts between Phase 2a and Phase 1 keywords, confirmed via set intersection

3. **Implementation Lead Verification (Day 6, 2 hrs)**
   - Create validation script:
     ```python
     # Load Phase 1 keywords
     # Load Phase 2 keywords
     # Check for conflicts: hw1 ∩ hw2, sw1 ∩ sw2, ni1 ∩ ni2
     # Check cross-category: hw2 in sw1, hw2 in ni1, etc.
     # Output conflict report
     ```
   - Run validation, confirm zero conflicts
   - Document threshold settings (will use 1, 1, 1 from Phase 1)
   - **Output:** Validation report + conflict confirmation

### Day 7: Sample Testing & Deployment Readiness

**Responsible:** Data Analyst + Implementation Lead

**Tasks:**

1. **Sample Testing (Day 7, 3 hrs)**
   - Select 50-100 Unknown items from Week 1 dataset
   - Run classifier with Phase 2a keywords + (1, 1, 1) thresholds
   - Measure:
     - How many items now classified as Instrument?
     - How many Software? Non-Instrument?
     - How many remain Unknown?
     - Reclassification rate: X% of 50-100 items
   - Manual review: Pick 10-15 reclassified items, verify accuracy
   - **Output:** `scratchpad/phase2a_sample_test_results.txt`
   - **Verification:** Reclassification rate >20% (expected 30%+ if keyword candidates strong)

2. **Deployment Package Preparation (Day 7, 2 hrs)**
   - Final keyword file: `research_equipment_keywords_phase2a.txt`
     - Merge Phase 1 + Phase 2a keywords
     - Organize with section headers (Microscopy, Spectrometry, Lab Equipment, Measurement, etc.)
     - Include comments noting Phase 2a additions
   - Configuration: Thresholds remain (1, 1, 1)
   - Document: Update notes on what changed, why, expected impact
   - **Output:** Ready-to-deploy keyword file + deployment notes
   - **Verification:** File loads without syntax errors, line count matches expected

### Week 2 Deliverables Checklist

- [ ] Conflict detection complete (Phase 2 candidates vs Phase 1 keywords)
- [ ] Conflict resolution applied (clean, unique Phase 2 keywords)
- [ ] Conflict validation script run (zero conflicts confirmed)
- [ ] Sample testing complete (50-100 items, reclassification rate measured)
- [ ] Manual accuracy review done (10-15 items spot-checked)
- [ ] Deployment package ready (merged keyword file + deployment notes)
- [ ] Team sync: Review test results, approve Phase 2a deployment decision

**Decision Gate - End of Week 2 (CRITICAL):**
- Conflict validation passed? (Zero conflicts) → YES/NO
- Sample test shows >20% reclassification? → YES/NO
- Manual review shows accuracy? → YES/NO
- **If YES to all:** Proceed to Week 3 Phase 2a deployment
- **If NO to any:** Identify issue, adjust Phase 2a keywords before deploying

---

## PHASE 3: CONCURRENT WEEKS 1-4 — Context Analysis Design Track (Phase 2b)

### Parallel Execution Note
Phase 2b design happens concurrently with Phase 2a (Weeks 1-4). This track does NOT block Phase 2a deployment. Phase 2b integration happens in Week 4 after Phase 2a is deployed and measured.

### Week 1-2: Vague Item Analysis & Rule Design

**Responsible:** Architecture Designer + Data Analyst + Domain Expert

**Tasks:**

1. **Analyze Vague Item Patterns (Week 1, Days 1-3, 4 hrs)**
   - From 706 Unknown items (Week 1 data), identify vague descriptions:
     - Items with only generic terms: "equipment", "system", "unit", "assembly", "component"
     - Items with no technical specificity (could apply to many categories)
     - Estimate: ~200 of 706 are vague descriptions
   - For each vague item, examine context:
     - Prior items in same quote (what were they?)
     - Supplier metadata (what type of business?)
     - Item position (first item? bundled with others?)
     - Related items (sibling descriptions more specific?)
   - Document patterns: What context clues predict category?
   - **Output:** `scratchpad/phase2b_vague_patterns.txt`
     - Format: pattern_type | example_items | context_clues | predicted_category
   - **Verification:** 100-150 vague items analyzed, patterns documented

2. **Design Context Rules (Week 1-2, Days 4-7, 6 hrs)**
   - Design three rule types:

   **Rule A: Prior Context**
   - Logic: If prior item in quote is classified Instrument + current is vague → boost Instrument probability
   - Implementation: After keyword classification, check prior item classification
   - Confidence: Medium (prior item might be unrelated, but same quote is correlated)
   - Fallback: If prior is Unknown, apply default
   - **Pseudocode:**
     ```
     if current_item.classification == "Unknown" AND prior_item.classification == "Instrument":
         current_item.classification = "Instrument"
         confidence = "medium"
     else:
         keep current classification
     ```

   **Rule B: Metadata Context**
   - Logic: If supplier type is "Lab Equipment Distributor" + item has lab-related terms → Instrument
   - Implementation: Extract supplier metadata, match against supplier database
   - Confidence: Medium-High (supplier specialization is correlated with inventory)
   - Fallback: If supplier metadata missing, skip rule
   - **Pseudocode:**
     ```
     supplier_type = extract_supplier_type(supplier_id)
     if supplier_type in ["lab equipment", "scientific equipment", "analytical"] AND has_lab_keywords:
         boost Instrument probability
     ```

   **Rule C: Bundle Analysis**
   - Logic: For grouped/bundled items, extract dominant item description → classify main item
   - Implementation: Parse multi-item descriptions, extract first/longest/most-specific item
   - Confidence: Low-Medium (bundle items might be unrelated)
   - Fallback: If unclear which is dominant, skip rule (don't guess)
   - **Pseudocode:**
     ```
     if is_bundle(item_description):
         dominant_item = extract_dominant_item(description)
         if dominant_item has keywords:
             classify based on dominant_item
     else:
         keep current classification
     ```

   - **Output:** `scratchpad/phase2b_context_rules_design.txt`
     - Rule definitions with logic, confidence, fallback
     - Implementation pseudocode for each rule
   - **Verification:** 3 rules fully specified, guardrails defined

3. **Safety Validation (Week 2, Days 5-7, 4 hrs)**
   - Design MVP (minimal viable product) rules:
     - Rule A (Prior Context): Safe, proven approach
     - Rule B (Metadata): Requires supplier database validation (might skip if unavailable)
     - Rule C (Bundle Analysis): Risky, requires careful string parsing (might defer to Phase 3)
   - Define safety guardrails:
     - No false-positive risk to Software category (context rules for Instrument only)
     - Clear fallback if context clues ambiguous (don't force classification, keep Unknown)
     - Disable rule if confidence drops below threshold
     - Audit trail: Log which rule applied to which items (for monitoring)
   - Create safety checklist:
     - [ ] No Software misclassification possible
     - [ ] Fallback logic for all rules
     - [ ] Confidence thresholds defined
     - [ ] Logging/audit trails ready
   - **Output:** `scratchpad/phase2b_safety_validation.txt`
   - **Verification:** MVP rules approved, safety checklist complete

### Week 3-4: Integration Specification

**Responsible:** Architecture Designer

**Tasks:**

1. **Integration Spec (Week 3, Days 1-3, 4 hrs)**
   - Define integration points:
     - Phase 2a keywords run first (classification step 1)
     - Context rules apply to Unknown items from Phase 2a (classification step 2)
     - Final output: Instrument/Software/Non-Instrument/Unknown
   - Confidence combination logic:
     - Keyword match = "high" confidence
     - Context rule = "medium" confidence
     - Unknown = "low" confidence
   - Threshold adjustments:
     - For context-ruled items, use lower threshold (context is weaker signal)
     - Example: Keyword-matched Instrument gets score 2+; context-matched gets 1+
   - Data flow:
     - Input: Item description + metadata
     - Step 1: Keyword classification (Phase 2a)
     - Step 2: Context rule check (Phase 2b, for Unknown items)
     - Output: Final classification + confidence + rule applied
   - **Output:** `scratchpad/phase2b_integration_spec.txt`
   - **Verification:** Integration flow clear, data inputs/outputs defined

2. **Implementation Roadmap (Week 4, Days 1-2, 2 hrs)**
   - Phase 2b.1 (Week 4): Integrate Rule A (Prior Context) — low risk
   - Phase 2b.2 (Week 4-5): Integrate Rule B (Metadata) — medium risk (requires supplier data)
   - Phase 2b.3 (Later): Integrate Rule C (Bundle Analysis) — higher risk, defer if needed
   - For each rule:
     - Where in classifier code to add?
     - What functions to create?
     - How to test each rule?
   - **Output:** `scratchpad/phase2b_implementation_roadmap.txt`
   - **Verification:** Implementation tasks clear, assigned to roles

### Week 3-4 Deliverables Checklist

- [ ] Vague item patterns identified (100-150 items analyzed)
- [ ] Context rules designed (3 rules with logic, pseudocode, confidence)
- [ ] MVP rules selected (safe subset for Phase 2b)
- [ ] Safety validation complete (checklist approved)
- [ ] Integration specification written (data flow, thresholds, logging)
- [ ] Implementation roadmap created (Phase 2b.1/2b.2/2b.3 tasks)
- [ ] Team sync: Review context design, approve MVP rules

**Decision Gate - End of Week 2 (Phase 2b):**
- Context rules fully specified? → YES/NO
- MVP rules safe for production? → YES/NO
- Integration spec clear? → YES/NO
- **If YES to all:** Ready for Phase 2b integration (Week 4)
- **If NO:** Adjust rule design, re-review

---

## PHASE 4: WEEK 3 — Phase 2a Deployment

### Week 3 Goal
Deploy Phase 2a keywords, measure impact on remaining 706 Unknown items, decide whether to proceed with Phase 2b integration.

### Day 8-9: Deployment Preparation

**Responsible:** Implementation Lead

**Tasks:**

1. **Deployment Package Review (Day 8, 2 hrs)**
   - Verify deployment package (from Week 2):
     - `research_equipment_keywords_phase2a.txt` ready
     - Syntax verified (no blank lines, no special chars, lowercase)
     - Line count matches expected (~150-200 Phase 2a keywords + 263 Phase 1 = ~400-460 total)
   - Prepare deployment steps:
     - Backup existing keywords file
     - Copy Phase 2a keywords to production location
     - Verify classifier loads without errors
   - **Output:** Deployment checklist, backup plan documented
   - **Verification:** File ready, deployment steps clear

2. **Staging & Testing (Day 8-9, 4 hrs)**
   - Deploy Phase 2a keywords to staging environment
   - Run on test dataset (706 remaining Unknown items from Phase 1)
   - Capture metrics:
     - Unknown items before: 706
     - Items now classified as Instrument: X
     - Items now classified as Software: Y
     - Items now classified as Non-Instrument: Z
     - Items remain Unknown: 706 - (X+Y+Z)
     - Reclassification rate: (X+Y+Z)/706 * 100%
   - **Output:** `deployment_results/phase2a_deployment_metrics.txt`
   - **Verification:** Metrics captured, no errors during classification

### Day 10: Validation & Decision Gate

**Responsible:** Data Analyst + Domain Expert + Implementation Lead

**Tasks:**

1. **Validation Run (Day 10, 3 hrs)**
   - Manual spot-check: Review 20-30 items reclassified by Phase 2a keywords
   - For each item, verify:
     - Reclassification is accurate (item is research equipment)
     - Keyword match makes sense (which keywords triggered classification?)
     - No false positives in Software category
   - Log any misclassifications for analysis
   - **Output:** Validation review document with sample items
   - **Verification:** Spot-check complete, accuracy assessed

2. **Decision Gate (Day 10, 1 hr)**
   - Review metrics:
     - **Target:** Unknown reduces from 706 to <400 (44%+ reduction)
     - **Minimum:** Unknown reduces from 706 to <500 (30%+ reduction)
     - **Validation:** Manual review shows >90% accuracy
   - **Criteria for GO (Phase 2b integration):**
     - Unknown reduction >30% AND manual accuracy >90% → **GO to Phase 2b**
     - Unknown reduction 20-30% OR accuracy 80-90% → **HOLD: Adjust keywords, retry**
     - Unknown reduction <20% OR accuracy <80% → **NO-GO: Pause, analyze why**
   - **Output:** Decision document with rationale
   - **Coordinator approval:** Kren Castro signs off on decision

### Week 3 Deliverables Checklist

- [ ] Deployment package prepared and verified
- [ ] Phase 2a keywords deployed to staging
- [ ] Metrics captured (Unknown reduction rate, reclassification counts)
- [ ] Manual validation done (20-30 items spot-checked, accuracy verified)
- [ ] Decision gate completed (GO/HOLD/NO-GO)
- [ ] Team sync: Announce Phase 2a results, confirm proceeding to Phase 2b

**Critical Decision Gate (End of Week 3):**
- Unknown reduction >30%? → YES/NO
- Validation accuracy >90%? → YES/NO
- **Decision:**
  - YES + YES → **GO: Proceed to Phase 2b integration (Week 4)**
  - YES + NO → **HOLD: Review accuracy, adjust Phase 2a keywords**
  - NO + ANY → **NO-GO: Analyze why keyword expansion underperformed, pause Phase 2b**

---

## PHASE 5: WEEK 4 — Phase 2b Integration & Final Testing

### Week 4 Goal
Integrate Phase 2b context rules with Phase 2a keywords, test unified solution, prepare for production deployment.

### Day 11-12: Integration Development

**Responsible:** Implementation Lead + Architecture Designer

**Tasks:**

1. **Rule A Implementation: Prior Context (Day 11, 3 hrs)**
   - Add context rule to classifier:
     - After Phase 2a keyword classification, loop through items
     - For items classified "Unknown", check prior item in quote
     - If prior is "Instrument" + current is vague → reclassify as "Instrument"
     - Log: "Reclassified via Prior Context rule"
   - **Code location:** `column_filter_and_classify_v3.py` (after line 92, after keyword classification)
   - **Verification:** Rule applies correctly, logging works, no crashes

2. **Rule B Implementation: Metadata Context (Day 11-12, 3 hrs)**
   - If supplier database available:
     - Extract supplier metadata (supplier type: "lab equipment", "scientific", etc.)
     - For Unknown items with supplier type match, boost Instrument probability
     - Log: "Reclassified via Metadata rule"
   - If supplier database NOT available:
     - Skip for Phase 2b, defer to Phase 3
     - Log: "Metadata rule skipped (database unavailable)"
   - **Code location:** `column_filter_and_classify_v3.py` (after Rule A)
   - **Verification:** Rule applies when available, graceful skip if unavailable

3. **Rule C Implementation: Bundle Analysis (Day 12, 2 hrs)**
   - Optional for Phase 2b (lower priority):
     - If bundle detected (multiple semicolon/comma-separated items):
       - Extract dominant item (first or longest description)
       - Classify based on dominant item keywords
     - Log: "Reclassified via Bundle Analysis rule"
   - If time/complexity high: Defer to Phase 3, skip for Phase 2b
   - **Code location:** `column_filter_and_classify_v3.py` (after Rule B)
   - **Verification:** Bundle detection works, edge cases handled

### Day 13-14: Integration Testing & Validation

**Responsible:** Data Analyst + Domain Expert

**Tasks:**

1. **End-to-End Testing (Day 13-14, 4 hrs)**
   - Run integrated Phase 2a + 2b classifier on remaining Unknown items (after Phase 2a)
   - Measure:
     - Unknown items before Phase 2b: 706 - (X+Y+Z) from Phase 2a
     - Items now classified via Rule A (Prior Context): P_a
     - Items now classified via Rule B (Metadata): P_b
     - Items now classified via Rule C (Bundle): P_c
     - Items remain Unknown after Phase 2b: Final_unknown
     - Final Unknown %, Instrument %, Software %, Non-Instrument %
   - Compare to target:
     - Target: Unknown <400 (44%+ total reduction), Instrument 25%+
   - Manual review: 30-50 context-rule-classified items for accuracy
   - **Output:** Phase 2b integration test results
   - **Verification:** Metrics captured, accuracy validated

2. **Final Quality Checks (Day 14, 2 hrs)**
   - Regression test: Verify Phase 1 keywords still work (no degradation)
   - Conflict check: Run conflict detection on Phase 1 + Phase 2a (must be zero)
   - Software category check: Verify no false positives (context rules didn't misclassify as Software)
   - Error handling: Test edge cases (missing metadata, ambiguous descriptions)
   - **Output:** Quality check report
   - **Verification:** No regressions, no new conflicts, error handling works

### Day 15: Final Decision & Deployment Readiness

**Responsible:** All roles, Coordinator approval

**Tasks:**

1. **Final Metrics Review (Day 15, 1 hr)**
   - Unknown items: 706 → ? (target: <400)
   - Instrument %: ? (target: 25%+)
   - Validation accuracy: ?% (target: >90%)
   - Compare to Phase 2 spec success criteria (all must-haves)
   - **Output:** Final metrics summary
   - **Verification:** All metrics documented

2. **Production Readiness Decision (Day 15, 1 hr)**
   - **Go/No-Go criteria:**
     - Unknown <400 (44%+ reduction) AND Instrument 25%+ AND Accuracy >90% → **GO**
     - Unknown 400-450 AND Instrument 23-25% AND Accuracy 85-90% → **GO with monitoring**
     - Unknown >450 OR Instrument <23% OR Accuracy <85% → **NO-GO: Continue Phase 2 refinement**
   - Document decision rationale
   - **Coordinator approval:** Kren Castro signs off
   - **Output:** Production readiness assessment

### Week 4 Deliverables Checklist

- [ ] Phase 2b context rules integrated (Rule A, B, C or subset)
- [ ] End-to-end testing complete (Phase 2a + 2b combined)
- [ ] Final metrics captured (Unknown %, Instrument %, accuracy)
- [ ] Manual validation done (30-50 items spot-checked)
- [ ] Regression tests passed (Phase 1 keywords still work)
- [ ] Quality checks passed (no conflicts, no Software false positives)
- [ ] Production readiness decision made (GO/NO-GO)
- [ ] Team sync: Announce final results, decide deployment timing

**Final Decision Gate (End of Week 4):**
- Unknown <400? → YES/NO
- Instrument 25%+? → YES/NO
- Accuracy >90%? → YES/NO
- **If YES to all:** Ready for production deployment (see Phase 6)
- **If mixed:** GO with monitoring (deploy Phase 2a+2b, watch for issues)
- **If NO to multiple:** Continue refinement, don't deploy yet

---

## PHASE 6: PRODUCTION DEPLOYMENT & MONITORING

### Deployment Window (End of Week 4 / Start of Week 5)

**Responsible:** Implementation Lead + Coordinator

**Tasks:**

1. **Production Deployment (2 hrs)**
   - Backup existing classifier configuration
   - Deploy Phase 2a + 2b keywords and context rules to production
   - Update `column_filter_and_classify_v3.py` with integrated rules
   - Verify no syntax errors (run import test)
   - Set up monitoring: log all classifications for first week
   - **Verification:** Deployment successful, no errors

2. **Monitoring Setup (1 hr)**
   - Daily metric tracking: Unknown %, Instrument %, classification accuracy
   - Alert thresholds:
     - Unknown % increases >2% → investigate
     - Software misclassifications detected → investigate
     - Context rules applied to X items → log for analysis
   - Duration: 1 week daily, then weekly checks
   - **Output:** Monitoring dashboard or log file

3. **Rollback Plan (1 hr)**
   - If production issues detected:
     - Immediate rollback: Revert to Phase 1 keywords (simple swap)
     - Analysis: Identify which rules caused issues
     - Remediation: Adjust rules, redeploy
   - Rollback is simple (keyword file swap), estimated 30 mins to execute

### Post-Deployment Monitoring (Week 5-6)

**Responsible:** Data Analyst + Implementation Lead

**Tasks:**

1. **Daily Reviews (Week 5)**
   - Track: Unknown %, Instrument %, context rule application rates
   - Flag: Any categories with unexpected distributions
   - Review: Sample of context-rule-classified items for accuracy
   - Action: If issues, escalate to Coordinator for decision

2. **Weekly Review (Week 6)**
   - Summary: How did Phase 2a + 2b perform against target metrics?
   - Issues: Any false positives, edge cases, data quality issues?
   - Recommendations: Fine-tune thresholds? Disable problematic rules?
   - Phase 3 planning: What remains Unknown? Next steps?
   - **Output:** Phase 2 deployment report

---

## TEAM COORDINATION & SYNC SCHEDULE

### Weekly Sync Meetings

| Week | Day | Duration | Attendees | Topics |
|---|---|---|---|---|
| 1 | Friday | 1 hr | All | Week 1 findings (patterns, keywords), adjust scope |
| 2 | Friday | 1 hr | All | Conflict resolution results, test metrics, go/no-go Phase 2a |
| 3 | Friday | 1 hr | All | Phase 2a deployment metrics, decision on Phase 2b |
| 4 | Friday | 1 hr | All | Phase 2b integration results, final deployment decision |
| 5-6 | Monday | 30 min | Leads | Monitoring review, issues, Phase 3 planning |

### Async Communication

- **Slack/Email:** Daily updates from track leads (15 min summary)
- **Decision gates:** Formal approval from Coordinator (Kren Castro) required before phase transitions
- **Escalation:** If blockers, contact Coordinator immediately (don't wait for sync)

---

## TASK ASSIGNMENTS SUMMARY

### Track 1: Keyword Analysis (Weeks 1-2)
- **Data Analyst:** Week 1 pattern segmentation, keyword extraction; Week 2 sample testing, deployment prep
- **Domain Expert (Research):** Week 1 category validation; Week 2 conflict resolution review
- **Implementation Lead:** Week 2 conflict validation, deployment readiness

### Track 2: Context Analysis (Weeks 1-4 concurrent)
- **Architecture Designer:** Vague pattern analysis, rule design, integration spec, implementation roadmap
- **Data Analyst:** Vague item analysis, context clue identification
- **Domain Expert (Research):** Rule validation, safety guardrails review

### Phase 2a Deployment (Week 3)
- **Implementation Lead:** Deployment preparation, staging test, decision gate documentation
- **Data Analyst:** Validation run, spot-checking accuracy
- **Domain Expert:** Accuracy review of reclassified items

### Phase 2b Integration (Week 4)
- **Implementation Lead:** Rule A & B implementation, integration testing
- **Architecture Designer:** Rule C implementation (if included), code review
- **Data Analyst:** End-to-end testing, final validation
- **Coordinator:** Final decision, production approval

---

## SUCCESS CRITERIA & METRICS

### Must-Have (Deployment Gate)
- ✓ Unknown items reduced from 706 to <400 (44%+ reduction)
- ✓ Instrument classification ≥25% of total dataset
- ✓ Zero new keyword conflicts
- ✓ Context rules validated safe (no false positives)

### Nice-to-Have
- Unknown <350 (50%+ reduction)
- Instrument ≥28%
- Context rules improve reduction by additional 50+ items
- Team documents learnings for Phase 3

### Tracking
- **Baseline (end of Phase 1):** 1,134 Unknown (19.8%), 840 Instrument (14.7%)
- **Phase 2 target:** 706 Unknown (remaining), <400 Unknown after Phase 2, 25%+ Instrument
- **Final goal:** Unknown <400 (<15% of total), Instrument 25%+

---

## RISK MITIGATION & CONTINGENCIES

| Risk | Likelihood | Mitigation |
|---|---|---|
| Phase 2a keywords too broad (false positives) | Medium | Domain expert validation, multi-word keywords preferred, conflict checks |
| Context rules cause misclassification | Medium | MVP approach (safe rules only), extensive testing, gradual rollout |
| Phase 2a doesn't reduce Unknown enough (<30%) | Low | Analyze why, adjust keywords, retry before Phase 2b |
| Integration complexity delays Phase 2b | Low | Early design work (Weeks 1-2), implementation roadmap clear |
| Production deployment issues | Low | Rollback plan (revert to Phase 1 keywords), monitoring in place |
| Team capacity / schedule slips | Medium | Weekly syncs to identify blockers early, adjust scope if needed |

---

## Document Control & Next Steps

### Created By
Claude Code (AI Planning Agent)

### Review & Approval
- [ ] Kren Castro (Coordinator) reviews plan
- [ ] Data Analyst confirms Week 1-2 tasks
- [ ] Domain Expert (Research Equipment) confirms keyword scope
- [ ] Architecture Designer confirms Phase 2b design approach

### Execution Start
Once approved, Week 1 tasks begin immediately:
1. Data Analyst extracts Unknown items dataset
2. Domain Expert and Data Analyst segment patterns
3. Keyword candidate extraction begins (Days 3-4)

---

## Appendix: File Locations & Naming Conventions

### Deliverable Locations
- **Final Keyword File:** `docs/guides/documents/research_equipment_keywords_phase2a.txt` (deployed)
- **Classifier Code:** `src/services/data-cleaning/column_filter_and_classify_v3.py` (updated)
- **Phase 2b Spec:** `planning/phase2b_context_analysis_specification.md` (generated from scratchpad)
- **Deployment Report:** `planning/phase2_deployment_results.md` (final)

### Scratchpad Working Files (Week 1-4)
- `phase2_unknown_items_706.csv` - Unknown items dataset
- `phase2_pattern_segments.txt` - Pattern segmentation results
- `phase2_keyword_candidates_ranked.txt` - Extracted keywords with frequencies
- `phase2_keywords_organized.txt` - Organized by category
- `phase2_conflicts_identified.txt` - Conflict detection report
- `phase2_keywords_final_clean.txt` - Clean, conflict-free keywords
- `phase2a_sample_test_results.txt` - Sample validation results
- `phase2b_vague_patterns.txt` - Vague item pattern analysis
- `phase2b_context_rules_design.txt` - Rule specifications
- `phase2b_safety_validation.txt` - Safety checklist
- `phase2b_integration_spec.txt` - Integration specification
- `phase2b_implementation_roadmap.txt` - Phase 2b task breakdown
- `deployment_results/phase2a_deployment_metrics.txt` - Deployment results
- `phase2b_integration_test_results.txt` - Final testing results

### Naming Conventions
- Research equipment keywords (Phase 2a): `research_equipment_keywords_phase2a.txt`
- Context rules: Inline comments in classifier code (`# PHASE 2B: Rule A/B/C`)
- Test/validation data: Scratchpad CSVs with `phase2_` prefix
- Reports: Markdown files in planning/ with `phase2_` prefix

---

**Plan Status:** Ready for Execution  
**Last Updated:** 2026-06-23  
**Version:** 1.0
