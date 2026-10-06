# TopperTrail

**One rank. Many claims. Follow the trail.**

After every UPSC, JEE and NEET result, coaching institutes put the same toppers on their pages, posters, YouTube channels and ads. Parents and aspirants pay Rs 1 to 3 lakh on the strength of those claims. The Central Consumer Protection Authority (CCPA) has issued more than 60 notices and over Rs 1.46 crore in penalties, and its orders keep finding the same thing: the "topper" had taken only a free interview programme, a test series, or nothing at all, and the advertisement did not say so. In May 2026 it fined Vajiram & Ravi Rs 7 lakh for "8 Rank Holders in the Top 10"; seven of the eight had only attended its free Interview Guidance Programme ([PIB](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2266932)).

CCPA finds this one institute at a time, months later. The evidence is public on result day. TopperTrail assembles it: for every official topper it collects each institute's claims from the institute's own channels, checks what the institute disclosed next to the claim against the CCPA's 2024 coaching guidelines, compares it with the topper's own words in an independent interview, and records what Google AI Mode says.

Built for the SerpApi India Hackathon 2026 (Knowledge & Public Interest). **Demo video (2:53):** https://youtu.be/XMOh3FFxQos

## What the recorded run found (UPSC CSE 2025, top 20)

- **7 institutes claim AIR 1**, and all 20 top ranks are claimed by at least 3 institutes each (266 claims by 20 institutes).
- A course is named next to 69% of claims; **39% of those name only an interview programme**, the pattern behind most CCPA penalties.
- Whether the course was paid or free is stated next to **1%** of claims.
- Vajiram & Ravi claims 18 of the top 20; 29 of its 47 claims name only its interview programme.
- Google AI Mode names a coaching institute for all 20 toppers.

Full numbers, JEE Advanced and NEET UG: [docs/FINDINGS.md](docs/FINDINGS.md). Every number is reproducible from the committed run with no API key.

## Try it in a minute, no API key

Windows (PowerShell):

```powershell
git clone https://github.com/MONSTERBOY110/TopperTrail.git; cd TopperTrail
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
$env:TOPPERTRAIL_REPLAY = "1"
toppertrail collect upsc-cse-2025  # replays the recorded SerpApi run from fixtures/
toppertrail verify upsc-cse-2025   # evidence hashes and the manifest root match the recording
toppertrail analyze upsc-cse-2025  # builds the ledger and prints the headline numbers
toppertrail serve                  # http://127.0.0.1:8765/
```

macOS or Linux:

```bash
git clone https://github.com/MONSTERBOY110/TopperTrail.git && cd TopperTrail
python3.11 -m venv .venv && source .venv/bin/activate
python -m pip install -e .
export TOPPERTRAIL_REPLAY=1
toppertrail collect upsc-cse-2025 && toppertrail verify upsc-cse-2025
toppertrail analyze upsc-cse-2025 && toppertrail serve
```

The same replay works for `jee-adv-2026` and `neet-ug-2026`. Python 3.11 or newer.

## Run it live

1. Put your key in `.env`: `SERPAPI_API_KEY=...` (never commit it; `.env` is ignored).
2. `toppertrail estimate upsc-cse-2025` prints the credits per engine before anything is spent.
3. `toppertrail collect upsc-cse-2025 --record` collects, stops at the credit cap, and exports scrubbed fixtures for replay.
4. `toppertrail analyze upsc-cse-2025`, then `toppertrail serve` or `toppertrail export --out site`.

| Exam | Scope | Credits |
|---|---|---|
| UPSC CSE 2025 | top 20 ranks, deep | 145 |
| JEE Advanced 2026 | top 5 ranks | 24 |
| NEET UG 2026 | top 5 ranks | 24 |

Identical searches within an hour come from SerpApi's cache at no cost; `collect` never sets `no_cache`.

## Why this needs SerpApi

| Engine | What TopperTrail reads | Why nothing else works |
|---|---|---|
| `google` (gl=in, hl=en and hl=hi) | organic results on institute domains: titles, snippets, links | finds every institute page that names a topper, in English and Hindi |
| `google_images` | images on institute domains, original image URL | congratulation posters are the main claim medium |
| `youtube` | video results with channel links and lengths | institute-hosted mock interviews, and the independent interview to read |
| `youtube_video` | full descriptions | institutes list "courses joined" in descriptions |
| `youtube_video_transcript` | timestamped captions in Hindi or English | the topper's own words, matched against each claim |
| `google_ads_transparency_center` (region 2356) | ad creatives an institute ran in India after the result | paid claims, not just organic ones |
| `google_ai_mode` | answer text and references | whether Google's AI repeats institute claims as fact |
| Account API | searches left | refuses a run that would overspend |

Every stored claim keeps the SerpApi search id that surfaced it. Responses are scrubbed of account URLs and the key, trimmed to the fields the rules use, and stored by SHA-256; the run manifest's root hash covers all of it.

## How a verdict is made

No AI model decides anything. Fourteen fixed rules (TT-01 to TT-14) each cite a clause of the Guidelines for Prevention of Misleading Advertisement in Coaching Sector, 2024, the Consumer Protection Act 2019, or a CCPA order: course not stated next to the claim, interview programme only, vague label, paid or free not stated, duration not stated, different labels across the institute's own sources, selective disclosure on one page, rank differing from the official result, superlatives, guarantee wording, count claims, the topper's own words, a claim for a different exam, and a paid ad in India. A page mention counts as a claim only when it ties the topper to the institute; pages that list toppers as news are not counted. Details: [docs/METHODOLOGY.md](docs/METHODOLOGY.md).

## Validation

The rules were scored against the claim texts of 33 CCPA coaching orders (94 texts) and 21 course labels quoted in CCPA findings, labelled before scoring and frozen by SHA-256. Count claims: precision 1.0, recall 0.75. Guarantee wording: 1.0 and 1.0. Superlatives: 0.889 and 0.8. Course labels classified exactly: 21 of 21. What the rules miss is listed in [docs/VALIDATION.md](docs/VALIDATION.md).

The pipeline was also run on institute pages and a Hindi interview transcript saved during research, which found and fixed six extraction defects before any credits were spent (logged in VALIDATION.md).

## Limits

- Counts are lower bounds: 46 institutes are registered, and claims phrased without an association word are not counted.
- Pages that render only in JavaScript fall back to the search snippet.
- OCR reads English only; it is an optional extra (`pip install -e ".[ocr]"`).
- Automatic captions mangle names and negations; every own-words line links to its timestamp so it can be checked.
- Findings are as observed on the date shown on each claim.

## Ethics and corrections

TopperTrail records what institutes publicly claim and what they disclose next to the claim. Only the CCPA decides whether an advertisement is misleading. It uses only names and ranks published in official results and statements from public interviews, does no face matching, and does not redistribute poster or ad images. If an institute discloses a course next to a claim and the ledger missed it, open an issue with the page link; the page is collected again and the change is published with its date.

## AI tools

Code, tests and documentation were written with Claude Code (Anthropic). The demo video's narration voice is Microsoft Edge neural text to speech. No AI model is used inside the product.

## License

MIT. Fonts: Martel and Mukta under the SIL Open Font License (licences in `toppertrail/web/static/fonts/`).
