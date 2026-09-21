# Phase 22 — Blinded manual read: ANSWER KEY

**Do not open until both readers have submitted.** This file maps packet
report numbers to their version and uid. It is deliberately a separate
file from reader_packet.md.

Seed: `20260921` (frozen §6.4). 20 uids sampled, both versions of
each, pooled and shuffled.

Sampled uids: 345, 429, 663, 740, 1608, 1770, 1776, 2045, 2288, 2417, 2427, 2475, 2507, 2575, 3462, 3469, 3735, 3841, 3846, 3947

| Report | Version | uid |
|---|---|---|
| 01 | v1.1 | 3947 |
| 02 | v1.2 | 3462 |
| 03 | v1.1 | 2507 |
| 04 | v1.1 | 1770 |
| 05 | v1.1 | 2575 |
| 06 | v1.2 | 740 |
| 07 | v1.2 | 429 |
| 08 | v1.2 | 663 |
| 09 | v1.1 | 3462 |
| 10 | v1.2 | 3735 |
| 11 | v1.1 | 345 |
| 12 | v1.1 | 3469 |
| 13 | v1.2 | 1770 |
| 14 | v1.2 | 1608 |
| 15 | v1.1 | 429 |
| 16 | v1.1 | 3841 |
| 17 | v1.2 | 2045 |
| 18 | v1.2 | 2427 |
| 19 | v1.1 | 740 |
| 20 | v1.1 | 1608 |
| 21 | v1.2 | 2475 |
| 22 | v1.2 | 1776 |
| 23 | v1.2 | 2417 |
| 24 | v1.2 | 3841 |
| 25 | v1.2 | 3947 |
| 26 | v1.1 | 2427 |
| 27 | v1.1 | 2288 |
| 28 | v1.2 | 3469 |
| 29 | v1.1 | 2475 |
| 30 | v1.2 | 2288 |
| 31 | v1.1 | 2045 |
| 32 | v1.1 | 2417 |
| 33 | v1.2 | 2575 |
| 34 | v1.2 | 3846 |
| 35 | v1.1 | 3735 |
| 36 | v1.2 | 345 |
| 37 | v1.1 | 1776 |
| 38 | v1.1 | 3846 |
| 39 | v1.2 | 2507 |
| 40 | v1.1 | 663 |

## Scoring rule (frozen §6.4)

Report **raw agreement** between the two readers per question, as a count
out of 40. No kappa: at n=40 with a low expected base rate it is unstable
and would imply more precision than two readers on forty reports supply.
List disagreements individually with both verdicts rather than resolving
them into a consensus label.

**Stop condition:** a single clear grounding failure in the v1.2 half,
agreed by both readers, is grounds to withhold adoption pending review,
regardless of every automated endpoint passing.