#!/usr/bin/env python3
"""
Verify that the token from surveys.json can be accessed
"""
import json
from datetime import datetime, timedelta

# Read the actual surveys.json
with open('surveys.json', 'r') as f:
    surveys = json.load(f)

print(f"📊 Total tokens in surveys.json: {len(surveys)}")
print("\n🔍 Token details:")

SURVEY_EXPIRY_HOURS = 24

for token, data in surveys.items():
    created = datetime.fromisoformat(data['created_at'])
    now = datetime.now()
    age_hours = (now - created).total_seconds() / 3600
    is_expired = age_hours > SURVEY_EXPIRY_HOURS
    
    print(f"\n  Token: {token}")
    print(f"    Issue: {data['issue_key']}")
    print(f"    Language: {data['language']}")
    print(f"    Age: {age_hours:.1f} hours")
    print(f"    Expired: {'❌ YES' if is_expired else '✅ NO'}")
    print(f"    Used: {data['is_used']}")

# Check for the specific token the user mentioned
target_token = "-Zmz-Hwpg7veUiHiMARfLA"
print(f"\n🔎 Looking for token: {target_token}")
if target_token in surveys:
    print(f"   ✅ Found in surveys.json")
else:
    print(f"   ❌ NOT found in surveys.json")
    print(f"   This token was never created or was already deleted")
