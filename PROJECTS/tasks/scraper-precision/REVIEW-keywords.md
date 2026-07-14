# REVIEW-keywords.md

Terms that don't fit confidently into junk/keep buckets. Domain judgment required.

## Software Keywords (ambiguous)

### Brand names that are or include scientific software
| Term | Current | Issue | Recommendation |
|------|---------|-------|-----------------|
| `adobe` | in Software | Brand that makes creative/office software; not research-specific | REMOVE? (it's CAD/design, not lab software) |
| `autocad` | in Software | CAD tool; is this ever lab software? Could be for mechanical design | REMOVE? (not research science) |
| `prism` | REMOVED from Software | Both a brand (GraphPad Prism) AND a generic optical term | **RESOLVED 2026-07-13 — REMOVE is correct.** Checked the real data: `prism` appears 14x and every one is an OPTICAL prism (VERTICAL PRISM BAR, DIC PRISM FOR WI-SRE3). `graphpad` appears 0x. Do not restore it. |
| `visio` | in Software | Diagram/flowchart tool; used in lab reporting? | REMOVE? (office tool, not lab software) |
| `revit` | in Software | CAD/BIM tool; unlikely in research requisitions | REMOVE (architecture/engineering, not research) |
| `salesforce` | in Software | CRM platform; not research software | REMOVE? (enterprise sales, not science) |
| `intel` | in Software | Processor brand; never appears as purchased software | Review if in Software at all |

### Abbreviations/acronyms that might be valid
| Term | Current | Issue | Recommendation |
|------|---------|-------|-----------------|
| `gmpe` | removed (fragment) | No clear meaning; not in standard ML/bio domains | CONFIRM: junk? |
| `pmml` | if present | Predictive Model Markup Language - is this ever purchased as software? | Review if present |

## Non-Instrument Keywords (ambiguous)

### Brand names for products that are often *components* not standalone instruments
| Term | Current | Issue | Recommendation |
|------|---------|-------|-----------------|
| `axon` | in Non-Instrument | Molecular Devices electrophysiology amplifiers/controllers | KEEP (per plan: deliberate non-instrument category) |
| `barco` | in Non-Instrument | Projection/display company; displays are not instruments | Review: KEEP? REMOVE? |
| `cisco` | in Non-Instrument | Network equipment company; networking hardware not science equipment | REMOVE? (but might appear in lab infrastructure) |
| `sony` | in Non-Instrument | Electronics brand; cameras/displays are components not instruments | Review: specific context? |
| `zebra` | in Non-Instrument | Barcode/label printer brand; not science equipment | REMOVE? |
| `nomad` | in Non-Instrument | ? Unknown what this refers to in context | Review: what product is this? |
| `joel` | in Non-Instrument | Proper name or brand? Very ambiguous | REMOVE? (likely person's name in quoted text) |
| `jess` | in Non-Instrument | Proper name or brand? Very ambiguous | REMOVE? (likely person's name in quoted text) |
| `york` | in Non-Instrument | City name OR brand? Appears in our data as what? | Review: context needed |
| `rice` | in Non-Instrument | Food item or brand name? Very ambiguous | Review: appears in data how? |

### Short terms that might be real but are borderline
| Term | Current | Issue | Recommendation |
|------|---------|-------|-----------------|
| `barco` | kept | Display projection; is this ever lab equipment? | Review: keep or remove? |
| `noise` | kept | Generic but could indicate acoustic shielding products | KEEP (real use in labs) |
| `pitch` | kept | Could be tilt adjustment or generic | KEEP (real use) |

## Unsure Which List

### Terms that appear in multiple contexts
| Term | Currently | Issue | Recommendation |
|------|-----------|-------|-----------------|
| `server` | in Software (before cleanup) | Could be: enterprise IT server (SW), or lab file/analysis server (SW), or server components (NI) | Review: which is dominant in our data? |
| `system` | likely in both | Extremely generic; appears in equipment requisitions as "lab system" or "instrument system" | Review: any in software list? |

## Summary

- **Clear removals**: 11 terms (per plan rules S1-S2 and N1-N2 above)
- **Ambiguous brands**: 10 terms needing judgment (mostly vendor names)
- **Abbreviations**: 2 terms needing verification
- **Context-dependent**: 3 terms needing to understand the data

**Total**: 26 terms flagged for review (within 20-40 range per plan)
