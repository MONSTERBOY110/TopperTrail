from toppertrail.extract.courses import Lexicon
from toppertrail.rules import load_orders, score_orders


def test_orders_file_is_complete_and_scores():
    data = load_orders()
    assert len(data["orders"]) == 33
    assert sum(len(o["claims"]) for o in data["orders"]) >= 80
    assert len(data["course_labels"]) == 21
    scores = score_orders(data, Lexicon.load())
    for rule in ("TT-09", "TT-10", "TT-11"):
        assert set(scores[rule]) == {"tp", "fp", "fn", "precision", "recall"}
    assert 0.0 <= scores["course_labels"]["exact"] <= 1.0
