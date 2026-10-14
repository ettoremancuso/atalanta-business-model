import sys
from pathlib import Path

# make `src` importable when pytest is run from the repository root (as in GitHub Actions)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
