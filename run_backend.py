#!/usr/bin/env python3
import subprocess
import sys

# Run uvicorn server
subprocess.run([
    sys.executable, "-m", "uvicorn",
    "api.main:app",
    "--port", "8001",
    "--host", "127.0.0.1"
])
