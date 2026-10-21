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

## Addendum 3 (2026-10-21, "Quick answers" screen, requested by Joyce; scoring untouched)
- New screen between Today and Follow up: every open enquiry whose last message is theirs gets the question it asked, a suggested answer, and Send / Edit per person, plus tick boxes, Select all and "Send selected" (with a confirm step).
- Rules, not a model: a keyword table maps the last message to price / slot / downtime / info / "let me think" (answerable) or promo / other (kept for a person, no draft). Misses fail safe to "needs a person".
- Drafts never state a price, a time slot or a number. Price questions point to a consultation with Dr Cheak.
- "Send" is simulated on practice data (marked sent, nothing leaves). On uploaded data it copies the text, because WhatsApp is not connected. Nothing is sent without a tick or a click and, for batches, a confirm.
- Pre-registered checks, added to `parity_test.js`: intent table matches on 9 fixed strings; ready + needs-a-person equals the open waiting list exactly; no ready draft contains a digit or a currency sign; no needs-a-person item has a draft; both groups non-empty on the practice data. Result on this run: waiting 136 = ready 112 + person 24, 0 numeric drafts, 0 mismatches.
- NOT verified: that the keyword table recognises real clinic chats (the practice chats are generated from the same phrases, so recognition here is circular); the wording of answers by the clinic; real WhatsApp delivery.
- Scoring, seed, thresholds, results.json unchanged. Parity 2128/2128.

## Addendum 4 (2026-10-21, four requests from Joyce; scoring untouched)
1. **Clinic mark.** The proposal deck contains no logo image (checked: `ppt/media` is empty), only the text lockup "S AESTHETICS CLINIC / LASER & AESTHETICS" in Cambria with a terracotta tagline. The header now uses that lockup. It is the deck's wording, not a supplied brand file; a real logo file from the clinic is still needed.
2. **Helpdesk bot** (new tab). Answers only from the clinic's notes, quoting the matching sentences with the note's title. Rule-based word-stem scoring; no match = "I could not find this, I won't guess" and the question is listed as a gap. Clinic can load its own notes (.txt, blank-line separated). The 13 sample notes are made up for the demo (hours, 24h cancellation, 12-month packages are invented examples).
   - Pre-registered checks (`parity_test.js`): 8 fixed questions hit the intended note, 2 off-topic questions return nothing, uploaded notes parse and answer.
   - **Known failure, reported not gated:** "Can I take a photo of Dr Cheak?" is answered from "Booking a consultation" (matches "photo" and "Cheak" in a note about photo ID). Stem matching cannot tell the senses apart. Upgrade path: embedding search plus a quote-only LLM with a labelled question set.
3. **Trends** (new tab). Enquiries per day (30), week (8) and month, split booked / not booked yet, with waiting-for-reply count and a 7-day change. Check: buckets partition the leads exactly in all three views. Limit: practice data reaches back about six weeks, so Months shows two or three months; uploaded data fills more.
4. **Contact and WhatsApp shortcut** on every record: Follow up panel, record dialog, Quick answers card, Everyone table. Practice numbers are masked, so the link opens a blank WhatsApp chat with the message pre-filled; with real numbers it opens that patient's chat (8-digit Singapore numbers get +65). Link construction is unit-tested; opening a real WhatsApp chat was NOT tested.
- Nav: with seven tabs, only the selected tab shows its subtitle.
- Scoring, seed, thresholds, results.json unchanged. Parity 2128/2128.
