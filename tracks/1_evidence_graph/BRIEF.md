# Track 1 — Evidence graph

**Build:** an agent that takes a compound and returns every paper behind it —
how many independent groups produced them, which were animal and which were
human, how many subjects, what dose, what route. One card per compound, every
number linked to its source.

```bash
python -m pip install -e ".[dev]"

python tracks/1_evidence_graph/run.py --compound BPC-157        # the no-LLM baseline
python tracks/1_evidence_graph/solution.py --compound BPC-157        # your turn
```

## Start by running the baseline

`baseline.py` makes about ten API calls and produces a card with **no LLM at
all**. Species and study design come off PubMed's MeSH headings, not from a
model. Look at its output before you write anything — a surprising amount of
this track is free, and your agent has to be better than free.

## What free cannot do — this is your actual job

| Field | Why the baseline can't | Where to get it |
|---|---|---|
| dose, route | no structured field anywhere | abstract and full text, via LLM extraction |
| sample size | occasionally in the abstract, never reliably | full text |
| does the paper support the claim | counting papers ≠ evidence of an effect | reading |
| non-English literature | an English query misses it | Semax and Epitalon are mostly Russian |
| self-citation | needs the citation graph | `europepmc.citations()` / `.references()` |

## The free accuracy check

MeSH gives you ground truth for species and study design. Run your LLM
extraction on those two fields as well, compare against MeSH, and you have a
measured error rate for your own pipeline — which tells you how much to trust
it on dose and sample size, where there is no ground truth. Put that number in
your demo. Almost nobody does this and it is the difference between a demo and
a result.

## The headline number

```python
from pephack import concentration
m = concentration.author_concentration(papers)
m["top_author_share"]                      # one author on what share of papers
m["share_independent_of_top_author"]       # how much is genuinely independent
```

"500 papers" and "500 papers from one lab" are different evidence bases. The
affiliation clustering is deliberately crude — improving it is a real
contribution, and a better version should disagree with this one on specific
compounds in a way you can defend.

See `README.md` for detail.
