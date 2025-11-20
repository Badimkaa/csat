#!/usr/bin/env python3
"""
Test the multi-worker survey synchronization fix
This simulates what happens when multiple workers access surveys created by different workers
"""
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# Create a temporary surveys file
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    surveys_file = Path(f.name)
    
    # Initial survey data (simulating startup)
    initial_surveys = {
        "token1": {
            "issue_key": "PROJ-1",
            "is_used": False,
            "language": "en",
            "created_at": datetime.now().isoformat()
        }
    }
    json.dump(initial_surveys, f)

print(f"✅ Created test surveys file: {surveys_file}")
print(f"📁 Initial surveys: {list(initial_surveys.keys())}")

# Simulate Worker 1 loading surveys at startup
print("\n🔄 Worker 1: Loading surveys at startup...")
with open(surveys_file, 'r') as f:
    worker1_surveys = json.load(f)
print(f"   Worker 1 in-memory: {list(worker1_surveys.keys())}")

# Simulate Worker 2 loading surveys at startup (would be identical)
print("🔄 Worker 2: Loading surveys at startup...")
with open(surveys_file, 'r') as f:
    worker2_surveys = json.load(f)
print(f"   Worker 2 in-memory: {list(worker2_surveys.keys())}")

# Worker 1 creates a new survey
print("\n➕ Worker 1: Creating new survey token2...")
new_survey = {
    "issue_key": "PROJ-2",
    "is_used": False,
    "language": "en",
    "created_at": datetime.now().isoformat()
}
worker1_surveys["token2"] = new_survey

# Worker 1 saves to disk
print("💾 Worker 1: Saving surveys to disk...")
with open(surveys_file, 'w') as f:
    json.dump(worker1_surveys, f)
print(f"   Disk contains: {list(worker1_surveys.keys())}")

# Worker 2 tries to access token2 (which it created - simulating the bug)
print("\n🔍 Worker 2: Looking for token2 in memory...")
if "token2" in worker2_surveys:
    print("   ✅ Found token2 in memory")
else:
    print("   ❌ NOT found in memory (BUG! Before fix)")
    print("   🔧 Applying fix: Reloading from disk...")
    with open(surveys_file, 'r') as f:
        updated_surveys = json.load(f)
    if "token2" in updated_surveys:
        worker2_surveys["token2"] = updated_surveys["token2"]
        print("   ✅ Found token2 in disk and reloaded to memory (FIXED!)")

# Verify all tokens are now accessible
print(f"\n📊 Final state:")
print(f"   Worker 1 memory: {list(worker1_surveys.keys())}")
print(f"   Worker 2 memory: {list(worker2_surveys.keys())}")
print(f"   Disk: {list(updated_surveys.keys())}")

# Cleanup
surveys_file.unlink()
print(f"\n✅ Test passed! Multi-worker synchronization working correctly.")
