"""Oversized / slow PDFs get a clear, actionable error; bulk purge casts job ids to uuid."""
import io
from contextlib import contextmanager
from unittest.mock import patch

import pytest
from pypdf import PdfWriter

import main
import store
from services import pdf_processor
from services.pdf_processor import PdfExtractionTimeout, PdfTooManyPages, extract_text_from_pdf


def _pdf(pages: int = 1) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def test_count_pdf_pages():
    assert pdf_processor.count_pdf_pages(_pdf(3)) == 3
    assert pdf_processor.count_pdf_pages(b"not a pdf") == 0


def test_pdf_over_page_limit_is_rejected_before_datalab(monkeypatch):
    monkeypatch.setenv("DATALAB_API_KEY", "x")
    monkeypatch.setattr(pdf_processor, "MAX_PDF_PAGES", 2)
    with patch("services.datalab_client.convert_pdf_to_markdown") as convert:
        with pytest.raises(PdfTooManyPages) as exc:
            extract_text_from_pdf(_pdf(3))
    convert.assert_not_called()
    assert exc.value.pages == 3 and exc.value.max_pages == 2


def test_datalab_timeout_raises_extraction_timeout(monkeypatch):
    monkeypatch.setenv("DATALAB_API_KEY", "x")
    with patch("services.datalab_client.convert_pdf_to_markdown", side_effect=TimeoutError("slow")):
        with pytest.raises(PdfExtractionTimeout):
            extract_text_from_pdf(_pdf(1))


def test_other_datalab_failures_still_return_empty(monkeypatch):
    monkeypatch.setenv("DATALAB_API_KEY", "x")
    with patch("services.datalab_client.convert_pdf_to_markdown", side_effect=RuntimeError("boom")):
        assert extract_text_from_pdf(_pdf(1)) == ""


def test_pdf_error_maps_too_many_pages():
    e = main._pdf_error(PdfTooManyPages(1560, 300))
    assert e.status_code == 422
    assert e.detail["code"] == "PDF_TOO_MANY_PAGES"
    assert "1,560 pages" in e.detail["detail"] and "split" in e.detail["detail"]


def test_pdf_error_maps_timeout():
    e = main._pdf_error(PdfExtractionTimeout("slow"))
    assert e.status_code == 422
    assert e.detail["code"] == "PDF_EXTRACTION_TIMEOUT"
    assert "split" in e.detail["detail"]


def test_purge_jobs_data_casts_ids_to_uuid_array(monkeypatch):
    executed = []

    class FakeCursor:
        rowcount = 2

        def execute(self, sql, params):
            executed.append((sql, params))

    @contextmanager
    def fake_cursor():
        yield FakeCursor()

    monkeypatch.setattr(store, "_cursor", fake_cursor)
    ids = ["18070945-24c8-4c79-82bd-812c41efc683", "22d8e098-5c78-4ea9-9ef4-3a2eb89b7c35"]
    assert store.purge_jobs_data(ids, "user-1") == 2
    sql, params = executed[0]
    assert "ANY(%s::uuid[])" in sql
    assert params == (ids, "user-1")
