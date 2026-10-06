# Live spike, 5 Oct 2026 (AIR 1, UPSC CSE 2025, 7 credits)

Every engine answered; fields match what the parsers read.

- `google`: 8 organic results for the exact-name query, mostly news sites and social posts. Institute pages are rarer here than in image results.
- `google_images`: 100 results; `link` often points at institute pages (Vajiram & Ravi, Vajirao & Reddy, Physics Wallah). Change made: the collector now also fetches those pages, at no extra credit cost.
- `youtube`: 3 video results for this query, with `channel.link` as `/@handle`. A collaboration video ("NEXT IAS and NEXT IAS HINDI") has no channel link. Change made: a joined channel name resolves when one part is exactly a registered name.
- `youtube_video`: `description` is an object with `content`; already handled.
- `youtube_video_transcript`: `language_code=hi` without `type=asr` returned the auto captions (859 lines); kept as is.
- `google_ads_transparency_center`: 100 creatives for visionias.in (200 total) since 6 Mar 2026; image creatives carry `image` and `last_shown`; some creatives have no `image`.
- `google_ai_mode`: `text_blocks` plus `reconstructed_markdown`; the answer names NEXT IAS.
- OCR (rapidocr-onnxruntime on Python 3.11) reads ad creatives, about 1 to 3 s per image.
