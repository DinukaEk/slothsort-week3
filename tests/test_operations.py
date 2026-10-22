from pathlib import Path
import pytest

from slothsort.config import Settings
from slothsort.engine import Suggestion
from slothsort.operations import history, move_items, undo_last_batch
from slothsort.scanner import read_item


def setup_workspace(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    out = tmp_path / "sorted"
    return inbox, out, Settings(inbox, out)


def candidate(path, category="Finance"):
    return Suggestion(read_item(path), category, 0.81, 0.2, True, "Work")


def test_move_then_undo(tmp_path):
    inbox, out, settings = setup_workspace(tmp_path)
    file = inbox / "bank.txt"
    file.write_text("Payment received")
    event = move_items(settings, [(candidate(file), "Finance")], {"Finance"})
    assert len(event) == 1
    assert not file.exists()
    assert (out / "Finance" / "bank.txt").exists()
    assert history(out)[0]["op"] == "move"
    restored, errors = undo_last_batch(settings)
    assert len(restored) == 1 and not errors
    assert file.read_text() == "Payment received"
    assert len(history(out)) == 2


def test_undo_is_idempotent(tmp_path):
    inbox, out, settings = setup_workspace(tmp_path)
    file = inbox / "a.txt"
    file.write_text("hi")
    move_items(settings, [(candidate(file), "Finance")], {"Finance"})
    undo_last_batch(settings)
    assert undo_last_batch(settings) == ([], [])


def test_collision_never_overwrites(tmp_path):
    inbox, out, settings = setup_workspace(tmp_path)
    file = inbox / "item.txt"
    file.write_text("new data")
    target = out / "Finance"
    target.mkdir(parents=True)
    (target / "item.txt").write_text("old data")
    move_items(settings, [(candidate(file), "Finance")], {"Finance"})
    assert (target / "item.txt").read_text() == "old data"
    assert (target / "item__2.txt").read_text() == "new data"


def test_changed_preview_is_refused(tmp_path):
    inbox, out, settings = setup_workspace(tmp_path)
    file = inbox / "a.txt"
    file.write_text("first")
    suggestion = candidate(file)
    file.write_text("later")
    with pytest.raises(ValueError, match="changed after preview"):
        move_items(settings, [(suggestion, "Finance")], {"Finance"})
    assert file.exists()


def test_unknown_category_is_refused(tmp_path):
    inbox, out, settings = setup_workspace(tmp_path)
    file = inbox / "a.txt"
    file.write_text("first")
    with pytest.raises(ValueError, match="Unknown"):
        move_items(settings, [(candidate(file), "Unknown")], {"Finance"})


def test_undo_changed_content_is_refused(tmp_path):
    inbox, out, settings = setup_workspace(tmp_path)
    file = inbox / "a.txt"
    file.write_text("first")
    move_items(settings, [(candidate(file), "Finance")], {"Finance"})
    (out / "Finance" / "a.txt").write_text("edited")
    restored, errors = undo_last_batch(settings)
    assert restored == [] and "content changed" in errors[0]


def test_undo_does_not_overwrite_new_inbox_file(tmp_path):
    inbox, out, settings = setup_workspace(tmp_path)
    file = inbox / "a.txt"
    file.write_text("first")
    move_items(settings, [(candidate(file), "Finance")], {"Finance"})
    file.write_text("new inbox content")
    restored, errors = undo_last_batch(settings)
    assert not restored and errors
    assert file.read_text() == "new inbox content"


def test_nested_output_is_refused(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    with pytest.raises(ValueError, match="separate"):
        Settings(inbox, inbox / "categorized").validate()


def test_same_folder_is_refused(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    with pytest.raises(ValueError, match="separate"):
        Settings(inbox, inbox).validate()


def test_multiple_moves_one_batch(tmp_path):
    inbox, out, settings = setup_workspace(tmp_path)
    a, b = inbox / "a.txt", inbox / "b.txt"
    a.write_text("one")
    b.write_text("two")
    move_items(settings, [(candidate(a), "Finance"), (candidate(b), "Work")], {"Finance", "Work"})
    restored, errors = undo_last_batch(settings)
    assert len(restored) == 2 and not errors
    assert a.exists() and b.exists()


def test_undo_most_recent_batch_only(tmp_path):
    inbox, out, settings = setup_workspace(tmp_path)
    a = inbox / "a.txt"
    a.write_text("first")
    move_items(settings, [(candidate(a), "Finance")], {"Finance"})
    b = inbox / "b.txt"
    b.write_text("second")
    move_items(settings, [(candidate(b), "Finance")], {"Finance"})
    undo_last_batch(settings)
    assert b.exists() and not a.exists()


def test_unsupported_output_symlink(tmp_path):
    inbox, out, settings = setup_workspace(tmp_path)
    external = tmp_path / "external"
    external.mkdir()
    try:
        out.symlink_to(external, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation not allowed")
    with pytest.raises(ValueError, match="Symlink"):
        settings.validate()
