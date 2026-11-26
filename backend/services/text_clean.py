"""Plain-text cleanup for transaction descriptions."""
import re
import unicodedata

_SPACES = re.compile(r"\s+")


def clean_description(value) -> str:
    """Drop statement icons and other non-ASCII symbols; fold accents to plain letters.

    Card statements print glyphs beside some rows (CIBC Aeroplan uses ✈ and →). They
    end up in the extracted text and break imports into accounting tools, which
    expect plain characters. "CAFÉ" becomes "CAFE"; ordinary punctuation (# & ' * / -)
    is kept because it is part of merchant names.
    """
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if " " <= ch <= "~" or ch.isspace())
    return _SPACES.sub(" ", text).strip()
