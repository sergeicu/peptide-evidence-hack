.PHONY: install smoke test card claims lint

install:
	python -m pip install -e ".[dev]"

# Hit every public API once. Run this first thing on hack day.
smoke:
	python scripts/smoke_test.py

test:
	python -m pytest tests -q

# Build an evidence card for one compound, e.g. make card C=BPC-157
card:
	python tracks/1_evidence_graph/run.py --compound "$(C)" --out out/

# Score a claim-to-source submission, e.g. make claims S=out/submission.jsonl
claims:
	python -m pephack.scoring.claims --submission "$(S)" --gold data/gold/claims.jsonl
