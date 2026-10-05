# TopperTrail: design spec

Date: 2026-10-05. Event: SerpApi India Hackathon 2026 (deadline 10 Oct 2026, 23:59 IST).
Track: 5, Knowledge & Public Interest. Builder: solo lead (owner commits and pushes; Claude Code writes code, never commits).

Tagline: **One rank. Many claims. Follow the trail.**

## 1. The insight

Every UPSC, JEE and NEET result day, coaching institutes race to put the same toppers on their posters, pages, ads and YouTube channels. Parents and aspirants pay Rs 1 to 3 lakh on the strength of those claims. The Central Consumer Protection Authority (CCPA) has now issued 60+ notices and more than Rs 1.46 crore in penalties, and its orders keep finding the same pattern: the "topper" took only a free interview programme, a test series, or nothing at all, and the advertisement did not say so.

CCPA finds this one institute at a time, months later, by demanding enrolment forms. But most of the evidence is public on result day, scattered across search results, image results, YouTube videos, transcripts and Google's ad archive. Nobody assembles it. That is a search problem, and SerpApi is the only practical way to read all of those surfaces with one key.

Ground truth that the idea is real (all verified, sources in section 12):
- UPSC CSE 2025 AIR 1 Anuj Agnihotri is associated with at least 12 organisations. In his own Hindi interview he says he took no coaching after Unacademy, gave mock interviews at NEXT IAS and PW, and never joined a test series.
- AIR 3 Akansh Dhull: "मतलब मैंने ऑलमोस्ट हर इंस्टट्यूट से कुछ ना कुछ ले लिया" ("I took something or other from almost every institute").
- CCPA fined Vajiram & Ravi Rs 7 lakh (29 May 2026) for "8 Rank Holders in the Top 10"; 7 of the 8 took only the free Interview Guidance Programme. Vision IAS Rs 11 lakh (Dec 2025, repeat offence). Motion Education Rs 10 lakh (Apr 2026, JEE/NEET).

## 2. Users and success criteria

Primary users:
1. Aspirant or parent choosing a coaching institute: "Before I pay, what does this institute actually disclose about its toppers?"
2. Journalist, consumer group or CCPA investigator: "Give me every public claim on this exam's toppers, with evidence I can cite."

Hackathon success means scoring well on all five published criteria:

| Criterion | How TopperTrail answers it |
|---|---|
| Idea strength | A crisp, verifiable insight backed by CCPA orders and a quantified headline finding |
| Originality | No existing tool or hackathon entry does this (GitHub search "topper serpapi" = 0); first public use of transcripts + Ads Transparency + AI Mode together for consumer protection |
| Technical complexity | Multi-engine collection with budget control, evidence store with hash manifest, entity resolution in English and Hindi, OCR, a deterministic rule engine validated against 33 CCPA orders |
| Usefulness | Institute scorecards for parents, evidence packs for complaints, reproducible exam-wide ledgers |
| Meaningful SerpApi usage | 8 engines are load-bearing; without SerpApi there is no data (section 6 table) |

Measurable targets for submission:
- UPSC CSE 2025 top 20 fully processed; JEE Advanced 2026 and NEET UG 2026 top 5 each processed (light).
- Rule engine reproduces CCPA's findings on the claim texts of the 33 coaching orders (report precision and recall, no hand-tuning after the frozen set is scored).
- Replay mode: a judge with no API key runs `collect`, `analyze` and `serve` and gets the identical ledger (same manifest hash) as the recorded run.
- Total SerpApi spend for the full recorded run at most 230 credits (free plan is 250 per month).

## 3. Scope

In scope (v1):
- Exams: UPSC CSE 2025 (deep, top 20), JEE Advanced 2026 and NEET UG 2026 (light, top 5 each).
- Sources: Google web results (en, plus hi for top 10), Google Images, YouTube search, YouTube video details, YouTube transcripts, Google Ads Transparency Center (region India), Google AI Mode, and page snapshots fetched from result URLs.
- CLI, local dashboard, static export, replay mode, evidence pack export.
- Rule engine with CCPA clause references, English and Hindi lexicons.

