# Phase 2 Classifier Improvement Plan: Research Equipment + Hybrid Context

**Document:** Phase 2 Planning Specification  
**Date:** 2026-06-23  
**Status:** Design Ready for Review  
**Team Lead:** Kren Castro  
**Duration:** 4 weeks (Weeks 1-4, concurrent tracks)

---

## Executive Summary

Phase 2 builds on Phase 1's 37.7% Unknown reduction by implementing a **hybrid approach**: keyword expansion focused on research equipment + context-aware classification rules for vague descriptions.

**Goal:** Reduce remaining 706 Unknown items by 44%+ (to <400) and increase Instrument classification to 25%+ of total dataset.

**Approach:** Two parallel tracks executing concurrently:
- **Track 1 (Weeks 1-2):** Research equipment keyword analysis → Phase 2a deployment
- **Track 2 (Weeks 1-4):** Context analysis design → Phase 2b integration

**Success Criteria:**
- Unknown items: 706 → <400 (44%+ reduction)
- Instrument classification: 20% → 25%+
- Zero new keyword conflicts
- Context rules validated safe for production

---

## Background: Why Phase 2?

After Phase 1 deployed 44 keywords (expanding Instrument + Software coverage), **706 items (62.3%)** remain Unknown. Analysis shows:

| Category | Count | Issue |
|---|---|---|
| Vague descriptions | ~200 items | "Equipment", "system", "unit" without specifics |
| No descriptive text | ~140 items | Quote numbers only, no product description |
| Proprietary equipment | ~150 items | Brand-specific models not yet in keywords |
| Service-only items | ~85 items | Labor/installation without product context |
| Mixed/bundle items | ~131 items | Multiple unrelated items, unclear categorization |

**Phase 2 addresses:** Vague descriptions (via context rules) + Proprietary equipment (via research-focused keywords)

---

## Phase 2a: Keyword Analysis Track (Weeks 1-2)

### Objective
Extract 150-200 **research equipment keywords** from the 706 remaining Unknown items. Focus: lab equipment, analytical instruments, measurement/testing devices (NOT medical equipment from Phase 1).

### Team Roles & Responsibilities

| Role | Responsibilities | Deliverables |
|---|---|---|
| **Data Analyst** | Pattern discovery in Unknown items; keyword candidate extraction; frequency analysis | Keyword candidate list with frequencies |
| **Domain Expert (Research Equipment)** | Validate keywords are research-focused; prevent medical equipment drift; ensure category accuracy | Approved keyword list; conflict notes |
| **Implementation Lead** | Conflict detection with Phase 1 keywords; threshold verification; sample testing | Conflict resolution report; test results |

### Process: 4-Phase Execution

**Phase 2a.1 - Pattern Segmentation (Days 1-2)**
1. Group 706 Unknown items by text pattern
2. Identify research equipment categories:
   - Lab equipment (centrifuges, chromatography, spectroscopy)
   - Analytical instruments (mass spec, NMR, HPLC components)
   - Measurement/testing devices (scales, gauges, sensors, probes)
   - Data collection systems (software-adjacent hardware)
   - Calibration/reference standards
3. Exclude medical equipment (covered in Phase 1)
4. Output: Segmented Unknown items by category

**Phase 2a.2 - Keyword Extraction (Days 3-4)**
1. For each category, extract keyword candidates
2. Prioritize by frequency in Unknown items
3. Create research equipment keyword list (target: 150-200 keywords)
4. Organize by subcategory (e.g., lab equipment → centrifuge, rotary evaporator, spectrometer)
5. Output: Ranked candidate keyword list

**Phase 2a.3 - Conflict Resolution (Days 5-6)**
1. Compare against existing Phase 1 keywords
2. Check for overlap with Software keywords (e.g., "system" too broad?)
3. Verify no conflicts between Instrument, Software, Non-Instrument categories
4. Validate single vs. multi-word keywords (prefer multi-word for precision)
5. Output: Conflict-free Phase 2a keyword list

**Phase 2a.4 - Sample Validation (Day 7)**
1. Test keywords on 50-100 Unknown items
2. Measure: How many items → Instrument classification?
3. Manual review: Are classifications accurate?
4. Decision gate: Proceed to Phase 2b integration if Unknown reduction is significant
5. Output: Validation report + sample test results

### Deliverables

1. **`research_equipment_keywords_phase2a.txt`**
   - 150-200 keywords organized by research equipment category
   - One keyword per line, sorted by frequency
   - Comments noting source pattern/frequency

2. **Conflict Resolution Report**
   - List of potential conflicts identified + resolution
   - Keywords unique to Phase 2a (not in Phase 1)
   - Cross-category validation results

3. **Sample Validation Results**
   - Test dataset: 50-100 Unknown items
   - Unknown items → Instrument reclassifications (count & samples)
   - Accuracy assessment (manual review notes)
   - Decision: Ready for Phase 2b? (Yes/No with reasoning)

### Success Metrics (Phase 2a)
- 150-200 research equipment keywords extracted
- Zero conflicts with Phase 1 keywords
- Sample shows 30%+ of test Unknown items → Instrument classification
- All keywords verified as research equipment focus (no medical drift)

