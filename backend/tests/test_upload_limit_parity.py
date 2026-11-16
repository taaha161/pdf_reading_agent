"""Upload size limits are written in three places; fail if they drift apart."""
import re
from pathlib import Path

import main

ROOT = Path(__file__).resolve().parents[2]
MB = 1024 * 1024


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_frontend_limits_match_backend():
    src = _read("frontend/src/lib/fileSize.js")
    found = {
        name: int(mb)
        for name, mb in re.findall(r"export const (MAX_FILE_BYTES_\w+) = (\d+) \* MB;", src)
    }
    assert found == {
        "MAX_FILE_BYTES_ANON": main.MAX_FILE_SIZE // MB,
        "MAX_FILE_BYTES_SIGNED_IN": main.MAX_FILE_SIZE_SIGNED_IN // MB,
        "MAX_FILE_BYTES_PAID": main.MAX_FILE_SIZE_PAID // MB,
    }


def test_marketing_limits_match_backend():
    src = _read("marketing/src/consts.ts")
    found = {name: int(mb) for name, mb in re.findall(r"export const (MAX_UPLOAD_MB_\w+) = (\d+);", src)}
    assert found == {
        "MAX_UPLOAD_MB_GUEST": main.MAX_FILE_SIZE // MB,
        "MAX_UPLOAD_MB_FREE_ACCOUNT": main.MAX_FILE_SIZE_SIGNED_IN // MB,
        "MAX_UPLOAD_MB_PAID": main.MAX_FILE_SIZE_PAID // MB,
    }
