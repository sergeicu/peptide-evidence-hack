# Track 3 — Safety record

**Deliverable:** what has actually been reported for a compound, versus what
people assume.

```bash
python tracks/3_safety_record/run.py --out out/safety.json
```

## Read this first or your output will be actively harmful

FAERS is a spontaneous reporting system.

- A report is not proof the drug caused the event.
- Reporting is voluntary and the same case can appear more than once.
- **Counts are not rates.** Nobody knows the exposed population, so there is
  nothing to divide by.
- For compounds that were never approved, there are very few reports, because
  the reporting pathway barely exists for something bought from a website.
  **That absence is not safety.** A card that prints a bare `0` next to a
  gray-market compound is worse than printing nothing.

`openfda.summarise()` attaches these caveats to its output. Keep them attached.

## Where the actual signal is

- **Case reports in PubMed.** `Case Reports[Publication Type]` finds published
  harms that never reach FAERS. For several compounds this is the only human
  safety literature that exists.
- **Comparison with the approved cousin.** Melanotan II versus bremelanotide,
  sermorelin versus tesamorelin. An approved analogue has a label listing real
  adverse effects, and that is often the best available guide to what the
  unapproved one does.
- **Why something was withdrawn or dropped.** Sermorelin was an approved US
  product and is not any more. Ipamorelin went into industry development and
  came out. Those decisions are documented.

## Regulatory status is a moving target

BPC-157 was placed in FDA 503A Category 2 in September 2023 and removed from
Category 2 in April 2026, and removal is not the same as being permitted. If
your card prints a status it has to print the document and the date it came
from. `data/compounds.csv` has a `status_hypothesis` column that is explicitly
a guess — correcting it against the FDA record is task zero.
