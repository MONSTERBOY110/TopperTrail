# Demo video (2:52, recorded 5 October 2026)

Everything on screen is the project running locally: a real PowerShell session and the real dashboard, filmed frame by frame. The terminal part is judge mode, run in a fresh copy of the repository with no `.env` and no API key, so the recording spent no credits. The short live clip is the actual recorded run, sped up. Narration is Microsoft Edge neural text to speech; every number it says is printed by `toppertrail analyze` on the recorded run.

| Time | On screen | Narration |
|---|---|---|
| 0:00 | Title card | TopperTrail. One rank, many claims. Follow the trail. |
| 0:07 | CCPA order of 29 May 2026; AIR 1 claimed by 7 institutes | In May, India's consumer regulator fined Vajiram and Ravi seven lakh rupees over one line: eight rank holders in the top ten. For UPSC 2025, the top rank alone is claimed by seven institutes. Which of them taught the topper, and what? |
| 0:28 | PowerShell in a fresh copy: `Test-Path .env` (False), `estimate`, replay `collect`, `verify`, `analyze`, `serve` | This is judge mode: a fresh copy of the repo, with no API key. TopperTrail plans every SerpApi search and its credit cost before spending anything: Google in English and Hindi, Google Images, YouTube, video transcripts, the Ads Transparency Center, and AI Mode. Collect replays the recorded run. Verify checks every evidence hash against the recorded manifest. And analyze rebuilds the same ledger, hash for hash. |
| 1:05 | The live run on 5 October (`budget`, `estimate`, `collect --record`), sped up | The recording itself was one live run on the fifth of October, with OCR reading every poster and ad. |
| 1:16 | Exam board: finding sentence, tally strip, who claims each rank | The dashboard opens on the finding. Every one of the top twenty toppers is claimed by at least three institutes. Each chip is one institute. Solid means a course is named next to the claim. Stripes mean only an interview programme. A hollow ring means nothing is stated. |
| 1:38 | AIR 1 ledger: Vajiram & Ravi's poster and "(IGP)" claim, rule flags, source and SerpApi search id | For the topper, every claim keeps its exact wording, with the course words marked. Vajiram and Ravi lists the topper with I G P, its interview guidance programme. Each claim shows the rules it raises, the source, the date, and the SerpApi search that found it. |
| 1:58 | The topper's own words, timestamped Hindi caption lines | Then the topper's own words, from an independent interview's captions. Every line is timestamped and linked, so anyone can check what the topper actually took. |
| 2:10 | What Google AI Mode says | And this is what Google's AI Mode tells an aspirant who asks. |
| 2:18 | Vajiram & Ravi scorecard, CCPA order on record, the notice | Each institute gets a scorecard: its claims, its wording, and the CCPA orders already on record against it. |
| 2:29 | Methodology: the 14 rules | Fourteen fixed rules. No AI model decides anything. The rules are validated against thirty three CCPA orders. |
| 2:41 | End card: repository, judge mode, the seven engines | TopperTrail runs locally, and the recorded run replays without a key. One rank. Many claims. Follow the trail. |

The terminal segment was filmed before two later refinements (excerpts now cut at any whitespace, and a page that yields a claim is no longer also listed as unclaimed). They change the ledger hash a replay prints today (UPSC `df324724...`) but none of the numbers on screen; live run and replay still produce the identical hash.

To re-voice it, record the narration column over the version without a voice, keeping each line at its start time.