Out of scope (v1), stated honestly in the README:
- Headless browser rendering for JavaScript-only pages (they fall back to the search snippet, labelled "snippet only").
- OCR of Hindi or Devanagari text inside images (English OCR only).
- Instagram and Facebook posts.
- Any judgement that a claim is false. TopperTrail records claims and disclosures; only CCPA decides what is misleading.
- Any LLM. No model is used anywhere in the pipeline.

## 4. Ground-truth inputs shipped in the repo

All under `data/`, each with source URL, retrieval date and SHA-256 of the original file:
- `data/results/upsc-cse-2025.csv` (rank, name, roll no) from the official UPSC PDF (declared 06.03.2026). Same for CSE 2024 and 2023 (used by tests and the CCPA validation).
- `data/results/jee-adv-2026.csv` (CRL 1 to 10, from the IIT Roorkee press release) and `data/results/neet-ug-2026.csv` (AIR 1 to 10, re-exam result of 16.07.2026).
- `data/ccpa/guidelines-2024.md`: verbatim clauses of the Guidelines for Prevention of Misleading Advertisement in Coaching Sector, 2024, plus the cited clauses of the 2022 guidelines and section 2(28) of the Consumer Protection Act, 2019.
- `data/ccpa/orders.yaml`: the 33 coaching success-claim orders (institute, exam, verbatim claim text, CCPA finding, penalty, order URL, PIB URL).
- `data/institutes.yaml`: registry of institutes (canonical name, legal entity, domains, YouTube channel IDs and handles, English and Devanagari aliases, exams served, CCPA orders). Vajiram & Ravi and Vajirao & Reddy are separate entries. Khan Study Group and Khan Global Studies are separate entries.
- `data/lexicon.yaml`: course types (en, hi), interview-only programme terms, vague labels, superlatives, guarantee phrases, paid/free and duration patterns, negation phrases for self-reports.

## 5. Architecture

A single Python package, `toppertrail`, Python 3.11+, installable with `pip install -e .`. Each module has one job and a narrow interface. (Revised 2026-10-05 while planning: a canonical JSON ledger replaces SQLite, and page snapshots keep relevant text blocks plus the HTML hash rather than raw HTML.)

```
toppertrail/
  cli.py            Typer CLI: version, estimate, collect, analyze, verify, budget, validate, serve, export
  config.py         Settings from env/.env (SERPAPI_API_KEY, TOPPERTRAIL_REPLAY, home, fixtures, budget cap)
  hashing.py        SHA-256 helpers and canonical JSON
  models.py         Exam, Topper, Institute, Claim, Signal, SelfReport, Interview, AIAnswer, Flag
  data.py           Loads exams, official rosters, the institute registry and independent channels
  evidence.py       Content-addressed evidence store, run manifest and root hash, integrity check
  serp/
    base.py         SerpClient protocol, canonical params, key redaction, scrubbing, field trimming
    live.py         Official `serpapi` SDK; 429 + Retry-After; key never leaks; Account API check
    replay.py       Reads recorded responses keyed by canonical params hash; no network
    budget.py       Credit cap and spend log
  fetch/
    pages.py        Polite page snapshots (robots.txt, 1 req/s/host, size cap) and menu-free text blocks
    images.py       Image download + optional RapidOCR, and replay reader
  extract/
    text.py         Normalisation (case, Unicode, Devanagari nukta), tolerant name matching, context
    courses.py      Lexicon: course types, vague labels, paid/free, duration, superlatives, guarantees, counts
    claims.py       Turns institute-controlled text blocks into claims and institute signals
    selfreport.py   Independent interview pick, topper's own statements, own-words status
    aianswer.py     Institute attributions in AI Mode answers
  rules.py          TT-01..TT-14 with clause references; CCPA order suite scoring
  collect.py        Query plan, credit estimate, collector, fixture export
  analyze.py        Evidence to ledger; ledger hash
  report.py         Headline numbers, topper and institute views, AI Mode findings
  web/              FastAPI + Jinja2 dashboard (autoescape on), static export, CSS
  data/             Ground truth (section 4) shipped inside the package
tests/              pytest; offline only
fixtures/           Recorded, trimmed, scrubbed evidence for replay, plus manifests per exam
docs/               Spec, plan, validation, methodology, findings, demo script, submission text
```

