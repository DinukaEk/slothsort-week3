from pathlib import Path
import pytest

from slothsort.scanner import read_item, scan, MAX_BYTES
from slothsort.demo import SAMPLE_FILES, EXPECTED, create_demo


def test_plain_text_is_read(tmp_path):
    file = tmp_path / "note_01.txt"
    file.write_text("Pay for breakfast", encoding="utf-8")
    item = read_item(file)
    assert "Pay for breakfast" in item.text
    assert len(item.digest) == 64


def test_csv_is_read(tmp_path):
    file = tmp_path / "report.csv"
    file.write_text("item,amount\nTea,20", encoding="utf-8")
    assert "Tea,20" in read_item(file).text


def test_invalid_extension_skipped(tmp_path):
    (tmp_path / "a.exe").write_bytes(b"danger")
    items, skips = scan(tmp_path)
    assert items == []
    assert skips[0][0] == "a.exe"


def test_hidden_ignored(tmp_path):
    (tmp_path / ".private.txt").write_text("secret")
    items, skips = scan(tmp_path)
    assert items == [] and skips == []


def test_subfolders_not_scanned(tmp_path):
    folder = tmp_path / "sub"
    folder.mkdir()
    (folder / "foo.txt").write_text("Hello")
    assert scan(tmp_path)[0] == []


def test_symlink_ignored(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("Test")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(source)
    except (OSError, NotImplementedError):
        pytest.skip("Creating symlinks not permitted")
    items, _ = scan(tmp_path)
    assert [i.path.name for i in items] == ["source.txt"]


def test_oversized_file_skipped(tmp_path):
    file = tmp_path / "giant.txt"
    with file.open("wb") as handle:
        handle.seek(MAX_BYTES)
        handle.write(b"x")
    items, skips = scan(tmp_path)
    assert not items
    assert "8 MB" in skips[0][1]


def test_fully_synthetic_dataset(tmp_path):
    inbox, organized, count = create_demo(tmp_path)
    assert count == len(SAMPLE_FILES) == 11
    assert set(EXPECTED) == set(SAMPLE_FILES)
    assert len(scan(inbox)[0]) == 11
    assert create_demo(tmp_path)[2] == 0
    assert organized.is_dir()


def test_invalid_inbox(tmp_path):
    with pytest.raises(ValueError):
        scan(tmp_path / "does-not-exist")
