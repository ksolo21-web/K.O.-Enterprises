"""Local private M5 cohort design summary; never activates field operations."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from inspection_engine.m5_pilot_readiness import assess_pilot_cohort_design
from inspection_engine.serious_defect_benchmark import BenchmarkBlock
from scripts.m4_safety_benchmark_cli import _private_json


def main(argv=None):
    parser = argparse.ArgumentParser(description="M5 paper pilot design only")
    parser.add_argument("--planned-cases", type=Path, required=True)
    parser.add_argument("--training-property-groups", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = assess_pilot_cohort_design(
            _private_json(args.planned_cases),
            training_property_groups=_private_json(args.training_property_groups))
    except (BenchmarkBlock, OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "M5_PILOT_DESIGN_BLOCKED",
                          "reason": str(exc), "customer_release_allowed": False}))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
