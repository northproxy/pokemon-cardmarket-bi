import sys
from pathlib import Path

# Ensures `from src.utils... import ...` works whether tests are run via
# `pytest`, `python -m unittest`, or from a different working directory.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
