# Validation

## CCPA order suite

The claim texts of 33 CCPA coaching orders (2023 to 2026, 94 claim texts) and 21 course labels quoted in CCPA findings were labelled by the author from the text alone, before the rule engine was scored. The author also wrote the rules, so this is a consistency check against CCPA's own record, not an independent evaluation.

Label definitions used:
- `TT-11` when the text states a count, share or top-N position of selections or results.
- `TT-09` when the text uses a superlative about the institute.
- `TT-10` when the text promises an outcome.

Two entries are research descriptions of a claim rather than verbatim advertisement text; they carry no labels and are marked with a `note`.

Frozen file: `toppertrail/data/ccpa/orders.yaml`, SHA-256 `a2d144d890c7bad09b23dec0fa3015990770e36d0283ff70064f1be49f32d77a`, frozen on 2026-10-05.

Results are pasted below exactly as printed by `toppertrail validate`. The frozen file is not edited after scoring; any later lexicon change is reported as a new, dated table.

## Results (2026-10-05, first scoring of the frozen file)

| Rule | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|
| TT-09 | 8 | 1 | 2 | 0.889 | 0.8 |
| TT-10 | 3 | 0 | 0 | 1.0 | 1.0 |
| TT-11 | 57 | 0 | 19 | 1.0 | 0.75 |

Course labels classified exactly (types, paid/free, duration, vague): 21 of 21.

What the rules missed, from the same run:
- Count claims phrased without "selections", "rank holders", "top N" or "out of": "3291+ successful candidate", "Hundreds of ... students aced", "1384 IIT-Ranks", "1650+ CLCians", "2 CLCians in NEET AIR-100", "Success Ratio at 61%", "% of Qualified students 6972/7645", "99.99% in JEE 2021", "Delivering 20% selection", "150 plus students ... have cleared", "42 candidates have cleared ... 37 studied", "First Rank four times", "1st RANK IN HCS/PCS/HAS", "7 Times result growth".
- One Hindi line: "सीकर में Best CLC AIR-1000 में गत वर्ष सर्वाधिक 7 गुना वृद्धि" (superlative and count).
- "India's largest coaching network" (superlative not in the lexicon).
- One extra: "stepping stone to India's Best Officers" was counted as a superlative about the institute.

Reading: the rules are precise (one false positive in 94 texts) and conservative. Missed claims are mostly JEE and NEET style result statistics, which the UPSC-first lexicon was not written for. A missed count claim means a signal is not shown; it never produces a wrong flag on a topper claim.

## Results (2026-10-05, after the real-page fixes)

The lexicon was changed after the first scoring, to fix problems found by running the pipeline on real institute pages and a real Hindi transcript saved during research (not on this suite): bare "optional" no longer counts as a course ("Optional Subject" is the topper's subject), "N out of M" counts only with a noun such as "selected" or "vacancies" (so marks like "1071 out of 2025" are not counted), one-digit "N results" needs a "+", and Devanagari terms must start a word ("मोशन" no longer matches inside "इमोशन"). The frozen file is unchanged (same SHA-256).

| Rule | TP | FP | FN | Precision | Recall |
|---|---|---|---|---|---|
| TT-09 | 8 | 1 | 2 | 0.889 | 0.8 |
| TT-10 | 3 | 0 | 0 | 1.0 | 1.0 |
| TT-11 | 57 | 0 | 19 | 1.0 | 0.75 |

Course labels classified exactly: 21 of 21. Scores are unchanged by the fixes.
