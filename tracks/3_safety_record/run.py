#!/usr/bin/env python3
"""Baseline safety block for every compound in the registry.

    python tracks/3_safety_record/run.py --out out/safety.json

Read the caveats this prints. For compounds that were never approved, a low
report count means the reporting pathway barely exists, not that the compound
is safe, and a card that prints a bare zero is actively misleading.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pephack import compounds, openfda  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out/safety.json")
    args = ap.parse_args()

    rows = {}
    for c in compounds.load():
        name = c.faers_name or c.name
        try:
            rows[c.name] = openfda.summarise(name)
        except Exception as exc:
            rows[c.name] = {"error": f"{type(exc).__name__}: {exc}"}
        reports = rows[c.name].get("faers_reports", "?")
        label = rows[c.name].get("has_fda_label", "?")
        print(f"{c.name:<18} status={c.status_hypothesis:<18} faers={reports:<6} fda_label={label}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2))
    print(f"\nwrote {out}")
    print("\nReminder: FAERS counts are reports, not rates, and absence of reports for an "
          "unapproved compound is absence of a reporting pathway.")


if __name__ == "__main__":
    main()