### Ledger (canonical JSON, one file per exam)

- `toppers[]`: rank, official name, display name
- `claims[]`: claim_id, exam, rank, institute_id, source_type (web_page, snippet_only, poster, ad_creative, youtube_hosted, youtube_description), url, title, window, course_types, course_terms, paid_free_stated, duration_stated, vague_label, claimed_rank, search_id, evidence (SHA-256 list), observed_at
- `signals[]`: institute-level superlative, guarantee and count phrases with source
- `selfreports[]`, `interviews[]`: the topper's own statements with timestamps and polarity
- `ai_answers[]`: institutes named by AI Mode, excerpt, search_id
- `flags[]`: rule_id, institute_id, claim_id, rank, detail, code
- `unresolved[]`, `missing[]`: transparency about what could not be resolved or collected
- `manifest_root`: root hash of the evidence run; the ledger itself is hashed with canonical JSON

## 6. SerpApi usage (why nothing else works)

| Engine | Params (typical) | Fields used | Why it is needed |
|---|---|---|---|
| `google` | `q="<Name>" UPSC 2025 AIR <r>`, `gl=in`, `hl=en` (and `hl=hi` for top 10), `num` default | organic_results link/title/snippet/date, inline_videos, top_stories | Finds institute pages and posts that claim the topper |
| `google_images` | `q="<Name>" AIR <r> UPSC 2025`, `gl=in` | images_results original, source, link, title | Congratulation posters, the main claim medium |
| `youtube` | `search_query="<Name> UPSC topper interview"`, `gl=in`, `hl=en` | video_results link, title, channel.link, published_date, length | Institute-hosted mock interviews and independent interviews; channel identifies the institute |
| `youtube_video` | `v=<id>` (top 2 institute videos per topper, top 10 only) | description | Full descriptions carry course claims ("Courses joined at ...") |
| `youtube_video_transcript` | `v=<id>`, `language_code=hi` or `en`, `type=asr` when needed | transcript[].snippet, start_ms | The topper's own words; nothing else exposes this at scale |
| `google_ads_transparency_center` | `text=<institute domain>`, `region=2356`, `start_date` = result date | ad_creatives image, format, first_shown, last_shown, advertiser | Paid ads that actually ran in India featuring toppers |
| `google_ai_mode` | `q="Which coaching did <Name> (UPSC CSE 2025 AIR <r>) join?"`, `gl=in`, `hl=en` | text_blocks, references | Shows whether Google's AI repeats institute claims as fact |
| Account API | none | plan_searches_left, this_hour_searches | Pre-run budget check (free, no credit) |

Every stored claim keeps the `search_metadata.id` of the SerpApi search that surfaced it.

### Credit plan (recorded demo run)

| Item | Credits |
|---|---|
| UPSC CSE 2025 top 20: google en 20, google hi 10, images 20, youtube 20, youtube_video 20, transcripts 20, ai_mode 20 | 130 |
| Ads Transparency: 15 UPSC institutes | 15 |
| JEE Adv + NEET top 5 each: google 10, images 10, youtube 10, ai_mode 10 | 40 |
| Ads Transparency: 8 JEE/NEET institutes | 8 |
| Live spike and development | 25 |
| **Total** | **218 of 250** |

`toppertrail estimate` prints this table for any chosen scope before spending. `collect` refuses to start if the estimate exceeds `plan_searches_left` or the configured cap, and stops cleanly at the cap. Identical requests within an hour hit SerpApi's free cache; the recorder never sets `no_cache`.

## 7. Pipeline

