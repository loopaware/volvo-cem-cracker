#!/usr/bin/env python3
import requests
import sys

try:
    response = requests.get("http://localhost:5001/health")
    if response.status_code == 200 and response.json() == {"status": "ok"}:
        sys.exit(0)
    else:
        sys.exit(1)
except requests.exceptions.RequestException:
    sys.exit(1)
