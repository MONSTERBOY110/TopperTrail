# Findings from the recorded run (5 October 2026)

Every number below is printed by `toppertrail analyze` on the recorded run committed in `fixtures/`. Replay it with no API key (`TOPPERTRAIL_REPLAY=1`, see the README) and the same ledgers come out, hash for hash. Counts are lower bounds: 46 institutes are registered, a mention counts as a claim only when it ties the topper to the institute, and pages that render only in JavaScript fall back to the search snippet.

A claim recorded here is a claim observed, not a finding against anyone. Only the CCPA decides whether an advertisement is misleading.

## UPSC Civil Services Examination 2025, top 20 ranks

| Measure | Value |
|---|---|
| Claims recorded | 266, by 20 institutes |
| Institutes claiming AIR 1 | 7: ALLEN Career Institute, Legacy IAS Academy, NEXT IAS, Physics Wallah, Sriram's IAS, Unacademy, Vajiram & Ravi |
| Top-20 ranks claimed by at least 3 institutes | 20 of 20 (average 5.0 institutes per rank) |
| Claims that name a course next to the claim | 184 of 266 (69%) |
| Of those, claims that name only an interview programme | 72 of 184 (39%) |
| Claims that say whether the course was paid or free | 1% |
| Paid Google ads in India (Ads Transparency Center) naming a top-20 topper | 3, all Vision IAS, all naming AIR 5 |

Institutes with the most claims:

| Institute | Toppers claimed | Claims | Claims naming only an interview programme |
|---|---|---|---|
| Vajiram & Ravi | 18 | 47 | 29 |
| Vision IAS | 15 | 81 | 1 |
| NEXT IAS | 15 | 42 | 13 |
| ForumIAS | 11 | 32 | 10 |
| Physics Wallah | 9 | 11 | 2 |
| Unacademy | 7 | 10 | 8 |

Vajiram & Ravi lists AIR 1 on its selections page as "Anuj Agnihotri AIR 1 - UPSC CSE 2025 (IGP)", and its congratulation poster names the Interview Guidance Programme. In May 2026 the CCPA fined the same institute Rs 7 lakh over "8 Rank Holders in the Top 10" for CSE 2023, finding that seven of the eight had only attended its free Interview Guidance Programme.

**The toppers' own words.** For each topper, TopperTrail reads one independent interview's captions (Hindi or English). Of the 266 claims, the claiming institute is mentioned by the topper for 8 and not mentioned for 165; for 7 more, the topper's line about that institute is marked "words to check" (a negation near the institute's name, which automatic captions often mangle). 86 claims concern toppers with no independent interview transcript. Every line links to its timestamp.

**Google AI Mode.** Asked how each topper prepared, AI Mode named a coaching institute for 20 of 20 toppers. In 20 cases the institute it named has, for that topper, only interview-programme claims or claims the topper's interview does not mention; in 5 cases it named an institute with no claim found at all.

**Wording in the institutes' own material.** Count claims ("X of the top Y", TT-11): 22. Unsubstantiated superlatives (TT-09): 21. Guarantee wording (TT-10): 1.

## JEE Advanced 2026 and NEET UG 2026, top 5 ranks (light scope)

| Exam | Claims | Institutes | Course named next to the claim |
|---|---|---|---|
| JEE Advanced 2026 | 16 (ALLEN 14, Narayana 2) | 2 | 7 of 16 (44%) |
| NEET UG 2026 | 6 (ALLEN 4, Aakash 2) | 2 | 0 of 6 |

Engineering and medical claims sit mostly on the institutes' own YouTube channels ("Meet AIR 1"), and none of them says whether the course was paid or free.

## What the run cost

189 SerpApi searches across the three exams (UPSC 141 of the 145 planned, JEE 24, NEET 24); the account was charged 184 credits of the free plan's 250 a month. The run is stored as 756 scrubbed fixture files (6.1 MB on disk) so it replays without a key.
