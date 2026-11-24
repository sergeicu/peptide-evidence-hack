# The community corpus

Derived from the **California Peptide Club** wiki (`californiapeptide.club/wiki`),
whose author is an organiser of this hack. Used with permission.

This is **the material under audit**, not a reference. Nothing in here is a
claim this repo endorses. The whole point of the evidence tracks is to find out
which of it survives contact with a primary document.

## Why this is the right corpus

The wiki covers 48 compounds, each with a structured page: mechanism, history,
clinical evidence, dosing, regulatory status, safety profile, stacks. 438
sections in total, carrying 466 inline bracketed citations that resolve to 209
numbered references.

It presents, in other words, as a properly sourced wiki. Here is where those
209 references actually point:

| Source kind | Unique sources | Citations |
|---|---|---|
| YouTube videos | 36 | 176 |
| X / Twitter posts | 4 | 30 |
| Trial registry | 1 | 1 |
| Primary literature | 1 | 1 |
| Company pipeline page | 1 | 1 |

**Two citations out of 209 reach primary literature.** One X post is cited 24
times across different compounds; one YouTube video is cited 23 times. 118 of
the 438 sections carry no citation at all.

That is not a criticism of the wiki — it is an honest reflection of where the
information about these compounds actually lives, and it is exactly what makes
this a good benchmark. The task for track 2 is to take each of those claims and
find the primary document, or establish that there isn't one.

## Files

**`compounds.csv`** — 48 compounds with the wiki's own ratings.

| Column | Meaning |
|---|---|
| `tier` | the wiki's S/A/B/C/D/F rating |
| `is_peptide` | the wiki's own flag. **8 entries are marked FALSE** (MK-677, Dihexa, Methylene Blue, Tesofensine, SLU-PP-332, 5-Amino-1MQ, LIPO-C, NAD+) |
| `receptor_class` | known / contested / none / na — 8 compounds have no identified receptor, 10 are contested |
| `human_research_score` | the wiki's 1-10 self-assessment of how much human evidence exists. Present for 35 of 48 |
| `side_effect_score` | the wiki's 1-10 severity self-assessment |
| `wiki_sections`, `n_references` | size of that compound's page |

**`sources.csv`** — the 209 references deduplicated to 43 unique sources, each
classified by kind.

## The first analysis someone should run

`human_research_score` is the wiki's own guess at how much human evidence a
compound has. `pephack.pubmed.species_breakdown()` gives you the real count of
human-indexed records and randomised trials. Correlate them.

```python
from pephack import pubmed
from pephack.compounds import by_name
# wiki says BPC-157 human research = 2/10, semaglutide = 9/10, epitalon = 1/10
print(pubmed.species_breakdown("BPC-157"))
```

Where the self-ratings track reality, the community's instincts are good. Where
they diverge is the interesting part, and it is a scatter plot you can put on
screen before lunch.

## What is deliberately not here

Dosing strings and stack protocols. They exist in the source data and they are
part of what gets claimed, but this repo grades evidence and does not publish
protocols. Teams working the evidence tracks do not need them; the claim
"typical dose is X, all vibes-based, zero published combination data" is
auditable from its second half alone.
