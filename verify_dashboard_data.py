#!/usr/bin/env python3
import subprocess
import sys
import time
import threading
import json
import urllib.request

def run_server():
    subprocess.run([sys.executable, '-m', 'uvicorn', 'api.main:app', '--port', '8001'])

print("[VERIFY] Starting backend server...")
thread = threading.Thread(target=run_server, daemon=True)
thread.start()
time.sleep(12)

user_id = '14ab2d63-1eef-43d9-b3f4-748566bad8da'
headers = {'x-user-id': user_id}

print("=" * 70)
print("DASHBOARD DATA VERIFICATION")
print("=" * 70)

try:
    # Test /api/jobs endpoint (what dashboard uses for "Jobs Found")
    print("\n[TEST 1] /api/jobs endpoint (Dashboard header)")
    req = urllib.request.Request(f'http://127.0.0.1:8001/api/jobs?limit=1', headers=headers)
    with urllib.request.urlopen(req, timeout=5) as response:
        data = json.loads(response.read().decode())
        jobs_discovered = data.get('total_discovered', data.get('total_count'))
        jobs_scored = data.get('total_count')
        print(f"  total_discovered: {jobs_discovered} (should be 4,251)")
        print(f"  total_count (scored): {jobs_scored}")

    # Test /api/applications endpoint
    print("\n[TEST 2] /api/applications endpoint")
    req = urllib.request.Request(f'http://127.0.0.1:8001/api/applications?limit=100', headers=headers)
    with urllib.request.urlopen(req, timeout=5) as response:
        apps = json.loads(response.read().decode())
        pending = len([a for a in apps if a.get('status') == 'pending_approval'])
        print(f"  Total applications returned: {len(apps)}")
        print(f"  Pending approvals: {pending} (should be 11)")

    # Test /api/jobs/by-country endpoint
    print("\n[TEST 3] /api/jobs/by-country endpoint (Map)")
    req = urllib.request.Request(f'http://127.0.0.1:8001/api/jobs/by-country', headers=headers)
    with urllib.request.urlopen(req, timeout=5) as response:
        countries = json.loads(response.read().decode())
        total_on_map = sum(c['count'] for c in countries)
        print(f"  Countries on map: {len(countries)}")
        print(f"  Total jobs grouped: {total_on_map}")

    # Verify counts match
    print("\n" + "=" * 70)
    print("CONSISTENCY CHECK")
    print("=" * 70)

    if jobs_discovered == 4251:
        print("✓ Dashboard will show 'Jobs Found: 4,251'")
    else:
        print(f"⚠ Dashboard shows: {jobs_discovered} (expected 4,251)")

    if pending == 11:
        print("✓ Approvals page shows: 11 pending")
    else:
        print(f"⚠ Approvals shows: {pending}")

    if total_on_map > 0:
        print(f"✓ Map shows: {len(countries)} countries with {total_on_map} jobs")
    else:
        print(f"⚠ Map empty")

except Exception as e:
    print(f"Error: {type(e).__name__}: {str(e)}")

print("\n" + "=" * 70)
print("CONCLUSION")
print("=" * 70)
print("Dashboard data should be consistent after this verification.")
