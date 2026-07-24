#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
import time
import subprocess
import threading
import json
import urllib.request
import urllib.error

user_id = '14ab2d63-1eef-43d9-b3f4-748566bad8da'

print("=" * 70)
print("STEP 2: RUN FRESH MEXICO DISCOVERY")
print("=" * 70)
print()

# Start uvicorn server in background
def run_server():
    subprocess.run([sys.executable, '-m', 'uvicorn', 'api.main:app', '--port', '8001'],
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)

print("[DISCOVERY] Starting uvicorn server...")
server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()
time.sleep(8)

print("[DISCOVERY] Server started, triggering Mexico search...")
print()

try:
    # Trigger job search via POST /api/jobs/search
    url = 'http://127.0.0.1:8001/api/jobs/search'
    headers = {
        'x-user-id': user_id,
        'Content-Type': 'application/json'
    }

    payload = json.dumps({
        'user_id': user_id,
        'roles': ['Robotics Engineer', 'Embedded Systems Engineer', 'AI Engineer'],
        'country': 'mx'
    })

    print(f"[DISCOVERY] POST {url}")
    print(f"[DISCOVERY] Payload: {payload}")
    print()

    req = urllib.request.Request(url, data=payload.encode(), headers=headers, method='POST')

    print("[DISCOVERY] Waiting for discovery to complete (this may take 1-2 minutes)...")
    print()

    with urllib.request.urlopen(req, timeout=180) as response:
        result = json.loads(response.read().decode())

        print("=" * 70)
        print("MEXICO DISCOVERY RESULTS")
        print("=" * 70)
        print()
        print(f"Status: {result.get('status')}")
        print(f"Jobs found: {result.get('jobs_found')}")
        print(f"Jobs processed: {result.get('jobs_processed')}")
        print(f"Applied: {result.get('applied')}")
        print(f"Review: {result.get('review')}")
        print(f"Message: {result.get('message')}")
        print()

except Exception as e:
    print(f"ERROR: {type(e).__name__}: {str(e)}")
    print()
    print("Continuing to next step...")

# Check Mexico jobs now
print("=" * 70)
print("CHECKING MEXICO JOBS AFTER DISCOVERY")
print("=" * 70)
print()

from tools.db import execute_query

mexico_jobs = execute_query(
    """
    SELECT COUNT(*) as cnt FROM jobs
    WHERE user_id = %s AND search_country = 'mx' AND expires_at IS NULL
    """,
    (user_id,)
)

mexico_count = mexico_jobs[0]['cnt'] if mexico_jobs else 0
print(f"Mexico jobs (search_country='mx'): {mexico_count}")

# Show samples
samples = execute_query(
    """
    SELECT id, title, company, search_country, location
    FROM jobs
    WHERE user_id = %s AND search_country = 'mx' AND expires_at IS NULL
    LIMIT 5
    """,
    (user_id,)
)

if samples:
    print()
    print("Mexico job samples:")
    for job in samples:
        print(f"  - {job.get('title')} ({job.get('company')})")
        print(f"    Location: {job.get('location')}")
        print()