1. **Roster**: load the official result rows for the exam and top N.
2. **Plan**: build a deterministic, ordered query list (per topper, then per institute).
3. **Collect**: run each query through the SerpClient (live, record or replay). Store the raw JSON in the evidence store; record search_id and credit spend.
4. **Fetch**: for each result URL on a registered institute domain, fetch the page once (timeouts 10 s, max 2 MB, robots.txt respected, 1 request per second per host). Drop navigation, menus, headers, footers and scripts; split the rest into text blocks; keep only blocks that name a roster topper or carry a signal phrase, plus their neighbours, and the SHA-256 of the original HTML. On failure, mark the claim `snippet_only`.
5. **OCR** (optional extra): run on poster images from registered institute domains and on ad creatives; store OCR text keyed by image SHA-256. Replay fixtures include OCR output, so judges do not need OCR installed.
6. **Extract claims**: for every artifact, find mentions of the topper (normalised name match, tolerant of spacing and initials, exam and year required in the same window), resolve the institute (domain, channel ID, advertiser name, alias), and capture the text window around the mention. Hosted mock-interview videos become `youtube_hosted` claims with course type `mock_interview` unless the description states another course. A page mention counts as a claim only when the window ties the topper to the institute (an association word such as "our student", "congratulations", "alumni" or "associated with", a named course, the institute's own name, or a results-style URL); institute pages that list official toppers as news are recorded as "named without claiming the topper". Videos, posters and ads always count. (Added 2026-10-05 after running the pipeline on real saved pages.)
7. **Self-reports**: choose the topper's independent interview deterministically (longest video from a channel not in the institute registry whose title contains the topper's name). Fetch its transcript. Extract statements within a window of institute aliases or course words, with polarity from negation phrases ("कोई कोचिंग नहीं ली", "never joined", "जॉइन नहीं की").
8. **AI answers**: parse AI Mode text blocks for institute aliases near the topper's name.
9. **Rules**: apply TT-01 to TT-14 (section 8). Pure functions over stored data.
10. **Ledger and report**: write the canonical JSON ledger, compute aggregates, record the manifest root and ledger hash.

Analysis reads only stored evidence, so `analyze` is deterministic for a given evidence store.

## 8. Rule catalogue

Each rule outputs a flag with a plain-language detail and a clause reference. Flags describe disclosure, never truth.

| ID | Flag shown to users | Logic (deterministic) | Basis |
|---|---|---|---|
| TT-01 | Course not stated next to the claim | No course-type term in the claim window. Window = the text block containing the mention, plus an adjacent block only when that block names no other topper (pages); title plus OCR text (images); title plus description (videos); title plus snippet (snippet_only) | Guidelines 2024, 4(1)(a); CCPA directions in the Next IAS order (07.09.2026) |
| TT-02 | Interview-only programme | Every course type found is interview-only (IGP, mock interview, DAF analysis, personality test, Last Mile) | CCPA findings in Vajiram, KSG, Chahal, Drishti, StudyIQ orders |
| TT-03 | Vague course label | Label matches the vague-label list ("fresher", "With XII", "repeater", "our student", "from various courses") | CLC Sikar order (09.04.2026) |
| TT-04 | Paid or free not stated | No paid/free pattern in the window | Guidelines 2024, 4(1)(a) |
| TT-05 | Course duration not stated | No duration pattern in the window | Guidelines 2024, 4(1)(a) |
| TT-06 | Different course labels across the institute's own sources | Same institute, same topper, course-type sets disagree across its sources | Pattern seen in NEXT IAS pages vs video descriptions; Guidelines 4(1)(e) transparency |
| TT-07 | Selective disclosure on one page | On one page, course stated for some featured toppers and missing for others | Vision IAS and Narayana orders |
| TT-08 | Rank differs from the official result | Claimed rank for the named topper does not match the official list, or a category rank is shown as AIR | Guidelines 3(b); Narayana order; IITPK order |
| TT-09 | Unsubstantiated superlative | Superlative phrase ("Best", "No. 1", "India's top", "सर्वश्रेष्ठ") in the same artifact | 2022 Guidelines 12(a); Chahal, Rau's, Sriram's orders |
| TT-10 | Guarantee language | Guarantee phrase in English or Hindi ("guaranteed selection", "100% selection", "pakka", "है तो सिलेक्शन है") | Guidelines 2024, 3(c); Motion and StudyIQ orders |
| TT-11 | Aggregate count claim | "N in Top M", "N selections" pattern; recorded with the share of that institute's named claims that are interview-only | Guidelines 3(b); every UPSC order |
| TT-12 | Topper's own words | Status per claim: `mentioned` (topper names the institute), `denied` (explicit negative matching the claimed course type), `not_mentioned`, `no_interview_found` | Topper's independent interview transcript |
| TT-13 | Claimed by an institute for a different exam | Institute registry exams do not include this exam (e.g. a NEET coaching claiming a UPSC topper) | Informational |
| TT-14 | Featured in a paid Google ad in India | Ad creative OCR text names the topper, shown after the result date | Informational; raises visibility of the claim |

