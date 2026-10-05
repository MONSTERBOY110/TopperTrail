import pytest

from toppertrail.extract.courses import Lexicon


@pytest.fixture(scope="module")
def lex():
    return Lexicon.load()


def test_mock_interview_vs_mock_test_vs_topper_interview(lex):
    title = "Anuj Agnihotri AIR 1 | CSE Topper's Mock Interview"
    assert lex.classify(title).course_types == ("interview_only",)
    assert lex.classify("Prelims mock test series").course_types == ("test_series",)
    assert lex.classify("UPSC Topper Interview with Anuj").course_types == ()


def test_ccpa_course_labels(lex):
    label = "GS FOUNDATION BATCH CLASSROOM STUDENT"
    assert lex.classify(label).course_types == ("foundation_classroom",)
    m = lex.classify("Mock Interview / Free of cost")
    assert m.course_types == ("interview_only",) and m.paid_free
    m = lex.classify("free 5-day Interview Training Program")
    assert m.course_types == ("interview_only",) and m.paid_free and m.duration
    assert lex.classify("GS Mains Test Series 2020").course_types == ("test_series",)
    assert lex.classify("I-Eklavya (Online)").course_types == ("online_distance",)
    assert lex.classify("PSIR optional").course_types == ("optional",)


def test_vague_labels_and_hindi(lex):
    m = lex.classify("Our student Anuj Agnihotri, AIR 1")
    assert m.course_types == () and m.vague
    hindi = lex.classify("टेस्ट सीरीज़ और इंटरव्यू गाइडेंस प्रोग्राम")
    assert hindi.course_types == ("interview_only", "test_series")
    generic = lex.classify("कोई कोचिंग नहीं ली", include_generic=True)
    assert generic.course_types == ("coaching_generic",)
    assert lex.classify("Best IAS Coaching in Delhi").course_types == ()


def test_signals_from_ccpa_claim_texts(lex):
    assert lex.aggregates("8 Rank Holders in the Top 10 are from Vajiram & Ravi")
    assert lex.aggregates("120+ selections in UPSC CSE 2023")
    assert lex.aggregates("26% of all UPSC rankers are Unacademy learners")
    assert lex.aggregates(
        "All TOP 5 Successful Candidates of UPSC Civil Services Exam 2022 are from KSG."
    )
    assert lex.aggregates("682 out of 933 selected students are from KSG.")
    assert not lex.aggregates("UPSC 2025 results announced")
    assert lex.superlatives("We are India's No. 1 Prestigious UPSC/IAS Coaching Institute")
    best = "Best IAS Coaching Institute for General Studies and CSAT in India."
    assert lex.superlatives(best) == ["best ias coaching"]
    assert lex.guarantees("Success Pakka Offer")
    assert lex.guarantees("मोशन है तो सिलेक्शन है")
    assert lex.guarantees("Guaranteed Prelims & Mains")


def test_first_person_and_negation(lex):
    assert lex.first_person("मॉक इंटरव्यूज में मैंने नेक्स्ट आईएएस का मॉक इंटरव्यू दिया")
    assert not lex.first_person("10 आउट ऑफ टॉप 10 आर फ्रॉम वेरियस कोर्सेज ऑफ वाजराम एंड रवि")
    assert lex.negated("मैंने टेस्ट सीरीज शायद कभी जॉइ नहीं करी")
    assert not lex.negated("I joined the test series")


def test_optional_subject_is_not_a_course(lex):
    assert lex.classify("Anuj Agnihotri UPSC AIR 1 2025, Age, Optional Subject").course_types == ()
    assert lex.classify("Sociology Crash Course and Test Series").course_types == (
        "crash_course", "test_series")


def test_marks_are_not_count_claims(lex):
    assert not lex.aggregates("He scored 1071 out of 2025 marks")
    assert not lex.aggregates("Interview 204 out of 275")
    assert not lex.aggregates("UPSC AIR 1 result announced")
    assert lex.aggregates("62 out of 1228 vacancies in 2013")


def test_hindi_plural_suffix_still_matches(lex):
    text = "मॉक इंटरव्यूज में मैंने नेक्स्ट आईएएस का मॉक इंटरव्यू दिया"
    assert lex.classify(text).course_types == ("interview_only",)
