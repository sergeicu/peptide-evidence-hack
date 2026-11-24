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

## Where to get 400 more claims

`data/community/` holds the California Peptide Club corpus: 48 compounds, 438
wiki sections, 466 inline citations. It is the claim corpus for this track, and
its citation profile is the reason:

| Source kind | Unique sources | Citations |
|---|---|---|
| YouTube videos | 36 | 176 |
| X / Twitter posts | 4 | 30 |
| Trial registry | 1 | 1 |
| Primary literature | 1 | 1 |
| Company pipeline page | 1 | 1 |

Two citations out of 209 reach primary literature. One X post is cited 24 times
across different compounds. 118 of the 438 sections carry no citation at all.

So the task has a precise shape: **each claim already has a citation, and that
citation is almost always a video.** Your agent has to find the primary document
the video was describing — or establish that there is none. That is a harder and
much more useful problem than starting from a bare claim, and you can measure it,
because the wiki tells you what it thinks it is citing.

Scoring stays the same: verdict plus the primary document, graded on macro F1 and
citation resolvability. Teams that get this working leave behind something the
community can actually use.
