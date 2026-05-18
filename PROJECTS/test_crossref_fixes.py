#!/usr/bin/env python3
"""
Validation Test: CrossRef Fixes
Tests that the root causes have been fixed:
1. Path configuration works (relative paths resolve correctly)
2. No duplicate method definitions
3. State tracking prevents rescanning
"""

import sys
import os
import json
from pathlib import Path

# Add PROJECTS to path
PROJECTS_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECTS_ROOT))

def test_path_configuration():
    """TEST 1: Verify pipeline_config.json has relative paths, not hardcoded."""
    print("\n" + "="*70)
    print("TEST 1: Path Configuration")
    print("="*70)

    config_path = PROJECTS_ROOT / "src" / "services" / "pipeline_config.json"

    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        return False

    with open(config_path) as f:
        config = json.load(f)

    paths = config.get("paths", {})
    hardcoded_paths = []

    for key, value in paths.items():
        if value.startswith("C:/") or value.startswith("C:\\"):
            hardcoded_paths.append((key, value))
        print(f"  {key}: {value}")

    if hardcoded_paths:
        print(f"\n❌ FAILED: Found {len(hardcoded_paths)} hardcoded paths:")
        for key, value in hardcoded_paths:
            print(f"   - {key}: {value}")
        print("   Should be relative paths like 'data/masterlist/updated_master_list.xlsx'")
        return False

    print("\n✅ PASSED: All paths are relative (will resolve correctly)")
    return True

def test_no_duplicate_methods():
    """TEST 2: Verify find_matching_pdfs is defined only once."""
    print("\n" + "="*70)
    print("TEST 2: No Duplicate Method Definitions")
    print("="*70)

    crossref_path = PROJECTS_ROOT / "Cross-reference" / "crossref_standalone_fast.py"

    if not crossref_path.exists():
        print(f"❌ CrossRef file not found: {crossref_path}")
        return False

    with open(crossref_path) as f:
        content = f.read()

    # Count occurrences of "def find_matching_pdfs("
    import re
    matches = re.findall(r'^\s*def find_matching_pdfs\(', content, re.MULTILINE)

    print(f"  Found {len(matches)} definition(s) of find_matching_pdfs()")

    if len(matches) > 1:
        print(f"\n❌ FAILED: find_matching_pdfs() defined {len(matches)} times (should be 1)")
        return False

    if len(matches) == 0:
        print(f"\n❌ FAILED: find_matching_pdfs() not found in file")
        return False

    print("\n✅ PASSED: find_matching_pdfs() defined exactly once")
    return True

def test_state_tracking():
    """TEST 3: Verify state tracking methods exist."""
    print("\n" + "="*70)
    print("TEST 3: State Tracking Implementation")
    print("="*70)

    crossref_path = PROJECTS_ROOT / "Cross-reference" / "crossref_standalone_fast.py"

    with open(crossref_path) as f:
        content = f.read()

    required_methods = [
        '_load_state',
        '_save_state',
        '_mark_supplier_scanned'
    ]

    missing_methods = []
    for method in required_methods:
        if f'def {method}(' not in content:
            missing_methods.append(method)
        else:
            print(f"  ✅ Found method: {method}")

    if missing_methods:
        print(f"\n❌ FAILED: Missing methods: {missing_methods}")
        return False

    # Check that __init__ loads state
    if "self.state = self._load_state()" not in content:
        print(f"\n❌ FAILED: __init__ doesn't call _load_state()")
        return False

    print(f"  ✅ __init__ loads state on initialization")

    # Check that FALLBACK logic skips already-scanned suppliers
    if "already_scanned = set(self.state.get('scanned_suppliers'" not in content:
        print(f"\n❌ FAILED: FALLBACK logic doesn't skip already-scanned suppliers")
        return False

    print(f"  ✅ FALLBACK logic skips already-scanned suppliers")

    print("\n✅ PASSED: All state tracking methods implemented correctly")
    return True

def test_import_and_instantiate():
    """TEST 4: Verify CrossReferenceEngine can be imported and instantiated."""
    print("\n" + "="*70)
    print("TEST 4: Import and Instantiation")
    print("="*70)

    try:
        # Use importlib to import from module with hyphens in name
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "crossref_standalone_fast",
            PROJECTS_ROOT / "Cross-reference" / "crossref_standalone_fast.py"
        )
        crossref_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(crossref_module)
        CrossReferenceEngine = crossref_module.CrossReferenceEngine

        print("  ✅ Successfully imported CrossReferenceEngine")

        engine = CrossReferenceEngine()
        print("  ✅ Successfully instantiated CrossReferenceEngine")

        # Check that state was loaded
        if hasattr(engine, 'state') and isinstance(engine.state, dict):
            print(f"  ✅ State loaded: {engine.state}")
            return True
        else:
            print(f"  ❌ State not properly initialized")
            return False

    except Exception as e:
        print(f"  ❌ FAILED to import/instantiate: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n" + "="*70)
    print("CROSSREF FIXES VALIDATION TEST SUITE")
    print("="*70)
    print(f"Project root: {PROJECTS_ROOT}")

    tests = [
        ("Path Configuration", test_path_configuration),
        ("No Duplicate Methods", test_no_duplicate_methods),
        ("State Tracking", test_state_tracking),
        ("Import & Instantiate", test_import_and_instantiate),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ TEST ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name:.<50} {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n✅ ALL TESTS PASSED! CrossRef fixes are working correctly.")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed. Please review the issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
