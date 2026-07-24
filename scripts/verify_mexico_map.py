#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
import time
import subprocess
import threading
import json
import urllib.request

user_id = '14ab2d63-1eef-43d9-b3f4-748566bad8da'

print("=" * 70)
print("STEP 3: VERIFY MEXICO ON MAP")
print("=" * 70)
print()

# Start uvicorn server in background
def run_server():
    subprocess.run([sys.executable, '-m', 'uvicorn', 'api.main:app', '--port', '8001'],
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)

print("[VERIFY] Starting uvicorn server...")
server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()
time.sleep(8)

print("[VERIFY] Server started, calling debug endpoint...")
print()

try:
    # Call debug endpoint
    url = f'http://127.0.0.1:8001/api/debug/jobs-by-country'
    headers = {'x-user-id': user_id}

    print(f"[VERIFY] GET {url}")
    print()

    req = urllib.request.Request(url, headers=headers)

    with urllib.request.urlopen(req, timeout=30) as response:
        debug_data = json.loads(response.read().decode())

        print("=" * 70)
        print("JOBS BY COUNTRY (From Debug Endpoint)")
        print("=" * 70)
        print()

        total = debug_data.get('total_jobs', 0)
        print(f"Total active jobs: {total}")
        print()

        print("By search_country (Discovery tagging):")
        by_search = debug_data.get('by_search_country', {})
        for code in sorted(by_search.keys()):
            count = by_search[code]
            pct = (count / total * 100) if total > 0 else 0
            print(f"  {code:>4s}: {count:>5d} jobs ({pct:>5.1f}%)")

        print()
        print("By location extraction (Legacy fallback):")
        by_location = debug_data.get('by_location_extraction', {})
        if by_location:
            for code in sorted(by_location.keys()):
                count = by_location[code]
                print(f"  {code:>4s}: {count:>5d} jobs")
        else:
            print("  (none)")

        print()
        print("=" * 70)
        print("MEXICO SAMPLES")
        print("=" * 70)
        print()

        samples = debug_data.get('mexico_samples', [])
        if samples:
            print(f"Found {len(samples)} Mexico job samples:")
            for i, job in enumerate(samples, 1):
                print(f"{i}. {job.get('title')} ({job.get('company')})")
                print(f"   search_country: {job.get('search_country')}")
                print(f"   location: {job.get('location')}")
                print()
        else:
            print("No Mexico jobs found")

        print("=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print()

        mexico_count = by_search.get('mx', 0)
        if mexico_count > 0:
            print(f"✓ MEXICO IS ON MAP: {mexico_count} jobs with search_country='mx'")
        else:
            print("✗ MEXICO NOT ON MAP: 0 jobs with search_country='mx'")

        print()

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {str(e)}")
