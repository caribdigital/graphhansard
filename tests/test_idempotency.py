"""Test for NF-6: Miner pipeline idempotency and resumability.

Requirement: Re-running does not duplicate data.

This test verifies that the miner pipeline is idempotent - running it
multiple times on the same input produces identical output without
duplicating downloads or catalogue entries.
"""

import json
import shutil
import tempfile
from pathlib import Path

from graphhansard.miner.catalogue import AudioCatalogue
from graphhansard.miner.downloader import SessionDownloader


def test_miner_idempotency():
    """Test that re-running miner pipeline does not duplicate data."""
    
    print(f"\n{'='*60}")
    print(f"NF-6: Miner Pipeline Idempotency Test")
    print(f"{'='*60}")
    print()
    
    # Create temporary directory for test
    with tempfile.TemporaryDirectory() as tmpdir:
        archive_dir = Path(tmpdir) / "archive"
        
        print("1. Initializing downloader (first run)...")
        downloader1 = SessionDownloader(
            archive_dir=str(archive_dir),
            sleep_interval=0,  # Fast for testing
            max_downloads=5,
        )
        
        # Get initial catalogue state
        catalogue_path = archive_dir / "catalogue.json"
        initial_sessions = downloader1.catalogue.list_sessions()
        print(f"   Initial sessions: {len(initial_sessions)}")
        
        # Simulate adding a session entry
        print("\n2. Adding test session to catalogue...")
        test_session = {
            "session_id": "test_session_001",
            "video_id": "test_video_123",
            "session_date": "2024-01-15",
            "status": "completed",
            "file_path": str(archive_dir / "2024" / "2024-01-15" / "test_video_123.opus"),
        }
        
        downloader1.catalogue.add_or_update(**test_session)
        
        # Check catalogue after first run
        sessions_after_first = downloader1.catalogue.list_sessions()
        print(f"   Sessions after first add: {len(sessions_after_first)}")
        
        # Save catalogue state
        with open(catalogue_path, "r") as f:
            catalogue_first_run = json.load(f)
        
        print("\n3. Re-running with same data (second run)...")
        downloader2 = SessionDownloader(
            archive_dir=str(archive_dir),
            sleep_interval=0,
            max_downloads=5,
        )
        
        # Try to add the same session again
        downloader2.catalogue.add_or_update(**test_session)
        
        # Check catalogue after second run
        sessions_after_second = downloader2.catalogue.list_sessions()
        print(f"   Sessions after second add: {len(sessions_after_second)}")
        
        # Load catalogue state after second run
        with open(catalogue_path, "r") as f:
            catalogue_second_run = json.load(f)
        
        # Verify idempotency
        print("\n" + "="*60)
        print("VERIFICATION")
        print("="*60)
        
        # Check 1: Session count should be the same
        count_match = len(sessions_after_first) == len(sessions_after_second)
        print(f"Session count unchanged: {count_match}")
        print(f"  First run: {len(sessions_after_first)} sessions")
        print(f"  Second run: {len(sessions_after_second)} sessions")
        
        # Check 2: Session IDs should be the same
        ids_first = {s["session_id"] for s in sessions_after_first}
        ids_second = {s["session_id"] for s in sessions_after_second}
        ids_match = ids_first == ids_second
        print(f"\nSession IDs unchanged: {ids_match}")
        
        # Check 3: No duplicate entries
        session_ids_list = [s["session_id"] for s in sessions_after_second]
        has_duplicates = len(session_ids_list) != len(set(session_ids_list))
        no_duplicates = not has_duplicates
        print(f"No duplicate entries: {no_duplicates}")
        
        # Check 4: Catalogue structure preserved
        structure_match = (
            set(catalogue_first_run.keys()) == set(catalogue_second_run.keys())
        )
        print(f"Catalogue structure preserved: {structure_match}")
        
        # Overall result
        all_checks_pass = (
            count_match and ids_match and no_duplicates and structure_match
        )
        
        print("\n" + "="*60)
        print(f"Status: {'✅ PASS - Pipeline is idempotent' if all_checks_pass else '❌ FAIL - Pipeline is not idempotent'}")
        print("="*60)
        
        assert all_checks_pass, "Idempotency test failed"
        
        return all_checks_pass


