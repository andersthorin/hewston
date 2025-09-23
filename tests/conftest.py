import os
import sys

# Ensure repository root is on sys.path so "backend" package can be imported in tests
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

