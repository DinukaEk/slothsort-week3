from pathlib import Path
import pytest

from slothsort.engine import cosine, suggest
from slothsort.scanner import FileItem


class FakeEncoder:
    """Vector fixture; unit tests never download Hugging Face weights."""
    def encode(self, texts, **kwargs):
        def vec(text):
            if "Finance" in text or "payment" in text:
                return [1.0, 0.0, 0.0]
            if "Work" in text or "project" in text:
                return [0.0, 1.0, 0.0]
            return [0.0, 0.0, 1.0]
        return [vec(t) for t in texts]


def item(path, text):
    return FileItem(Path(path), text, "examplehash", 4)


def test_cosine_identical():
    assert cosine([1, 0], [1, 0]) == 1


def test_cosine_orthogonal():
    assert cosine([1, 0], [0, 1]) == 0


def test_cosine_zero_vector():
    assert cosine([0, 0], [1, 1]) == 0


def test_cosine_dimension_mismatch():
    with pytest.raises(ValueError):
        cosine([1, 0], [1])


def test_semantic_category_selection():
    results = suggest([item("a.txt", "payment arrived")], {"Finance": "money", "Work": "delivery"}, FakeEncoder())
    assert results[0].category == "Finance"
    assert results[0].eligible


def test_result_contains_runner_up():
    results = suggest([item("a.txt", "project review")], {"Finance": "money", "Work": "delivery"}, FakeEncoder())
    assert results[0].category == "Work"
    assert results[0].runner_up == "Finance"


def test_threshold_allows_clear_winner():
    results = suggest([item("a.txt", "payment received")], {"Finance": "money", "Work": "delivery"}, FakeEncoder(), min_similarity=1, min_margin=1)
    assert results[0].eligible is True
    assert results[0].margin == 1.0


def test_ambiguous_result_not_auto_eligible():
    class AmbiguousEncoder:
        def encode(self, texts, **kwargs):
            return [[1, 0], [0.99, 0.01], [1, 0]]
    result = suggest([item("a.txt", "something")], {"Finance": "money", "Work": "delivery"}, AmbiguousEncoder(), min_margin=0.05)[0]
    assert result.category == "Finance"
    assert result.eligible is False


def test_invalid_thresholds():
    with pytest.raises(ValueError):
        suggest([item("a.txt", "payment")], {"Finance": "a", "Work": "b"}, FakeEncoder(), min_margin=1.1)


def test_empty_input_no_model_call():
    assert suggest([], {"Finance": "money", "Work": "office"}, FakeEncoder()) == []


def test_at_least_two_categories():
    with pytest.raises(ValueError):
        suggest([item("a.txt", "payment")], {"Finance": "money"}, FakeEncoder())
