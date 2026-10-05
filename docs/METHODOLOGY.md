# Methodology

TopperTrail turns public search results into a ledger of coaching institutes' "our topper" claims. Every verdict is a fixed rule with a named basis. No AI model is used anywhere in the pipeline, so the same evidence always produces the same ledger and the same hash.

## 1. Inputs that are fixed before any search

- Official result lists: UPSC CSE 2025 (06.03.2026), JEE Advanced 2026 (01.06.2026), NEET UG 2026 re-exam (16.07.2026), in `toppertrail/data/results/`.
- A registry of 46 institutes with their domains, YouTube channel IDs and handles, English and Devanagari aliases, the exams they serve, and their CCPA orders (`toppertrail/data/institutes.yaml`). Vajiram & Ravi and Vajirao & Reddy are separate entries, as are Khan Study Group and Khan Global Studies.
- A lexicon of course types, vague labels, paid or free wording, durations, superlatives, guarantees and count claims, in English and Hindi (`toppertrail/data/lexicon.yaml`).
- The verbatim text of the CCPA coaching guidelines and the 33 coaching orders used for validation (`toppertrail/data/ccpa/`).

## 2. Collection (SerpApi)

For each topper: Google web results (English, plus Hindi for the top 10 UPSC ranks), Google Images, YouTube search, Google AI Mode; for the top 10 UPSC ranks the full description of up to two institute-hosted videos; for every UPSC topper the transcript of one independent interview. For each institute with an ad domain: the Google Ads Transparency Center in region India since the result date. `toppertrail estimate` prints the credit cost per engine before anything is spent; `collect` refuses to start when the estimate is above the cap or the account's remaining searches.

Pages on registered institute domains are fetched once, politely (robots.txt, one request per second per host, 2 MB cap). Navigation, menus, headers, footers and scripts are dropped; the rest is split into text blocks. Only blocks that name a roster topper or carry a signal phrase are kept, with their neighbours, plus the SHA-256 of the original HTML. Poster and ad images can be read with optional local OCR; images are never stored.

Every response is scrubbed of account URLs and the API key, trimmed to the fields the rules use, and stored in a content-addressed evidence store. The run manifest's root hash covers every artifact.

## 3. What counts as a claim

- Only sources an institute controls: a registered domain, a registered YouTube channel, or that institute's own Google ads.
- The exam and year must appear near the name, so "Shubham Kumar" (JEE Advanced 2026 CRL 1) is never matched to the UPSC CSE 2020 AIR 1 of the same name.
- A page mention is a claim only when it ties the topper to the institute: an association word ("our student", "congratulations", "alumni", "associated with", "student of", "joined", "enrolled"), a named course, the institute's own name beside the topper, or a results-style page address ("selections", "our results", "hall of fame"). Institute blogs that list the official toppers as news are recorded as "named without claiming the topper" and are not counted.
- Videos on the institute's own channel, its posters and its ads always count: publishing them is the association.

The claim window is the text block containing the name, plus a neighbouring block only when that neighbour names no other topper. A course named in a menu or elsewhere on the page does not count; CCPA's directions require the course "on the same page and in immediate proximity to such claims".

## 4. The topper's own words

One independent interview is chosen per topper: a listed media channel first, otherwise the longest video whose title names the topper and whose channel is not an institute, never a mock interview. Its captions are read for lines that name an institute or a course. A line counts as the topper's own statement only when it is in the first person within 15 seconds, so a sponsor message read at the start of a video is never attributed to the topper. A line with a negation in it or the next caption is marked as a negative.

For each claim the status is one of:
- mentioned: the topper names this institute;
- words to check: a negative line about the course this claim names, with no affirmation of that course elsewhere (shown with the quote and timestamp, because automatic captions can be wrong);
- not mentioned;
- no independent interview found.

## 5. Rules

| Rule | Records | Basis |
|---|---|---|
| TT-01 | Course not stated next to the claim | Guidelines 2024, cl. 4(1)(a); CCPA directions, NEXT IAS order 07.09.2026 |
| TT-02 | Interview-only programme | CCPA findings in the Vajiram & Ravi, KSG, Chahal, Drishti and StudyIQ orders |
| TT-03 | Vague course label | CCPA order against Career Line Coaching, Sikar, 09.04.2026 |
| TT-04 | Paid or free not stated | Guidelines 2024, cl. 4(1)(a) |
| TT-05 | Course duration not stated | Guidelines 2024, cl. 4(1)(a) |
| TT-06 | Different course labels across the institute's own sources | Guidelines 2024, cl. 4(1)(e) |
| TT-07 | Selective disclosure on one page | CCPA orders against Vision IAS (18.12.2025) and Narayana (11.06.2026) |
| TT-08 | Rank differs from the official result | Guidelines 2024, cl. 3(b); CCPA order against Narayana (11.06.2026) |
| TT-09 | Unsubstantiated superlative | 2022 Guidelines, cl. 12(a); CCPA orders against Chahal, Rau's and Sriram's |
| TT-10 | Guarantee language | Guidelines 2024, cl. 3(c); CCPA orders against Motion and StudyIQ |
| TT-11 | Aggregate count claim | Guidelines 2024, cl. 3(b) |
| TT-12 | Topper's own words | Independent interview transcript |
| TT-13 | Claimed for a different exam | Informational |
| TT-14 | Featured in a paid Google ad in India | Google Ads Transparency Center |

Flags describe disclosure. They never say a claim is false; that judgement belongs to the CCPA.

## 6. Limits

- Counts are lower bounds: unregistered institutes and pages without an association word are not counted.
- Pages that render only in JavaScript fall back to the search snippet, labelled "snippet only".
- OCR reads English only; Hindi text inside images is not read.
- Automatic captions mangle names and negations; every own-words line links to its timestamp.
- Findings are as observed on the collection date shown on each claim.
