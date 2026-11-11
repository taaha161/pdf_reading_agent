"""Tests for chunked, parallel extraction with split-and-retry on truncated model output."""
import json
import re

import pytest

from google.genai.types import FinishReason

from services import statement_agent as sa


def _statement(n_rows: int) -> str:
    header = "| Date | Description | Debit | Credit | Balance |\n|---|---|---|---|---|\n"
    rows = "".join(f"| D{i:04d} | Row {i} payee | {i}.00 | | 0 |\n" for i in range(n_rows))
    return header + rows


def _rows_in(text: str) -> list[dict]:
    return [
        {"date": m.group(1), "description": f"Row {int(m.group(1)[1:])} payee", "amount": f"{int(m.group(1)[1:])}.00", "type": "debit", "category": "Other"}
        for m in re.finditer(r"^\| (D\d{4}) \|", text, re.M)
    ]


@pytest.fixture
def fake_gemini(monkeypatch):
    """Fake model: echoes every table row in the prompt, but truncates if more than max_rows."""
    calls: list[int] = []
    state = {"max_rows": 10_000}

    def fake(client, system, user_content, max_tokens=32768):
        rows = _rows_in(user_content)
        calls.append(len(rows))
        if len(rows) > state["max_rows"]:
            body = json.dumps(rows[: state["max_rows"]])
            return body[: len(body) // 2], FinishReason.MAX_TOKENS  # cut mid-array
        return json.dumps(rows) + "\nCURRENCY: PKR", FinishReason.STOP

    monkeypatch.setattr(sa, "_generate_with_reason", fake)
    monkeypatch.setattr(sa, "_get_client", lambda: object())
    return state, calls


def test_split_into_chunks_keeps_whole_lines_and_covers_text():
    text = _statement(500)
    chunks = sa._split_into_chunks(text, 2000)
    assert len(chunks) > 1
    assert all(c.endswith("\n") for c in chunks)
    assert all(len(c) <= 2000 for c in chunks)
    assert "".join(chunks) == text  # no overlap, nothing lost


def test_split_in_half_cuts_on_line_boundary():
    a, b = sa._split_in_half(_statement(10))
    assert a.endswith("\n") and a + b == _statement(10)


def test_all_rows_extracted_in_order_across_chunks(fake_gemini, monkeypatch):
    monkeypatch.setattr(sa, "EXTRACTION_CHUNK_CHARS", 3000)
    txs, currency = sa.extract_and_categorize(_statement(581))
    assert [t["date"] for t in txs] == [f"D{i:04d}" for i in range(581)]
    assert currency == "PKR"


def test_truncated_chunk_is_split_and_retried_not_dropped(fake_gemini, monkeypatch):
    state, calls = fake_gemini
    state["max_rows"] = 40
    monkeypatch.setattr(sa, "EXTRACTION_CHUNK_CHARS", 100_000)
    monkeypatch.setattr(sa, "EXTRACTION_MIN_SPLIT_CHARS", 100)
    txs, _ = sa.extract_and_categorize(_statement(200))
    assert len(txs) == 200
    assert len(calls) > 1  # retried with smaller halves


def test_progress_callback_reports_every_chunk(fake_gemini, monkeypatch):
    monkeypatch.setattr(sa, "EXTRACTION_CHUNK_CHARS", 2000)
    seen: list[tuple[int, int]] = []
    sa.extract_and_categorize(_statement(300), on_chunk=lambda i, n: seen.append((i, n)))
    n = seen[0][1]
    assert n > 1 and [i for i, _ in seen] == list(range(1, n + 1))


def test_identical_repeat_rows_across_chunk_boundary_are_kept(monkeypatch):
    """Same fee twice on one day, landing in different chunks, must yield two rows."""
    row = {"date": "02 Jul 2025", "description": "SMS fee", "amount": "5.00", "type": "debit", "category": "Fees & Charges"}

    def fake(client, system, user_content, max_tokens=32768):
        n = user_content.count("| 02 Jul 2025 | SMS fee |")
        return json.dumps([row] * n) + "\nCURRENCY: PKR", FinishReason.STOP

    monkeypatch.setattr(sa, "_generate_with_reason", fake)
    monkeypatch.setattr(sa, "_get_client", lambda: object())
    line = "| 02 Jul 2025 | SMS fee | 5.00 | | 0 |\n"
    monkeypatch.setattr(sa, "EXTRACTION_CHUNK_CHARS", len(line))
    txs, _ = sa.extract_and_categorize(line * 2)
    assert len(txs) == 2


def test_currency_parse_ignores_code_fence():
    assert sa._parse_currency_from_response("CURRENCY: PKR```") == "PKR"
