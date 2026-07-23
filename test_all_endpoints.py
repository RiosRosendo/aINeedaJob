#!/usr/bin/env python3
import subprocess
import sys
import time
import json
import urllib.request

# Start uvicorn server
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "api.main:app", "--port", "8001"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Give server time to start
time.sleep(6)

headers = {"x-user-id": "14ab2d63-1eef-43d9-b3f4-748566bad8da"}

tests = [
    ("GET /api/jobs?limit=3", "http://127.0.0.1:8001/api/jobs?limit=3"),
    ("GET /api/jobs/by-country", "http://127.0.0.1:8001/api/jobs/by-country"),
    ("GET /api/applications?limit=3", "http://127.0.0.1:8001/api/applications?limit=3"),
]

for test_name, url in tests:
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            print(f"✓ {test_name}: {response.status}")
            if isinstance(data, dict):
                if 'jobs' in data:
                    print(f"    Returns {len(data['jobs'])} jobs (total: {data.get('total_count', '?')})")
                elif 'countries' in data or (isinstance(data, list) and len(data) > 0 and 'country' in str(data[0])):
                    if isinstance(data, list):
                        print(f"    Returns {len(data)} countries")
                    else:
                        print(f"    Result: {list(data.keys())[:3]}")
            elif isinstance(data, list):
                print(f"    Returns {len(data)} items")
    except Exception as e:
        print(f"✗ {test_name}: {type(e).__name__}")
        if hasattr(e, 'read'):
            try:
                print(f"    Response: {e.read().decode()}")
            except:
                pass

# Kill the server
print("\nShutting down server...")
proc.terminate()
proc.wait(timeout=5)