---

## Phase 2b: Context Analysis Design Track (Weeks 1-4 concurrent)

### Objective
Design and specify **context-aware classification rules** that layer on top of keywords to classify vague/generic Unknown items using metadata, quote context, and item relationships.

### Team Roles & Responsibilities

| Role | Responsibilities | Deliverables |
|---|---|---|
| **Architecture Designer** | Define context rules, data flow, integration with keyword system | Context specification document; rule trees |
| **Data Analyst** | Identify metadata patterns, analyze relationships between items in quotes | Data extraction patterns; quote analysis results |
| **Domain Expert (Research Equipment)** | Validate rule logic; ensure context makes sense for research equipment | Rule validation notes; risk assessment |

### Process: 4-Phase Execution

**Phase 2b.1 - Vague Item Analysis (Days 1-3)**
1. Identify Unknown items with vague descriptions ("equipment", "system", "unit", "assembly")
2. For each vague item, examine:
   - Prior items in same quote (what was classified?)
   - Quote metadata (supplier type, purchase category)
   - Item position (first item? middle? bundle?)
   - Related items (siblings with more specific names?)
3. Identify patterns: What context clues predict category?
4. Output: Vague item patterns + context clues

**Phase 2b.2 - Context Rule Design (Days 4-6)**
1. Design three types of context rules:
   - **Prior Context Rule:** If prior item is Instrument + current is vague, boost Instrument probability
   - **Metadata Rule:** If quote supplier is "Lab Equipment Distributor", apply research equipment defaults
   - **Bundle Analysis Rule:** For bundle items, extract the dominant/specific item, classify accordingly
2. Define decision logic for each rule:
   - When to apply?
   - Confidence levels?
   - Fallback behavior?
3. Document with decision trees and pseudocode
4. Output: Context rule specifications with logic diagrams

**Phase 2b.3 - MVP Safety Validation (Days 7-9)**
1. Design "Minimal Viable Product" context rules (safe, proven, low-risk)
2. Exclude experimental/risky heuristics
3. Define guardrails:
   - No false-positive risk to Software category
   - Clear fallback if context clues are ambiguous
   - Disable rule if confidence drops below threshold
4. Create safety checklist for integration
5. Output: MVP context rules specification; safety validation report

**Phase 2b.4 - Integration Specification (Day 10)**
1. Define how context rules integrate with Phase 2a keywords:
   - Rule execution order?
   - Confidence combination logic?
   - Threshold adjustments needed?
2. Specify data inputs & outputs
3. Design monitoring/audit logs (track rule application)
4. Create implementation roadmap for Phase 2b.5 (integration)
5. Output: Integration specification document

### Deliverables

1. **Context Analysis Specification Document**
   - Vague item pattern analysis (types, frequencies)
   - Context rule definitions (3 rule types with logic)
   - Decision trees for each rule
   - Safety guardrails & fallback behavior

2. **Rule Validation & Integration Plan**
   - MVP context rules (safe subset ready for Phase 2b integration)
   - Confidence thresholds for each rule
   - Integration points with Phase 2a keywords
   - Testing plan for Phase 2b (Week 4)

3. **Monitoring & Audit Design**
   - Logging strategy (track rule application)
   - Audit trails (which rule classified which items?)
   - Performance metrics (rule accuracy, false-positive rate)

### Success Metrics (Phase 2b)
- 3 context rule types fully specified with decision logic
- MVP rules validated safe (no false-positive risk)
- Integration plan clear & feasible
- Ready for Phase 2b.5 implementation (Week 4)

---

## Integration & Deployment (Weeks 3-4)

### Week 3: Phase 2a Keywords Deployment

**Goals:**
1. Deploy research equipment keywords from Track 1
2. Measure impact on remaining Unknown items
3. Validate no conflicts
4. Decision gate: Proceed to Phase 2b integration?

**Steps:**
1. Update classifier with `research_equipment_keywords_phase2a.txt`
2. Set thresholds to (1, 1, 1) for consistency with Phase 1
3. Run on 706 remaining Unknown items
4. Measure:
   - How many items now classified as Instrument?
   - How many remain Unknown?
   - Any conflicts detected?
5. Manual spot-check: 20-30 reclassified items for accuracy
6. **Decision gate:** If Unknown → <400, proceed to Phase 2b integration. If not, analyze why before adding context.

**Deliverables:**
- Phase 2a deployment report (metrics, validation results)
- Decision: Proceed to Phase 2b? (Yes/No)

### Week 4: Phase 2b Integration & Testing

**Goals:**
1. Integrate Phase 2b context rules with Phase 2a keywords
2. Test unified solution
3. Validate final Unknown % and Instrument %
4. Prepare for production deployment

**Steps:**
1. Integrate context rules into classifier
2. Run on full Unknown dataset (remaining items after Phase 2a)
3. Measure:
   - Unknown % after context rules applied
   - Instrument % increase
   - Software & Non-Instrument accuracy (false-positive check)
4. Manual validation: 30-50 context-rule-classified items
5. Monitor for edge cases (ambiguous contexts, incorrect inferences)
6. **Final decision:** Ready for production? (Yes/No)

