# Track 1 — Evidence graph

**Deliverable:** one card per compound, every number linked to its source.

```bash
python tracks/1_evidence_graph/run.py --compound BPC-157
python tracks/1_evidence_graph/run.py --all --counts-only --out out/
```

## The baseline you have to beat

`run.py` makes about ten API calls and produces a card with no LLM at all:
record counts split by species from MeSH, design mix, registered trials versus
trials with posted results, FAERS reports, and author concentration.

## What the baseline cannot do, which is your job

- **Dose, route, sample size.** Not in any structured field. This is the real
  extraction problem. Score yourself against MeSH on species and design, where
  ground truth is free, to calibrate how much to trust your extraction on the
  fields where it is not.
- **Whether a paper supports the claim.** Counting papers about a compound is
  not evidence about an effect.
- **Non-English literature.** Semax and Epitalon are mostly Russian-language.
  An English query returns almost nothing and an agent that concludes "no
  evidence" without having searched is right by accident. Record what you
  searched.
- **The citation graph.** `europepmc.citations()` and `.references()` tell you
  whether a literature cites itself. The baseline does not use them.

## The number that matters

`concentration.author_concentration()` returns `top_author_share` and
`share_independent_of_top_author`. "500 papers" and "500 papers from one lab"
are different evidence bases and the difference is computable from author lists.

The affiliation clustering is deliberately crude — it normalises the string and
groups on the first couple of significant words, so it will merge two
departments at one university and split one lab that renamed itself. Improving
it is a legitimate afternoon. A better version should disagree with this one on
specific compounds, and you should be able to say which answer is right and why.
