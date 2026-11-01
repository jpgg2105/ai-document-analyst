"""Turn a client-supplied upload filename into a safe basename."""

from __future__ import annotations

from pathlib import PurePosixPath


def safe_filename(name: str) -> str:
    """Return the last path component of ``name``, with no directory parts.

    Uploads come with a client-chosen filename, which may contain ``../`` or a
    Windows path. Only the basename is kept, so writing it under a temp directory
    can't escape that directory. Raises ``ValueError`` if nothing usable remains.
    """
    base = PurePosixPath(name.replace("\\", "/")).name.strip()
    base = base.replace("\x00", "")
    if base in ("", ".", ".."):
        raise ValueError("Filename is required.")
    return base
