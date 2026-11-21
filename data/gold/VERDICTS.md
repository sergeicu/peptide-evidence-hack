# Verdict vocabulary

Every gold item and every submission uses exactly one of these.

| verdict | means |
|---|---|
| `rct_supported` | At least one randomised controlled trial in humans supports the claim. |
| `human_uncontrolled` | Human data exists but it is uncontrolled: open-label, case series, case reports. |
| `animal_only` | Evidence exists but only in animals or in vitro. |
| `contradicted` | Human evidence exists and does not support the claim, including trials that missed their endpoint. |
| `no_evidence_found` | Nothing located that bears on the claim. |
| `not_a_factual_claim` | The claim is too vague to evaluate as stated, e.g. "supports recovery". |

`not_a_factual_claim` is not an escape hatch, it is a real category. A large
share of what gets said about these compounds cannot be checked as written, and
a system that cannot say so will instead invent a verdict.

## Why the controls matter

`no_evidence_found` is the single most common correct answer in this domain,
which means an agent that always answers `no_evidence_found` scores well on
accuracy while being useless. The scorer computes that baseline for you and
prints it next to your score. Beat it on macro F1, not on accuracy.

The gold set deliberately includes claims about approved drugs where the
correct verdict is `rct_supported`, and one compound that failed its human
trials where the correct verdict is `contradicted`.
