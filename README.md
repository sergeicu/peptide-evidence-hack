# Peptides: Claims vs Evidence — starter pack

SF × MIT Hack Day. Agents that audit the evidence behind a peptide.

Everything here is public data and public APIs. No lab, no GPU, no biology
background. If you can write Python and call an API you can compete.

## Five minutes to your first number

```bash
git clone https://github.com/sergeicu/peptide-evidence-hack
cd peptide-evidence-hack
python -m pip install -e ".[dev]"

make smoke            # hit every API once. DO THIS FIRST.
make test             # 26 offline tests, no network needed

python tracks/1_evidence_graph/run.py --compound BPC-157
```

That last command builds an evidence card with no LLM involved. It is the
baseline you have to beat.

> **Read this before you trust anything in here.** The API clients were written
> against the documented request and response shapes but could not be executed
> on the machine that built them, because outbound access to these hosts was
> blocked there. `make smoke` is therefore the real integration test. If a check
> fails, it is a bug in this repo — fix it and open a PR, because everyone else
> in the room is about to hit the same thing.

## What's here

```
pephack/
  pubmed.py         E-utilities. classify() gets species and study design from
                    MeSH instead of guessing with an LLM. Start here.
  europepmc.py      full text, citations and references (the citation graph)
  ctgov.py          ClinicalTrials.gov v2. Registration is not evidence.
  openfda.py        FAERS, labels. Read the caveats, they are load-bearing.
  opentargets.py    is there human genetic support for a claimed target
  concentration.py  how concentrated is a literature. The BPC-157 number.
  evidence_card.py  assembles the no-LLM baseline card
  scoring/claims.py      scores claim-to-source submissions
  scoring/prediction.py  scores sequence-property models, with a shortcut probe
  datasets/              PepBenchmark and MegaScale loaders
data/
  compounds.csv     24 compounds, with controls (see below)
  gold/claims.jsonl 12 seed claims. You write the other 38.
  fixtures/         offline fixtures so tests and dev need no network
tracks/             a runnable baseline per track
```

## The three ideas worth stealing from this repo

**1. MeSH beats an LLM for species and study design.** PubMed already records
whether a paper is about humans or rats, and whether it is a randomised trial or
a case report. `pubmed.Paper.classify()` reads it off. Use an LLM for what MeSH
does not carry — dose, route, sample size, what the paper concluded — and then
score your LLM against MeSH on the fields where both exist. That is a free
accuracy check on your own pipeline.

**2. The controls are the point.** `data/compounds.csv` mixes gray-market
compounds with approved drugs (semaglutide, tirzepatide, tesamorelin,
bremelanotide), one that ran real human trials and failed them (AOD-9604), one
approved then withdrawn (sermorelin), and one approved only outside the US
(thymosin alpha-1). In this domain `no_evidence_found` is the modal correct
answer, so an agent that always says it scores well and is useless. The controls
catch that. The scorer reports per-status-group accuracy and the best constant
baseline next to your score, and you have to beat it on macro F1, not accuracy.

**3. Check whether your model learned the property or learned the dataset.**
`scoring/prediction.py` trains a probe on four trivial features — length, net
charge, mean hydrophobicity, aromaticity — and reports its AUC next to yours.
Peptide activity datasets are usually built by taking positives from one
database and negatives from somewhere convenient, which leaves the classes
differing in bulk composition. If your model is within 0.02 of the probe you
have built a detector of how the dataset was assembled. It also splits the test
set by similarity to training data and reports AUC separately on the near and
far halves, because that gap is what memorisation looks like.

## The gold set is yours, not ours

`data/gold/claims.jsonl` ships 12 seed claims with `confirmed_by: null`. The
scorer refuses to run until a human has checked each label against the primary
documents and put their name in that field:

```bash
python -m pephack.scoring.claims --submission out/sub.jsonl
# -> 12 of 12 gold items have no confirmed_by. [...]
```

Pass `--allow-unconfirmed` to score anyway, and say so when you demo. The seed
labels were written by whoever built this pack from a few hours of searching.
They are a starting point, not ground truth. Writing the other 38 claims and
confirming all 50 is the morning's work, and the answer key belongs to the room.

See `data/gold/VERDICTS.md` for the verdict vocabulary.

## House rules

1. Use the split you were given. If you make your own, report both.
2. Say which of your test items your model could have seen in training.
3. Beat three baselines: random, nearest-neighbour, and the published number.
   For the evidence tracks, beat the counts-only baseline in
   `tracks/2_claim_to_source/run.py`, which never reads a paper.
4. A verdict with no document is not an answer.
5. This repo grades evidence. It does not produce protocols, doses or sourcing,
   and neither should anything built on it.

## Rate limits and API keys

Everything works without keys, but you will be sharing one room's IP with forty
other people. The HTTP layer caches every response to `cache/` — leave that on.

```bash
export NCBI_API_KEY=...     # free, raises PubMed from 3 to 10 req/s
export OPENFDA_API_KEY=...  # free, raises openFDA from 1k to 120k req/day
export PEPHACK_OFFLINE=1    # serve everything from data/fixtures/ instead
```

## Licence

MIT. The data behind the APIs has its own terms: MegaScale is CC-BY-4.0,
PepBenchmark has its own licence, and openFDA data carries the FDA's disclaimer
that it must not be used to make medical decisions.
