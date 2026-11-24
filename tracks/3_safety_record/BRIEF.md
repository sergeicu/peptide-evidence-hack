# Track 3 — Safety record

**Build:** an agent that pulls adverse event reports and case reports for
compounds that were never approved, and says what has actually been reported
rather than what people assume.

```bash
python -m pip install -e ".[dev]"

python tracks/3_safety_record/run.py --out out/safety.json
python tracks/3_safety_record/solution.py --compound "Melanotan II"
```

## Read this before you write a line, or your output will be harmful

FAERS is a spontaneous reporting system.

- A report is not proof the drug caused the event.
- Reporting is voluntary; one case can appear more than once.
- **Counts are not rates.** The exposed population is unknown, so there is
  nothing to divide by.
- For compounds that were never approved there are almost no reports, because
  the reporting pathway barely exists for something bought from a website.
  **That absence is not safety.** A card printing a bare `0` beside a
  gray-market compound is worse than printing nothing at all.

`openfda.summarise()` attaches those caveats to its own output. Keep them
attached to yours.

## Where the real signal is

- **Case reports in PubMed.** `Case Reports[Publication Type]` surfaces
  published harms that never reach FAERS. For several of these compounds it is
  the only human safety literature in existence.
- **The approved cousin.** Melanotan II versus bremelanotide; sermorelin versus
  tesamorelin. An approved analogue has a label listing real adverse effects,
  and that is often the best available guide to what the unapproved one does.
- **Why something was dropped.** Sermorelin was an approved US product and
  isn't now. Ipamorelin went into industry development and came out. Those
  decisions are documented.

## Regulatory status moves

BPC-157 went into FDA 503A Category 2 in September 2023 and came out in April
2026, and coming out is not the same as being permitted. If your card prints a
status it prints the document and the date. The `status_hypothesis` column in
`data/compounds.csv` is explicitly a guess — correcting it against the FDA
record is task zero.

See `README.md`.
