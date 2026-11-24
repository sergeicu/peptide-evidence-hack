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

## The compound list

Track 1's default set is `data/compounds.csv` — 24 compounds chosen so the
scorer has controls (approved drugs, one that failed its human trials, one
withdrawn, one approved only outside the US).

The wider set is `data/community/compounds.csv` — 48 compounds taken from the
California Peptide Club wiki, with that wiki's own tier ratings and its 1-10
self-assessment of how much human evidence each one has. Start with the 24, then
run your pipeline over the 48.

Three things in that file are worth a card of their own:

- **8 of the 48 are flagged by the wiki itself as not peptides** — MK-677,
  Dihexa, Methylene Blue, Tesofensine, SLU-PP-332, 5-Amino-1MQ, LIPO-C, NAD+.
  A category that contains a dye and a vitamin precursor is telling you
  something about how the category is used.
- **8 compounds have no identified receptor and 10 are contested.** "No known
  receptor" and "500 papers on mechanism" is a tension worth surfacing.
- **`human_research_score` is the wiki's own guess** at how much human evidence
  exists, 1-10, for 35 of the 48. You can check it: correlate it against
  `pubmed.species_breakdown()` and you have a scatter plot of community
  perception against indexed reality. Nobody has published that chart.

See `data/community/README.md` for the provenance of all of it, including why
only 2 of the wiki's 209 citations reach primary literature.
