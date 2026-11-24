# Track 2 — Claim to source

**Build:** an agent that takes a claim as it is actually written on a forum or
a vendor page and comes back with the primary document, or with nothing, which
is frequently the correct answer.

```bash
python -m pip install -e ".[dev]"

python tracks/2_claim_to_source/run.py --out out/baseline.jsonl                 # counts-only baseline
python -m pephack.scoring.claims --submission out/baseline.jsonl --allow-unconfirmed
python tracks/2_claim_to_source/solution.py --out out/mine.jsonl                     # your turn
python -m pephack.scoring.claims --submission out/mine.jsonl --resolve
```

## First task of the morning: own the answer key

The gold set ships 12 seed claims with `confirmed_by: null`, and **the scorer
refuses to run until a human has checked each label against the primary
documents and signed it.** Those seed labels were written from a few hours of
searching by whoever built the pack. They are a starting point, not truth.

Write the other 38 claims from real vendor pages and forum posts, confirm all
50, and the answer key belongs to the room rather than to us.

## You are scored on macro F1, not accuracy

`no_evidence_found` is the modal correct answer in this domain, so accuracy
rewards an agent that always says it. The scorer prints the best constant
predictor next to your score and tells you whether you beat it. It also prints:

- **control accuracy** — only compounds where the answer is knowable: approved
  drugs, and the one that ran human trials and failed them. Fail here and you
  are broken whatever your overall number says.
- **unresolvable rate** (`--resolve`) — cited identifiers that don't resolve
  against the live APIs. Your hallucinated-citation rate, and the single most
  interesting number you can put on screen at 6:30.

## Submission format

```json
{"id": "c005", "verdict": "animal_only",
 "cited_ids": ["PMID:12345678", "NCT01234567"], "note": "optional"}
```

Verdicts are in `data/gold/VERDICTS.md` in the core repo. `not_a_factual_claim`
is a real category, not an escape hatch: much of what gets said about these
compounds names no outcome, population or comparator, and a system without that
category will invent a verdict instead.

## Beat counting

`baseline.py` runs two PubMed counts per claim and picks a verdict from those
alone. It never reads a paper and it will still get several items right. Nobody
claims a win without beating it.

See `README.md` for the traps.
