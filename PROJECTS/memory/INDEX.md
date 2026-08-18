# Crawler Project Memory - Index

Welcome to your project-specific memory system. This two-tier system helps Claude understand your Crawler project's context, terminology, and development priorities.

---

## Quick Navigation

### 🔥 Hot Cache (Start Here)
**File**: `../CLAUDE.md`
- 📊 Core modules overview
- 🎯 Active issues & priorities
- 🔧 Key files & their status
- 📈 Performance metrics
- ⚙️ Configuration quick reference

### 📚 Full Glossary
**File**: `glossary.md`
- 📖 Complete decoder ring (all acronyms, terms, terminology)
- 🏗️ Organizational language
- 📊 Status indicators & meanings
- 🔧 Configuration parameters
- 📈 Performance baselines

---

## Module Deep Dives

### CLASSIFY Module (Phase 1 - ACTIVE)
**File**: `modules/classify.md`
- What it does (document classification system)
- Core components breakdown
- Component purposes & responsibilities
- Current issues (redundancy, testing, performance)
- Development roadmap (6 weeks, 4 phases)
- File locations & responsibilities
- Configuration details
- Running instructions

### CROSS-REFERENCE Module (Phase 2 - PENDING)
**File**: `modules/cross-reference.md`
- Overview & status
- Core components
- Workflow (input → output)
- Known issues
- Action items
- Running instructions

### SCRAPER_FULL Module (Phase 3 - PENDING)
**File**: `modules/scraper.md`
- Overview & status
- Core components
- Key features
- Performance baseline
- Phase 3 action items
- Running instructions

---

## Project Context

### Development Roadmap
**File**: `context/development-phases.md`
- Multi-phase development plan (4 phases, ~17 weeks)
- **Phase 1**: CLASSIFY (6 weeks, IN PROGRESS)
  - 1a: Code consolidation & deduplication
  - 1b: Testing & stability
  - 1c: Performance optimization
  - 1d: Maintainability improvements
- **Phase 2**: CROSS-REFERENCE (4-5 weeks)
- **Phase 3**: SCRAPER_FULL (4 weeks)
- **Phase 4**: Consolidation & Integration (2-3 weeks)
- Success criteria for each phase
- Timeline & blockers

### Project Structure
**File**: `context/project-structure.md`
- Complete directory tree
- Configuration file locations & content
- Dependencies & requirements
- Git & version control info
- Development environment setup
- File size overview
- Environment variable TODO list

---

## Tier System

### CLAUDE.md (Hot Cache - ~100 lines)
Covers ~90% of daily decoding needs:
- Top ~30 people/concepts (none in this project)
- ~30 most common terms (HW, SW, NI, etc.)
- Active projects (CLASSIFY, phases)
- Configuration quick reference
- Active issues
- Running commands

### memory/ (Deep Storage)
Full, unlimited-scale context:
- `glossary.md` - Everything (all acronyms, terms, details)
- `modules/` - Rich documentation for each module
- `context/` - Project-wide context (structure, phases, environment)

---

## How Claude Uses This Memory

### Decoding Shorthand
**User**: "Update CLASSIFY consolidation status"
**Claude Lookup Flow**:
1. CLAUDE.md → "CLASSIFY" = Module 1, in consolidation
2. memory/modules/classify.md → Full details on what consolidation means
3. memory/context/development-phases.md → Current action items

### Finding Information
**User**: "What does HW mean?"
**Claude Lookup**:
1. CLAUDE.md → HW = Hardware (quick answer)
2. memory/glossary.md → Full definition with examples

### Executing Tasks
**User**: "Run the classification monitor"
**Claude**: 
- CLAUDE.md → Running commands section
- memory/modules/classify.md → Detailed setup & troubleshooting

---

## File Locations Quick Reference

| File | Purpose | Size |
|------|---------|------|
| `../CLAUDE.md` | Hot cache (working memory) | ~3KB |
| `glossary.md` | Full glossary & decoder ring | ~8KB |
| `modules/classify.md` | CLASSIFY module deep dive | ~12KB |
| `modules/cross-reference.md` | CROSS-REF module overview | ~2KB |
| `modules/scraper.md` | SCRAPER module overview | ~2KB |
| `context/development-phases.md` | Multi-phase roadmap | ~10KB |
| `context/project-structure.md` | Directory & environment info | ~8KB |
| `INDEX.md` | This file (navigation guide) | ~4KB |

**Total Memory Size**: ~50KB (lightweight, fast to scan)

---

## Lookup Strategy

When you need information:

1. **Quick answer?** → Check `CLAUDE.md` (hot cache)
2. **Detailed definition?** → Check `glossary.md` (full glossary)
3. **Module deep dive?** → Check `modules/{name}.md`
4. **Development plan?** → Check `context/development-phases.md`
5. **File locations?** → Check `context/project-structure.md`
6. **Stuck?** → This file (INDEX.md)

---

## Memory Maintenance

### When to Update
- New modules added
- Terminology changes
- Development phases progress
- Configuration changes
- New issues identified

### What to Keep Fresh
- `CLAUDE.md` - Always current (hot cache)
- `context/development-phases.md` - Update as phases complete
- `glossary.md` - Add new terms as discovered
- Module files - Update when code changes significantly

### What's Permanent
- This index (structure rarely changes)
- project-structure.md (structure is stable)

---

## System Principles

✅ **CLAUDE.md** stays ~100 lines (the "hot 30" rule)
✅ **memory/** grows with unlimited detail
✅ Frequently-used terms promoted to CLAUDE.md
✅ Stale/historical info moved to memory/ only
✅ Full glossary always contains complete decoder ring
✅ No duplication between files (one source of truth)

---

## Author & Version

**Project**: PDF Crawler & Classification System
**Author**: Kren Castro (castrokren@gmail.com)
**Memory System**: Created May 14, 2026
**Next Review**: After Phase 1 completion (estimated June 2026)

---

## Questions?

If Claude doesn't understand a term or shorthand:
1. Check CLAUDE.md (hot cache)
2. Check glossary.md (full glossary)
3. Ask the user to add it to memory

This system grows with your project!
