# Track 2 — Claim to source

**Deliverable:** given a claim as it is actually written, return the primary
document or nothing.

```bash
python tracks/2_claim_to_source/run.py --out out/baseline.jsonl
python -m pephack.scoring.claims --submission out/baseline.jsonl --allow-unconfirmed
python -m pephack.scoring.claims --submission out/yours.jsonl --resolve
```

## Submission format

```json
{"id": "c005", "verdict": "animal_only",
 "cited_ids": ["PMID:12345678", "NCT01234567"], "note": "optional"}
```

One line per gold item. Verdicts: see `data/gold/VERDICTS.md`.

## How you will be scored

`macro_f1`, not accuracy. `no_evidence_found` is the modal correct answer in
this domain, so accuracy rewards an agent that always says it. The scorer prints
the best constant predictor next to your score and tells you whether you beat
it.

It also reports:

- **control accuracy** — restricted to compounds where the answer is knowable
  (approved drugs, the one that failed its trials). Fail here and you are broken
  regardless of your overall number.
- **unresolvable rate** with `--resolve` — cited identifiers that do not resolve
  against the live APIs. This is your hallucinated citation rate and it is the
  single most interesting number you can show at 6:30.

## The baseline that never reads a paper

`run.py` runs two PubMed counts per claim and picks a verdict from those alone.
It will get several items right for the wrong reasons. That is why it is here:
nobody gets to claim a win without beating counting.

## Things that will bite you

- `not_a_factual_claim` is a real category, not an escape hatch. A lot of what
  gets said about these compounds names no outcome, population or comparator, so
  no document can settle it. A system without this category will invent a
  verdict instead.
- A claim about a compound's *origin story* is still a claim needing a source.
- Vendors cite work on a different molecule than the one they sell. Check
  whether a cited study used the marketed fragment or the full-length protein.
