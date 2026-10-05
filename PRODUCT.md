# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary: SerpApi hackathon judges and journalists checking how Indian coaching institutes claim exam toppers. They arrive with a question ("who claims AIR 1, and on what basis?") and need to verify every claim back to its source in seconds.

Secondary (confirmed audience, not the lead): aspirants and parents choosing a coaching institute before paying Rs 1 to 3 lakh, and CCPA or consumer-group investigators who need citable evidence.

## Product Purpose

TopperTrail collects public "our topper" claims made by coaching institutes on their own websites, posters, YouTube channels and Google ads in India, checks each claim with fixed rules grounded in the CCPA Guidelines for Prevention of Misleading Advertisement in Coaching Sector, 2024 and CCPA's orders, compares claims with the topper's own words in independent interviews, and records what Google AI Mode says. Success: a reader can see the headline finding, open any topper or institute, and trace every flag to a dated source and a SerpApi search ID.

## Positioning

One rank, many claims. TopperTrail assembles, per exam, every institute claim about the same official topper and sets it against the official result list, the disclosure rules CCPA enforces, and the topper's own words. No model decides anything; every verdict is a named rule with a clause reference.

## Operating Context

- Runs locally (`toppertrail serve`) from a recorded evidence store, or as an exported static site; judges replay it with no API key.
- Exams in scope: UPSC CSE 2025 (top 20, deep), JEE Advanced 2026 and NEET UG 2026 (top 5 each, light).
- Sources are institute-controlled only: registered domains, registered YouTube channels, the institute's own Google ads (region India).
- Demo video under 3 minutes is recorded from this dashboard.

## Capabilities and Constraints

- Pages: exam list, exam overview with headline numbers, topper ledger, institute scorecard, methodology (rules + verbatim clauses), evidence viewer (raw JSON with integrity check).
- Server-rendered Jinja2 with autoescape; no JavaScript build step; all fetched text is untrusted and escaped.
- Must render Devanagari (Hindi transcript quotes, Hindi institute text) and work at 360 px width.
- Counts are lower bounds: only registered institutes are counted.
- Static export hides the evidence viewer links (evidence lives in the local store).

## Brand Commitments

- Name: TopperTrail. Tagline: "One rank. Many claims. Follow the trail."
- No existing logo, colours or fonts; the visual identity is open.
- Voice: neutral and factual. Flags say "not stated", "differs", "not mentioned"; never "false", "fake", "fraud", "lie" or "misleading" about a claim. The fixed notice appears on every page: TopperTrail records claims and disclosures; only the CCPA decides what is misleading.
- No em dashes or en dashes in UI copy.

## Evidence on Hand

- Official result lists (UPSC CSE 2025, JEE Advanced 2026, NEET UG 2026) in `toppertrail/data/results/`.
- 33 CCPA coaching orders with verbatim claim texts and penalties in `toppertrail/data/ccpa/orders.yaml`; verbatim guideline clauses in `toppertrail/data/ccpa/guidelines-2024.md`.
- Validation results in `docs/VALIDATION.md`.
- Live ledgers do not exist yet (recorded runs pending the owner's SerpApi key). Do not fabricate findings, counts, quotes or screenshots of data that has not been collected.

## Product Principles

1. Evidence before interpretation: every number links down to a claim, every claim to its source, search ID and snapshot.
2. Describe disclosure, never judge truth.
3. The official record is the reference point; claims are measured against it.
4. Honest about limits: lower bounds, snippet-only pages, auto-caption errors are shown, not hidden.

## Accessibility & Inclusion

- Readable at 360 px; keyboard focus visible; sufficient contrast.
- Mixed English and Hindi (Devanagari) text must render with an appropriate font fallback.
