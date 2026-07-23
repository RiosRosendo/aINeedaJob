#!/usr/bin/env python3
import subprocess
import sys
import time

# Start uvicorn server
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "api.main:app", "--port", "8001"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

# Give server time to start
time.sleep(5)

# Try to make a request
import urllib.request
import json

try:
    headers = {"x-user-id": "14ab2d63-1eef-43d9-b3f4-748566bad8da"}
    req = urllib.request.Request(
        "http://127.0.0.1:8001/api/jobs?limit=2",
        headers=headers
    )
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print(f"SUCCESS! Got {len(data['jobs'])} jobs")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {str(e)}")

# Kill the server
proc.terminate()
proc.wait(timeout=5)

# Print any errors from the server
print("\n--- Server stderr ---")
print(proc.stderr.read())
print("\n--- Server stdout (last 50 lines) ---")
lines = proc.stdout.read().split('\n')
for line in lines[-50:]:
    if line.strip():
        print(line)
