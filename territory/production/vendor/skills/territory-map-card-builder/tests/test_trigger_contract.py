from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_trigger_contract.py"


def test_trigger_contract() -> None:
    result = subprocess.run([sys.executable, str(VALIDATOR)], text=True, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
