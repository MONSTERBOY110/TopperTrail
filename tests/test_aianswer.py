from toppertrail.data import load_registry
from toppertrail.extract.aianswer import ai_answer


def test_ai_answer_lists_named_institutes():
    resp = {
        "search_metadata": {"id": "ai1"},
        "text_blocks": [
            {"type": "paragraph",
             "snippet": "Anuj Agnihotri prepared largely through self-study."},
            {"type": "list", "list": [
                {"snippet": "He attended mock interviews at NEXT IAS."},
                {"snippet": "Vajiram & Ravi lists him under its Interview Guidance Programme."},
            ]},
        ],
    }
    a = ai_answer(resp, 1, load_registry())
    assert a.institutes == ("next-ias", "vajiram-ravi")
    assert a.search_id == "ai1"
    assert a.excerpt.startswith("Anuj Agnihotri prepared")


def test_ai_answer_empty_response():
    a = ai_answer({"error": "no answer"}, 3, load_registry())
    assert a.institutes == () and a.excerpt == ""
