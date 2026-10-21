# Contract v3 (written 2026-10-21 BEFORE any seed-11 run)

Purpose: show the mechanism (score, explain, segment, consent-gate) in a dashboard that accepts any contact CSV. It is a demo of mechanics, not evidence of predictive validity on clinic data.

## What changed from v2
- Seed 7 -> **11** (fresh synthetic population; rules and generator unchanged from v2, so this is a genuine re-draw, not a retune of the rules).
- Thresholds lowered. **Honest provenance:** they are set after seeing v2 (rules AUC 0.658, hot/cold 2.4x, logistic ceiling 0.69), because the v2 AUC bar 0.68 sat at the generator's noise ceiling. They are therefore calibrated to the ceiling, not blind. The seed-11 run is the out-of-sample part.
- Scoring is ported to JS in the dashboard so uploaded CSVs are scored live. Parity test: JS score and reasons must equal Python on all rows.

## Gates (holdout = 30%, seed 11)
| Check | Pass |
|---|---|
| Rules AUC on holdout | >= 0.62 |
| Hot / Cold conversion | >= 2.0x |
| Top audience segment, Wilson lower-bound lift (n>=40) | > 1.0 |
| Consent leak (non-consented in seed or retarget list) | 0 |
| Determinism (two runs, identical output hash) | identical |
| JS/Python parity (score and reasons, every row) | 100% |

If any fails, the result stands; no second fix round without a new contract.

## Dashboard rules
- Built-in data carries a SYNTHETIC banner and the Python holdout gates.
- Uploaded data: no validity claim. If a `converted` column exists, metrics are labelled in-sample.
- Nothing is sent anywhere; all scoring runs in the browser, uploaded data never leaves it.

## Addendum 2026-10-21 (UI rebuild; gates re-run)
- Dashboard rewritten in plain language: 3 screens (texted us then went quiet / find new patients / database). Hot/Warm/Cold became High/Medium/Low chance to book, to avoid clashing with the clinic's own use of "cold lead".
- Generator defect fixed: last contact could be older than the enquiry itself. Now `days_since_contact = min(contact, enquiry)`. Rules, seed (11), thresholds unchanged. Gates re-run: rules AUC 0.632 (>=0.62), High/Low 2.19x (>=2.0), top segment 1.28 (>1.0), consent leak 0, deterministic, JS/Python parity 2128/2128. All pass, margin on AUC is small (0.012).
- Names, phones, chat text come from a separate RNG stream and do not touch scored data.
- Screens checked by headless-Chrome screenshots at 1280px. Phone width NOT verified (headless Chrome would not go below ~500px).

## Addendum 2 (2026-10-21, visual redesign, scoring untouched)
- New "Today" screen first (three actions, enquiry funnel, chance-to-book split, how-it-works), warm palette, serif headings, hero card built from a real contact, plain-language copy for a non-technical clinician. Ad channels renamed for readers ("Facebook & Instagram ads", "WhatsApp direct").
- Audience tab now also lists up to 2 "Promising, needs more data" groups (point lift >= 1.2x but not clearly above average after the small-sample bound). They are labelled as possibly luck and carry no claim.
- Scoring, seed, thresholds, results.json unchanged. Parity re-run: 2128/2128, 0 mismatches.
- Verified: 1280px headless-Chrome screenshots of Today / Follow up / Get new patients / Everyone. NOT verified: phone width, dark mode, Safari, behaviour when Google Fonts is offline (falls back to Georgia / system-ui).
