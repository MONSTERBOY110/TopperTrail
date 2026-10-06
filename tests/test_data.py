from datetime import date

from toppertrail.data import exam_ids, load_exam, load_independent, load_registry, load_roster


def test_exams_and_roster():
    assert exam_ids() == ["jee-adv-2026", "neet-ug-2026", "upsc-cse-2025"]
    exam = load_exam("upsc-cse-2025")
    assert exam.result_date == date(2026, 3, 6)
    assert exam.transcript_params == (("language_code", "hi"),)
    roster = load_roster(exam, 3)
    assert [(t.rank, t.name) for t in roster] == [
        (1, "ANUJ AGNIHOTRI"),
        (2, "RAJESHWARI SUVE M"),
        (3, "AKANSH DHULL"),
    ]


def test_registry_urls_and_lookalikes():
    reg = load_registry()
    assert reg.by_url("https://news.allen.in/allen-kota-alumni").id == "allen"
    assert reg.by_url("https://www.vajiraoinstitute.com/x.aspx").id == "vajirao-reddy"
    vajiram = reg.by_url("https://vajiramandravi.com/ias-selections-from-vajiram/")
    assert vajiram.id == "vajiram-ravi"
    assert reg.by_url("https://onlyias.com/anything") is None
    assert reg.by_url("https://thebetterindia.com/upsc/x") is None


def test_registry_channels():
    reg = load_registry()
    link = "https://www.youtube.com/channel/UCgKgAaGbKS-XWUJGWqP5W0A"
    assert reg.by_channel(link, None).id == "next-ias"
    assert reg.by_channel("https://www.youtube.com/@NEXTIAS", None).id == "next-ias"
    assert reg.by_channel(None, "NEXT IAS").id == "next-ias"
    assert reg.by_channel(None, "NEXT IAS Fans Club") is None


def test_aliases_avoid_common_hindi_words():
    reg = load_registry()
    assert reg.find_aliases("मेरी दृष्टि से यह विजन सही था") == []
    assert reg.find_aliases("मैंने नेक्स्ट आईएएस का मॉक इंटरव्यू दिया") == ["next-ias"]
    assert reg.find_aliases("Vajiram & Ravi and Vajirao & Reddy") == [
        "vajiram-ravi",
        "vajirao-reddy",
    ]


def test_ads_targets_and_independent_channels():
    reg = load_registry()
    upsc = reg.ads_for("upsc")
    assert len(upsc) == 15
    assert ("physics-wallah", "pwonlyias.com") in {(i.id, d) for i, d in upsc}
    assert len(reg.ads_for("jee")) == 4 and len(reg.ads_for("neet")) == 4
    ind = load_independent()
    assert ind.match("https://www.youtube.com/channel/UCuHW2abZ-K0SKGhXfkyOY6w", None)
    assert ind.match(None, "The Lallantop")
    assert not ind.match(None, "Vision IAS")


def test_devanagari_alias_needs_a_word_start():
    reg = load_registry()
    assert reg.find_aliases("व्हाई डज़ दैट इमोशन कम्स इन") == []
    assert reg.find_aliases("मोशन है तो सिलेक्शन है") == ["motion"]


def test_collaboration_channel_without_link_resolves_by_an_exact_part():
    reg = load_registry()
    assert reg.by_channel(None, "NEXT IAS and NEXT IAS HINDI").id == "next-ias"
    assert reg.by_channel(None, "NEXT IAS Fans Club") is None
