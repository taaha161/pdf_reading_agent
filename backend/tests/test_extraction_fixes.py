"""Tests for repeat-transaction merging and owner-password-only PDF handling."""
import io

import pytest
from pypdf import PdfWriter

from services import pdf_processor
from services.pdf_processor import PdfPasswordRequired, extract_text_from_pdf
from services.statement_agent import _merge_chunk_transactions

COFFEE = {"date": "2024-01-01", "description": "Coffee", "amount": "4.50", "type": "debit"}
RENT = {"date": "2024-01-02", "description": "Rent", "amount": "900.00", "type": "debit"}


def test_identical_rows_in_one_chunk_are_kept():
    assert _merge_chunk_transactions([[COFFEE, dict(COFFEE), dict(COFFEE)]]) == [COFFEE] * 3


def test_overlap_row_extracted_by_both_chunks_is_dropped_once():
    merged = _merge_chunk_transactions([[COFFEE, RENT], [dict(RENT), {**RENT, "date": "2024-01-03"}]])
    assert [t["date"] for t in merged] == ["2024-01-01", "2024-01-02", "2024-01-03"]


def test_extra_repeats_in_next_chunk_beyond_previous_count_are_kept():
    merged = _merge_chunk_transactions([[COFFEE], [dict(COFFEE), dict(COFFEE)]])
    assert len(merged) == 2


def _encrypted_pdf(user_password: str, owner_password: str) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.encrypt(user_password=user_password, owner_password=owner_password)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


@pytest.fixture
def no_datalab(monkeypatch):
    monkeypatch.delenv("DATALAB_API_KEY", raising=False)
    monkeypatch.setattr(pdf_processor, "_extract_text_scanned", lambda *a, **k: "")


def test_owner_password_only_pdf_opens_without_password(no_datalab):
    assert extract_text_from_pdf(_encrypted_pdf("", "owner-secret")) == ""


def test_user_password_pdf_still_requires_password(no_datalab):
    with pytest.raises(PdfPasswordRequired):
        extract_text_from_pdf(_encrypted_pdf("open-me", "owner-secret"))


def test_user_password_pdf_opens_with_correct_password(no_datalab):
    assert extract_text_from_pdf(_encrypted_pdf("open-me", "owner-secret"), password="open-me") == ""


def test_user_password_pdf_rejects_wrong_password(no_datalab):
    with pytest.raises(ValueError, match="Incorrect PDF password"):
        extract_text_from_pdf(_encrypted_pdf("open-me", "owner-secret"), password="nope")
