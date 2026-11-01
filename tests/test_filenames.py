import pytest

from src.api.filenames import safe_filename


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("report.pdf", "report.pdf"),
        ("../../etc/passwd.txt", "passwd.txt"),
        ("/abs/path/notes.md", "notes.md"),
        ("..\\..\\windows\\evil.docx", "evil.docx"),
        ("C:\\Users\\me\\doc.pdf", "doc.pdf"),
    ],
)
def test_keeps_only_the_basename(raw, expected):
    assert safe_filename(raw) == expected


@pytest.mark.parametrize("raw", ["", "..", ".", "  ", "dir/.."])
def test_rejects_names_with_no_basename(raw):
    with pytest.raises(ValueError):
        safe_filename(raw)
