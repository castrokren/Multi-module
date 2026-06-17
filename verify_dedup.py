#!/usr/bin/env python3
"""
Test script to verify dedup database is created and tracks URLs properly.
"""
import sqlite3
import os
import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "PROJECTS" / "src" / "services" / "scraper-full"))
from scraper_engine import _StateDB

def test_statedb_creation():
    """Verify _StateDB creates and uses SQLite correctly."""
    tmpdir = tempfile.mkdtemp()
    try:
        db_path = os.path.join(tmpdir, ".scraper_dedup.db")

        # Create DB and add some URLs
        db = _StateDB(db_path)

        # Verify file is created
        assert os.path.exists(db_path), f"Database not created at {db_path}"
        print(f"[+] Database created at {db_path}")

        # Test mark_seen and is_seen
        url1 = "https://example.com/doc1.pdf"
        url2 = "https://example.com/doc2.pdf"

        # URL should not be seen initially
        assert not db.is_seen(url1), "URL should not be seen initially"
        print(f"[+] URL not seen initially: {url1}")

        # Mark it seen
        db.mark_seen(url1, "queued")
        assert db.is_seen(url1), "URL should be seen after mark_seen"
        print(f"[+] URL marked seen: {url1}")

        # Other URL should still not be seen
        assert not db.is_seen(url2), "Different URL should not be seen"
        print(f"[+] Different URL not seen: {url2}")

        # Close DB
        db.close()

        # Reopen DB in new instance - should persist
        db2 = _StateDB(db_path)
        assert db2.is_seen(url1), "URL should be seen after reopening DB"
        print(f"[+] URL persisted after close/reopen: {url1}")

        assert not db2.is_seen(url2), "Other URL should still not be seen"
        print(f"[+] Other URL not seen after reopen: {url2}")

        # Test downloaded tracking
        file_path = "/path/to/file1.pdf"
        db2.mark_downloaded(file_path, url1, "TestSupplier")
        assert db2.is_downloaded(file_path), "File should be marked downloaded"
        print(f"[+] Downloaded file tracked: {file_path}")

        db2.close()

        # Final reopen to verify persistence
        db3 = _StateDB(db_path)
        assert db3.is_seen(url1), "URL should still be seen"
        assert db3.is_downloaded(file_path), "Downloaded file should persist"
        print(f"[+] Both URL and file persist across reopens")
        db3.close()
    finally:
        # Force cleanup
        import gc
        gc.collect()
        shutil.rmtree(tmpdir, ignore_errors=True)

def check_existing_db():
    """Check if the existing scraped-pdfs directory has a dedup database."""
    db_path = r"C:\Projects\Crawler\PROJECTS\data\scraped-pdfs\.scraper_dedup.db"
    if os.path.exists(db_path):
        print(f"\n[+] Dedup database exists: {db_path}")
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM seen_urls")
            url_count = cursor.fetchone()[0]
            print(f"  - Seen URLs: {url_count}")

            cursor.execute("SELECT COUNT(*) FROM downloaded")
            file_count = cursor.fetchone()[0]
            print(f"  - Downloaded files: {file_count}")

            conn.close()
        except Exception as e:
            print(f"  [-] Error reading database: {e}")
    else:
        print(f"\n[-] No dedup database found at {db_path}")
        print("  (Database will be created when scraper runs)")

if __name__ == "__main__":
    print("Testing _StateDB dedup functionality...\n")
    try:
        test_statedb_creation()
        print("\n[OK] All dedup tests passed!")
    except AssertionError as e:
        print(f"\n[FAIL] Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    check_existing_db()
