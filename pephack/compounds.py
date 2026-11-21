"""The compound registry.

status_hypothesis is a STARTING GUESS, not ground truth. Task zero for the
evidence tracks is checking it against the FDA record and correcting this file.
Regulatory status moves: BPC-157 was placed in FDA 503A Category 2 in September
2023 and removed from Category 2 in April 2026, and removal from Category 2 is
not the same as being allowed. If your card prints a status, it has to print
the document and the date it came from.

The set deliberately mixes:
  - approved drugs (semaglutide, tirzepatide, tesamorelin, bremelanotide)
  - one that ran real human trials and failed them (AOD-9604)
  - one that was approved and withdrawn (sermorelin)
  - one approved outside the US only (thymosin alpha-1)
  - one real research peptide that is not a drug (LL-37)
  - fifteen gray-market compounds
If an agent says "no good evidence" for semaglutide, it is broken. The controls
are there to catch that, so always report your score per status group.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

REGISTRY = Path(__file__).resolve().parent.parent / "data" / "compounds.csv"


@dataclass
class Compound:
    name: str
    aliases: list[str]
    status_hypothesis: str
    common_claim: str
    pubmed_query: str
    faers_name: str
    notes: str

    @property
    def is_control(self) -> bool:
        """True for compounds with a known, checkable evidence base."""
        return self.status_hypothesis in {
            "approved", "approved_withdrawn", "approved_elsewhere", "failed", "investigational"
        }


def load(path: Path | str = REGISTRY) -> list[Compound]:
    out = []
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            out.append(Compound(
                name=row["name"].strip(),
                aliases=[a.strip() for a in row["aliases"].split(";") if a.strip()],
                status_hypothesis=row["status_hypothesis"].strip(),
                common_claim=row["common_claim"].strip(),
                pubmed_query=row["pubmed_query"].strip(),
                faers_name=row["faers_name"].strip(),
                notes=row["notes"].strip(),
            ))
    return out


def by_name(name: str, path: Path | str = REGISTRY) -> Compound:
    needle = name.strip().lower()
    for c in load(path):
        if c.name.lower() == needle or needle in [a.lower() for a in c.aliases]:
            return c
    raise KeyError(f"{name!r} is not in the registry; add it to data/compounds.csv")