Headline numbers (exact definitions, computed by `report.py`):
- Claimants per topper: distinct institutes with at least one claim.
- Course stated: share of claims without TT-01.
- Interview-only: share of course-stated claims with TT-02.
- Own-words check: share of claims (where an independent interview exists) with status `mentioned`, `denied`, `not_mentioned`.
- AI Mode: number of toppers for whom AI Mode names a coaching institute, and how many of those named institutes have only interview-only or unmentioned claims.

## 9. Validation

1. **CCPA order suite**: each of the 33 orders becomes test cases (claim text in, expected flags out, e.g. KSG "All TOP 5 Successful Candidates ... are from KSG" plus finding "Mock Interview / Free of cost" must yield TT-11 and TT-02). The case file is frozen and its SHA-256 recorded in `docs/VALIDATION.md` before the rules are scored. Precision and recall are reported as measured, without tuning against the frozen set afterwards.
2. **Hand-labelled sample**: the lead labels 40 randomly sampled CSE 2025 claims (course type, course stated yes/no) before seeing rule output; agreement is reported.
3. **Determinism**: running `analyze` twice on the same evidence produces the same manifest root hash (test).
4. **Replay parity**: replay run reproduces the recorded run's ledger hash (test, CI).

## 10. Errors, safety and ethics

- **Fail closed**: anything that cannot be resolved (unknown institute, ambiguous name, unreadable page) is recorded as `unresolved` and never counted as a claim.
- **SerpApi errors**: HTTP 429 honours Retry-After with capped retries (max 3); "no results" responses are stored and cost nothing; every error is logged without the key.
- **Secrets**: key only from env or `.env` (gitignored, `.env.example` committed). Fixtures are scrubbed of `json_endpoint`, `raw_html_file`, `prettify_html_file` URLs; a test fails if any fixture or log contains the key or the account hash segment.
- **Untrusted content**: all fetched text is data. The dashboard escapes everything (Jinja2 autoescape), never renders fetched HTML, and links out with `rel="noopener noreferrer nofollow"`.
- **Polite fetching**: robots.txt, 1 request per second per host, identifying user agent with the repo URL.
- **People**: only names and ranks published in official results, and statements from public interviews, are used. No face matching. Poster and ad images are not redistributed in the repo; fixtures keep OCR text, image URL and SHA-256 only. JEE and NEET toppers may be minors: the dashboard shows names exactly as in the official press release and no images.
- **Wording**: flags say "not stated", "differs", "not mentioned". The UI and README carry a fixed notice: "TopperTrail records what institutes publicly claim and what they disclose next to the claim. It does not decide whether a claim is false or misleading; that is for the CCPA." A "Request a correction" section explains how an institute can point to a disclosure we missed.

## 11. Deliverables