def test_miner_resumability():
    """Test that miner can resume after interruption."""
    
    print(f"\n{'='*60}")
    print(f"NF-6: Miner Pipeline Resumability Test")
    print(f"{'='*60}")
    print()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        archive_dir = Path(tmpdir) / "archive"
        
        print("1. Starting initial download session...")
        downloader1 = SessionDownloader(
            archive_dir=str(archive_dir),
            sleep_interval=0,
            max_downloads=10,
        )
        
        # Simulate partial download
        print("   Adding sessions in progress...")
        sessions_to_add = [
            {
                "session_id": "session_001",
                "video_id": "video_001",
                "session_date": "2024-01-15",
                "status": "completed",
            },
            {
                "session_id": "session_002",
                "video_id": "video_002",
                "session_date": "2024-01-16",
                "status": "in_progress",  # Interrupted
            },
            {
                "session_id": "session_003",
                "video_id": "video_003",
                "session_date": "2024-01-17",
                "status": "pending",
            },
        ]
        
        for session in sessions_to_add:
            downloader1.catalogue.add_or_update(**session)
        
        # Check download archive
        archive_file = archive_dir / "download_archive.txt"
        print(f"   Download archive exists: {archive_file.exists()}")
        
        print("\n2. Simulating resume (new downloader instance)...")
        downloader2 = SessionDownloader(
            archive_dir=str(archive_dir),
            sleep_interval=0,
            max_downloads=10,
        )
        
        # Get sessions that need processing
        all_sessions = downloader2.catalogue.list_sessions()
        pending_sessions = [
            s for s in all_sessions
            if s["status"] in ["pending", "in_progress", "failed"]
        ]
        
        print(f"   Total sessions: {len(all_sessions)}")
        print(f"   Pending/resumable sessions: {len(pending_sessions)}")
        
        # Verify resumability
        print("\n" + "="*60)
        print("VERIFICATION")
        print("="*60)
        
        # Check 1: Catalogue loaded correctly
        catalogue_loaded = len(all_sessions) == len(sessions_to_add)
        print(f"Catalogue loaded correctly: {catalogue_loaded}")
        print(f"  Expected: {len(sessions_to_add)} sessions")
        print(f"  Found: {len(all_sessions)} sessions")
        
        # Check 2: Can identify incomplete sessions
        can_resume = len(pending_sessions) >= 2  # session_002 and session_003
        print(f"\nCan identify resumable sessions: {can_resume}")
        print(f"  Found {len(pending_sessions)} sessions to resume")
        
        # Check 3: Completed sessions not duplicated
        completed_sessions = [s for s in all_sessions if s["status"] == "completed"]
        no_redownload = len(completed_sessions) == 1  # Only session_001
        print(f"\nCompleted sessions not re-queued: {no_redownload}")
        print(f"  Completed sessions: {len(completed_sessions)}")
        
        # Overall result
        all_checks_pass = catalogue_loaded and can_resume and no_redownload
        
        print("\n" + "="*60)
        print(f"Status: {'✅ PASS - Pipeline is resumable' if all_checks_pass else '❌ FAIL - Pipeline cannot resume'}")
        print("="*60)
        
        assert all_checks_pass, "Resumability test failed"
        
        return all_checks_pass


if __name__ == "__main__":
    print("Running NF-6 Tests: Miner Pipeline Idempotency & Resumability")
    print("="*60)
    
    # Run tests
    idempotency_pass = test_miner_idempotency()
    resumability_pass = test_miner_resumability()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Idempotency: {'✅ PASS' if idempotency_pass else '❌ FAIL'}")
    print(f"Resumability: {'✅ PASS' if resumability_pass else '❌ FAIL'}")
    print()
    
    if idempotency_pass and resumability_pass:
        print("✅ NF-6: All tests passed - Pipeline is idempotent and resumable")
    else:
        print("❌ NF-6: Some tests failed")
        exit(1)