**Deliverables:**
- Phase 2b integration report
- Final metrics (Unknown %, Instrument %, accuracy)
- Production readiness assessment

### Production Deployment (End of Week 4)

**Deployment Plan:**
1. Deploy Phase 2a + 2b unified solution to production classifier
2. Set up monitoring: Daily Unknown % tracking for 1 week
3. Establish rollback plan (revert to Phase 1 if issues arise)
4. Document configuration (keywords + context rules)

**Monitoring (Week 5-6):**
- Track Unknown % daily
- Log any misclassifications
- Monitor Software category for false positives
- Weekly review: Any issues? Adjust thresholds if needed

---

## Team Structure & Timeline

### Team Composition

| Track | Team Members | FTE Allocation |
|---|---|---|
| **Track 1: Keywords** | Data Analyst + Domain Expert (Research) + Impl Lead | 2 weeks, ~10 hrs/week each |
| **Track 2: Context** | Architecture Designer + Data Analyst + Domain Expert (Research) | 4 weeks, ~10 hrs/week each (concurrent) |
| **Coordinator** | Kren Castro | Oversight, decision gates, async communication |

### Weekly Timeline

| Week | Track 1 | Track 2 | Milestones |
|---|---|---|---|
| **Week 1** | Pattern segmentation + keyword extraction | Vague item analysis + rule design | Track 1 midpoint check |
| **Week 2** | Conflict resolution + sample validation | MVP validation + integration spec | Track 1 complete; Track 2 MVP done |
| **Week 3** | Phase 2a deployment (async) | Integration testing prep | Decision gate: proceed to 2b? |
| **Week 4** | Monitor + support 2b integration | Phase 2b integration + final testing | Production deployment decision |

---

## Success Criteria

### Must-Have (Deployment Gate)
- ✅ Unknown items reduced from 706 to <400 (44%+ reduction)
- ✅ Instrument classification at 25%+ of total dataset
- ✅ Zero new keyword conflicts
- ✅ Context rules validated safe (no false positives in Software/Non-Instrument)
- ✅ Rollback plan documented

### Nice-to-Have (Optimization)
- Unknown <350 (50%+ reduction)
- Instrument at 28%+
- Context rules improve Unknown reduction by additional 50+ items
- Team documents learnings for Phase 3

### Measurements
- **Baseline:** 706 Unknown items (62.3% of remaining), 20% Instrument
- **Target:** <400 Unknown (44%+ reduction), 25% Instrument
- **Nice-to-Have:** <350 Unknown (50%+ reduction), 28% Instrument

---

## Technical Implementation Notes

### Classifier Files to Update
- `src/services/data-cleaning/column_filter_and_classify_v3.py`
- `docs/guides/documents/research_instrument_keywords.txt`
- `docs/guides/documents/software_keywords.txt`
- `docs/guides/documents/non_instrument_keywords.txt`

### Configuration Changes
- Keyword files: Add Phase 2a research equipment keywords
- Thresholds: Maintain (1, 1, 1) from Phase 1
- Context rules: New classification logic (TBD in Phase 2b spec)

### Testing Strategy
- Unit tests: Keyword loading & conflict detection
- Integration tests: End-to-end classification on 100+ Unknown items
- Regression tests: Verify Phase 1 keywords still work
- Manual validation: Domain expert review of 30-50 reclassified items

---

## Risk Mitigation

| Risk | Mitigation |
|---|---|
| **Keywords too broad (false positives)** | Domain expert validation; multi-word keywords preferred |
| **Context rules cause misclassification** | MVP approach (safe rules only); extensive testing before deploy |
| **Integration complexity delays Phase 2b** | Weekly sync meetings; early integration testing in Week 3 |
| **Phase 2a doesn't reduce Unknown enough** | Decision gate: analyze why before adding context rules |
| **Production deployment issues** | Rollback plan prepared; monitoring in place; async communication |

---

## Next Steps

### Immediate (Before Phase 2 Starts)
1. ✅ Get team approval on this spec
2. ✅ Assign team members to Track 1 & Track 2
3. ✅ Schedule weekly sync meetings
4. ✅ Prepare Unknown item data for analysis

### Week 1
- Track 1: Start pattern segmentation
- Track 2: Start vague item analysis
- Coordinator: Weekly check-in with both tracks

### Decision Gates
- **End of Week 2:** Track 1 complete; Track 2 MVP done. Ready for Week 3 deployment?
- **End of Week 3:** Phase 2a deployed. Unknown reduction measured. Proceed to Phase 2b integration?
- **End of Week 4:** Phase 2b testing complete. Ready for production deployment?

---

## Document Control

| Version | Date | Author | Status |
|---|---|---|---|
| 1.0 | 2026-06-23 | Claude Code | Draft for Review |

---

## Questions & Contact

**Questions about Phase 2 plan?**
- Scope or timeline questions → Kren Castro
- Technical implementation details → TBD (track leads)
- Team coordination → Weekly sync meetings

**Ready to proceed?** Review and confirm approval before Phase 2 starts.
