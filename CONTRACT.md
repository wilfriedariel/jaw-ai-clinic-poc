# PoC contract: lead temperature + ad audience agents (S Aesthetics Clinic)

Written BEFORE running `pipeline.py`. Context: Aaron/Joyce chat 2026-10-18, deck "S Aesthetics Clinic - AI Transformation Proposal".

## What this PoC is
Two agents on **synthetic** clinic data (Plato-shaped patients + WhatsApp/ad leads):
1. **Temperature agent**: scores every contact hot/warm/cold with a transparent reason list (rules-first, deck slide 6).
2. **Audience agent**: from converters, ranks ad segments by lift, builds a lookalike seed and a suppression list. Consent gates all of it (deck slides 12-13).

Nothing is sent to anyone. Human approves every action.

## What it can and cannot prove
- Synthetic outcomes come from a hidden intent variable the rules never see. The test shows the **mechanics work and the rules are not trivially circular**. It does **not** show predictive validity on real clinic data. Real validity needs the de-identified Plato export (deck slide 22) and a forward test.
- Cost-per-lead by source is an **assumed** input, not measured.

## Pre-registered thresholds (holdout = 30%, seed 7)
| Check | Pass | Else |
|---|---|---|
| Rules score AUC on holdout | >= 0.68 | KILL rules, rewrite |
| Hot tier conversion / Cold tier conversion | >= 4x | KILL rules |
| Fitted logistic AUC minus rules AUC | reported, no threshold (tells how much "scoring later" could add) | n/a |
| Audience: top segment lower-bound lift (Wilson, n>=40) | > 1.0 | report "no usable segment" |
| Consent leak: any non-consented contact in seed or retarget list | 0 | FAIL |
| Run-to-run determinism (same seed, same output hash) | identical | FAIL |

Results are written to `results.json` by the script, not copied by hand.

## Amendment v2 (2026-10-21, after seeing v1 results; thresholds unchanged)
v1 FAILED two gates (`results_v1_FAILED.json`): rules AUC 0.600, hot/cold 1.80x. Patient-only AUC was 0.42, below chance.
Cause, from a groupby on the generator output: patients with `next_booking` convert 42.3% vs 30.5% without. v1 penalised them (-10) while the outcome ("rebooks within 30d") counted them as converted. That is a target-definition defect, not a weak model.
Fix: patients who already have a booking are removed from the outreach list and from evaluation; the two booking rules are deleted. No other rule, weight, threshold or seed changed. This is the only fix round; if v2 still fails, the result stands.
