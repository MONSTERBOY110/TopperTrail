# Submission form text

Paste into https://serpapi.github.io/serpapi-india-hackathon-2026/submit.html (sign in with GitHub). Fill the repository and video links on submission day and test both in a private window.

**Project name:** TopperTrail

**Track:** Knowledge & Public Interest

**Public GitHub repository:** https://github.com/MONSTERBOY110/TopperTrail

**Demo video:** https://youtu.be/XMOh3FFxQos

**Project description:**
After every UPSC, JEE and NEET result, coaching institutes put the same toppers on their pages, posters, YouTube channels and ads. Parents and aspirants pay Rs 1 to 3 lakh on the strength of those claims, and the CCPA has fined institutes more than Rs 1.46 crore, mostly because the "topper" had only taken a free interview programme and the advertisement did not say so. TopperTrail collects every public claim about each official topper from the institutes' own channels, checks each one with fixed rules taken from the CCPA's 2024 coaching guidelines and orders, compares it with the topper's own words in an independent interview, and records what Google AI Mode says. The result is a ledger per exam: who claims each rank, what course they name next to the claim, and the evidence for every line. It helps aspirants and parents before they pay, and gives journalists and consumer bodies citable evidence. In the recorded run for UPSC CSE 2025, 7 institutes claim AIR 1, every top-20 rank is claimed by at least 3 institutes, and whether the course was paid or free is stated next to 1% of claims. No AI model decides anything; the rules are validated against 33 CCPA orders, and the recorded run replays with no API key.

**How the project uses SerpApi:**
SerpApi is the data layer; without it there is no ledger.
- Google Search (gl=in, hl=en and hl=hi): institute pages and posts that name each topper.
- Google Images: congratulation posters on institute domains.
- YouTube Search: institute-hosted mock interviews and independent interviews; the channel identifies the institute.
- YouTube Video: full descriptions, where institutes list "courses joined".
- YouTube Video Transcript (Hindi and English): the topper's own words, matched against each claim.
- Google Ads Transparency Center (region India): ads institutes actually ran after the result.
- Google AI Mode: whether Google's AI repeats institute claims as fact.
- Account API: a credit check before any run. Every stored claim keeps its SerpApi search id; responses are scrubbed and saved so judges can replay the run.

**AI tools used:** Claude Code (Anthropic) wrote code, tests and documentation with the developer. The demo video's narration voice is Microsoft Edge neural text to speech. No AI model is used inside the product.

**New or existing project:** New, built for this hackathon.

**How did you hear about the hackathon:** (answer truthfully)
