"""Tests for reading a statement's summary box (Gemini mocked)."""
from types import SimpleNamespace

from services.statement_meta import _excerpt, extract_statement_meta, normalize_meta


class _Client:
    def __init__(self, text=None, error=None):
        self.calls = []
        self._text, self._error = text, error
        self.models = SimpleNamespace(generate_content=self._generate)

    def _generate(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        return SimpleNamespace(text=self._text)


RAW = {
    "bank_name": "Chase", "account_last4": "1234", "account_type": "checking",
    "period_start": "2026-03-01", "period_end": "2026-03-31",
    "opening_balance": "8,240.15", "closing_balance": "10,243.29",
    "total_credits": "6,702.14", "total_debits": "-4,699.00", "account_count": 1,
}


def test_normalize_meta():
    meta = normalize_meta(RAW, "USD")
    assert meta == {
        "opening_balance": 8240.15, "closing_balance": 10243.29, "total_credits": 6702.14,
        "total_debits": 4699.0, "account_type": "checking", "bank_name": "Chase", "account_last4": "1234",
        "period_start": "2026-03-01", "period_end": "2026-03-31", "account_count": 1,
    }


def test_never_keeps_more_than_last_four_digits():
    assert normalize_meta({**RAW, "account_last4": "0001 2345 6789 4321"}, "USD")["account_last4"] == "4321"
    assert normalize_meta({**RAW, "account_last4": "x12"}, "USD")["account_last4"] is None


def test_dot_group_amounts_and_blanks():
    meta = normalize_meta({"opening_balance": "1.500.000", "closing_balance": "", "total_credits": "250.000,50"}, "IDR")
    assert meta["opening_balance"] == 1500000.0 and meta["total_credits"] == 250000.5
    assert meta["closing_balance"] is None and meta["total_debits"] is None


def test_bad_fields_are_cleaned():
    meta = normalize_meta({"account_type": "Business", "period_start": "March", "account_count": "two",
                           "period_end": "2026-01-01"}, None)
    assert meta["account_type"] == "other" and meta["period_start"] is None and meta["account_count"] == 1


def test_swapped_period_is_fixed():
    meta = normalize_meta({**RAW, "period_start": "2026-03-31", "period_end": "2026-03-01"}, "USD")
    assert (meta["period_start"], meta["period_end"]) == ("2026-03-01", "2026-03-31")


def test_extract_parses_fenced_json():
    client = _Client('```json\n{"bank_name": "Chase", "account_last4": "1234"}\n```')
    assert extract_statement_meta("statement text", client) == {"bank_name": "Chase", "account_last4": "1234"}


def test_extract_failure_returns_none():
    assert extract_statement_meta("statement text", _Client(error=RuntimeError("quota"))) is None
    assert extract_statement_meta("statement text", _Client("not json")) is None
    assert extract_statement_meta("   ", _Client("{}")) is None


def test_long_statement_sends_head_and_tail():
    text = "H" * 9000 + "M" * 50000 + "T" * 9000
    excerpt = _excerpt(text)
    assert excerpt.startswith("H" * 8000) and excerpt.endswith("T" * 8000) and "M" not in excerpt

