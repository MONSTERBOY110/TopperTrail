from toppertrail.extract.text import context_ok, find_name, mentions, normalize
from toppertrail.models import Topper


def t(rank, name, exam="upsc-cse-2025"):
    return Topper(exam, rank, name)


def test_normalize_folds_case_nukta_and_quotes():
    assert normalize("  Rau’s  IAS ") == "rau's ias"
    assert normalize("टेस्ट सीरीज़") == normalize("टेस्ट सीरीज")


def test_dotted_initials_and_possessive():
    assert find_name("Congrats to A.R. Rajah Mohaideen's success", "A R RAJAH MOHAIDEEN")
    assert find_name("Anuj Agnihotri's journey", "ANUJ AGNIHOTRI")


def test_printed_misspelling_matches_fuzzily_but_other_names_do_not():
    assert find_name("Pakshal Secretary AIR 8", "PAKSHAL SECRETRY")
    assert not find_name("Pakshal Sharma AIR 8", "PAKSHAL SECRETRY")


def test_single_token_name_needs_rank_nearby():
    hemant = t(13, "HEMANT", "upsc-cse-2024")
    assert mentions("Hemant secured AIR 13 in UPSC CSE 2024", [hemant])
    assert not mentions("Hemant Soren addressed a rally", [hemant])


def test_claimed_rank_is_the_nearest_rank():
    toppers = [t(1, "ANUJ AGNIHOTRI"), t(2, "RAJESHWARI SUVE M")]
    found = mentions("AIR 1 Anuj Agnihotri | AIR 2 Rajeshwari Suve M", toppers)
    assert {m.topper.rank: m.claimed_rank for m in found} == {1: 1, 2: 2}


def test_rank_word_inside_other_words_is_ignored():
    hemant = t(5, "HEMANT")
    assert not mentions("Hemant took the chair 5 times", [hemant])


def test_context_requires_exam_term_and_year():
    terms = ("jee", "iit")
    assert context_ok("Shubham Kumar CRL 1 JEE Advanced 2026", 2026, terms)
    assert not context_ok("Shubham Kumar AIR 1 UPSC CSE 2020", 2026, terms)
    assert context_ok("Shubham Kumar JEE topper ad", 2026, terms, require_year=False)
    assert not context_ok("bias in 2025 reports", 2025, ("ias",))


def test_topper_display_name():
    assert Topper("x", 7, "A R RAJAH MOHAIDEEN").display_name == "A R Rajah Mohaideen"


def test_rankers_is_not_a_rank_word():
    anuj = t(1, "ANUJ AGNIHOTRI")
    found = mentions("UPSC 2025 Top 10 Rankers: Anuj Agnihotri Secures Rank 1", [anuj])
    assert found[0].claimed_rank == 1


def test_rank_tokens_belong_to_the_nearest_name_in_lists():
    toppers = [t(1, "ANUJ AGNIHOTRI"), t(2, "RAJESHWARI SUVE M"), t(3, "AKANSH DHULL")]
    found = mentions("AIR 1 Anuj Agnihotri AIR 2 Rajeshwari Suve M AIR 3 Akansh Dhull", toppers)
    assert {m.topper.rank: m.claimed_rank for m in found} == {1: 1, 2: 2, 3: 3}
    found = mentions("Rajeshwari Suve M AIR 2, Akansh Dhull AIR 3", toppers)
    assert {m.topper.rank: m.claimed_rank for m in found} == {2: 2, 3: 3}


def test_a_wrong_rank_alone_is_still_reported():
    found = mentions("Our topper Anuj Agnihotri AIR 11 UPSC 2025", [t(1, "ANUJ AGNIHOTRI")])
    assert found[0].claimed_rank == 11


def test_a_nearby_official_rank_wins_over_a_neighbours_rank():
    toppers = [t(1, "ANUJ AGNIHOTRI"), t(2, "RAJESHWARI SUVE M"), t(3, "AKANSH DHULL")]
    text = ("Anuj Agnihotri has secured All India Rank 1, while Rajeshwari Suve M secured "
            "Rank 2 and Akansh Dhull secured Rank 3")
    found = mentions(text, toppers)
    assert {m.topper.rank: m.claimed_rank for m in found} == {1: 1, 2: 2, 3: 3}


def test_trim_around_snaps_to_words_and_marks_cuts():
    from toppertrail.extract.text import trim_around
    text = "alpha beta gamma delta " * 30 + "Anuj Agnihotri AIR 1 " + "epsilon zeta eta " * 30
    out = trim_around(text, "ANUJ AGNIHOTRI", 120)
    assert "Anuj Agnihotri" in out and out.startswith("...") and out.endswith("...")
    words = set(text.split()) | {"..."}
    assert all(w.strip(".") in words or w == "..." for w in out.split())
    assert len(out) <= 120


def test_exam_year_is_never_read_as_a_rank():
    from toppertrail.extract.text import ranks_in
    t = Topper("upsc-cse-2025", 1, "ANUJ AGNIHOTRI")
    m = mentions("UPSC CSE 2025 Rank 1 Anuj Agnihotri", [t])
    assert m and m[0].claimed_rank == 1
    assert ranks_in("UPSC CSE 2025 Rank 1") == {1}


def test_merged_ocr_name_must_start_and_end_a_word():
    akash = Topper("x", 9, "AKASH KUMAR")
    assert mentions("Congratulations PRAKASHKUMAR AIR 9", [akash], squashed=True) == []
    assert mentions("Congratulations AKASHKUMARI AIR 9", [akash], squashed=True) == []
    assert mentions("Congratulations AKASHKUMAR AIR 9", [akash], squashed=True)
    assert mentions("ToppersAkashKumar AIR9", [akash], squashed=True)  # case change ends a word


def test_trim_cuts_at_newlines_too():
    from toppertrail.extract.text import trim_around
    text = "\n".join(f"WORD{i}" for i in range(150)) + "\nAnuj Agnihotri AIR 1\n" + \
        "\n".join(f"TAIL{i}" for i in range(150))
    out = trim_around(text, "ANUJ AGNIHOTRI", 300).replace("...", " ")
    tokens = out.split()
    assert "Agnihotri" in tokens
    assert all(t.startswith(("WORD", "TAIL")) and t[4:].isdigit() or t in
               ("Anuj", "Agnihotri", "AIR", "1") for t in tokens)
    assert all(t not in ("ORD", "RD") for t in tokens)