- Public GitHub repo (MIT), with a README containing: the headline finding, a 30-second quick start (`TOPPERTRAIL_REPLAY=1`), the "Why this needs SerpApi" table, credit budget, methodology link, validation results, limitations, ethics notice, AI tools disclosure.
- Local dashboard and static export (optionally published to GitHub Pages by the owner).
- Demo video under 3 minutes (script in `docs/DEMO-SCRIPT.md`): problem in 20 s, estimate and collect in 30 s, AIR 1 ledger in 60 s, institute scorecard in 30 s, AI Mode finding and evidence pack in 30 s, close.
- Submission form text in `docs/SUBMISSION.md`: description, "how it uses SerpApi", AI tools used (Claude Code for code and docs), new project.
- CI (GitHub Actions): ruff, pytest offline.

## 12. Timeline and gates

| Day | Work | Gate |
|---|---|---|
| Mon 5 Oct | Spec and plan approved; repo scaffold; owner creates SerpApi key; live spike on AIR 1 (about 8 credits) confirms response shapes and OCR wheel on Python 3.11/3.12 | Spike data looks as expected |
| Tue 6 Oct | SerpClient (live, record, replay), budget, roster, registry, evidence store, collectors | `estimate` and replay collect pass tests |
| Wed 7 Oct | Extraction, self-reports, rule engine, CCPA order suite | CCPA suite scored and recorded |
| Thu 8 Oct | Full UPSC recorded run; dashboard v1 | Ledger for top 20 complete |
| Fri 9 Oct | JEE/NEET light run, AI Mode, static export, README, CI, labelled sample | Judge-mode dry run from a clean clone |
| Sat 10 Oct | Demo video, submission text, final QA; owner submits by 18:00 IST | Submitted, links tested in incognito |

## 13. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Credits run out | Estimate and hard cap; replay fixtures; scope flags (`--top`, `--engines`); owner may ask the organisers for build credits |
| Institute pages render only in JavaScript | Labelled `snippet_only`; poster images and YouTube still give evidence |
| OCR wheel missing for the Python version | OCR is an optional extra; use Python 3.12 venv; fixtures carry OCR output |
| Auto-caption errors in Hindi | Devanagari alias lists include observed misspellings (वाजराम, अनअकडमी); statements always shown with timestamp and link so a human can check |
| Name collisions (SHUBHAM KUMAR is JEE Adv 2026 CRL 1 and UPSC CSE 2020 AIR 1) | Matching requires exam and year in the same window |
| Legal pushback from an institute | Neutral wording, evidence links, correction process, no "false" verdicts |
| Data changes before judging | Snapshots with dates and hashes; findings are stated "as observed on <date>" |

## 14. Owner actions

1. Create a free SerpApi account and put the key in `D:\Projects\TopperTrail\.env` (never in chat or commits).
2. Create the public GitHub repo `TopperTrail` and commit in small steps as each piece lands.
3. Optional: email adarsh@serpapi.com asking whether entrants can get extra build credits.
4. Answer the form's "How did you hear about the hackathon" truthfully; claim a partner community only if it is true.

## 15. Sources

- CCPA Guidelines 2024: https://ccpa.doca.gov.in/files/Guidelines%20for%20Prevention%20of%20Misleading%20Advertisement%20in%20Coaching%20Sector,%202024.pdf
- CCPA orders register: https://ccpa.doca.gov.in/ccpa-orders.php?page_no=1
- Vajiram & Ravi penalty (PIB 30.05.2026): https://www.pib.gov.in/PressReleasePage.aspx?PRID=2266932
- Vision IAS penalty (PIB 25.12.2025): https://www.pib.gov.in/PressReleasePage.aspx?PRID=2208482
- Motion and CLC penalties (PIB 15.05.2026): https://www.pib.gov.in/PressReleasePage.aspx?PRID=2261329
- UPSC CSE 2025 final result: https://www.upsc.gov.in/sites/default/files/CSE_2025_FR_Eng_06032026.pdf
- JEE Advanced 2026 press release: https://jeeadv.ac.in/documents/Result2026PressRelease.pdf
- NEET UG 2026 re-exam press release: https://cdnbbsr.s3waas.gov.in/s37bc1ec1d9c3426357e69acd5bf320061/uploads/2026/07/20260716477215762.pdf
- SerpApi engine docs: https://serpapi.com/search-engine-apis
