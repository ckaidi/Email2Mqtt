import requests
import sys

try:
    response = requests.get('http://localhost:8000/health', verify=False)
    if response.status_code == 200:
        sys.exit(0)
    else:
        sys.exit(1)
except Exception:
    sys.exit(1)