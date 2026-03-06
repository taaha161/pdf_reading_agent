"""Extract text from PDF: Datalab when configured; otherwise direct text or OCR for scanned pages. No AI vision."""
import io
import logging
import os
import tempfile
import time

import pdfplumber

logger = logging.getLogger("pdf_processor")
from pypdf import PdfReader
from pdf2image import convert_from_path
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter

try:
    import cv2
    import numpy as np
    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False

# Chars per page below this → treat as scanned and use OCR
MIN_TEXT_PER_PAGE = 100

# OCR: higher DPI helps camera-scanned / hand-scanned / low-quality pages
OCR_DPI = 350
# Tesseract PSM 3 = fully automatic page segmentation (good for documents)
TESSERACT_PSM = 3

def extract_text_from_pdf(
    file_content: bytes,
    filename: str = "statement.pdf",
    scanned_method: str | None = None,
) -> str:
    """
    When DATALAB_API_KEY is set, use only Datalab Convert API (PDF -> markdown).
    Otherwise: try direct text extraction (pdfplumber, then pypdf); if too little text per page,
    use scanned path with OCR only. scanned_method: "ocr" | None (auto). No AI vision.
    Returns raw text string.
    """
    t0 = time.perf_counter()
    logger.info("extract_text_from_pdf: start, filename=%s, size=%d bytes, scanned_method=%s", filename, len(file_content), scanned_method or "auto")

    if os.environ.get("DATALAB_API_KEY", "").strip():
        try:
            from services.datalab_client import convert_pdf_to_markdown
            text = convert_pdf_to_markdown(file_content, filename or "statement.pdf")
            logger.info("extract_text_from_pdf: Datalab done, len=%d (%.2f s)", len(text), time.perf_counter() - t0)
            return text or ""
        except Exception as e:
            logger.warning("extract_text_from_pdf: Datalab failed (%s)", e)
            return ""

    stream = io.BytesIO(file_content)
    text = _extract_text_direct(stream)
    stream.seek(0)
    pages = _count_pages(stream)
    logger.info("extract_text_from_pdf: pdfplumber text len=%d, pages=%d (%.2f s)", len(text), pages, time.perf_counter() - t0)
    if pages == 0:
        return ""
    # If pdfplumber got little or no text, try pypdf (handles some PDFs better)
    if not text or len(text.strip()) < 50:
        stream.seek(0)
        t1 = time.perf_counter()
        text = _extract_text_pypdf(stream)
        logger.info("extract_text_from_pdf: pypdf fallback, len=%d (%.2f s)", len(text), time.perf_counter() - t1)
    avg_chars = len(text) / pages if pages else 0
    if avg_chars < MIN_TEXT_PER_PAGE:
        logger.info("extract_text_from_pdf: low text per page (%.0f), using scanned path", avg_chars)
        text = _extract_text_scanned(file_content, scanned_method=scanned_method)
    else:
        logger.info("extract_text_from_pdf: using direct text, total len=%d (%.2f s)", len(text), time.perf_counter() - t0)
    return text or ""


def _count_pages(stream: io.BytesIO) -> int:
    try:
        with pdfplumber.open(stream) as pdf:
            return len(pdf.pages)
    except Exception:
        pass
    try:
        stream.seek(0)
        return len(PdfReader(stream).pages)
    except Exception:
        return 0


def _extract_text_direct(stream: io.BytesIO) -> str:
    parts = []
    try:
        with pdfplumber.open(stream) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    parts.append(t)
    except Exception:
        pass
    return "\n".join(parts)


def _extract_text_pypdf(stream: io.BytesIO) -> str:
    """Fallback: extract text using pypdf (works on some PDFs where pdfplumber fails)."""
    parts = []
    try:
        reader = PdfReader(stream)
        for page in reader.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
    except Exception:
        pass
    return "\n".join(parts)


def _deskew_image(img: Image.Image) -> Image.Image:
    """Optional: deskew image using OpenCV (helps camera photos taken at an angle)."""
    if not _CV2_AVAILABLE:
        return img
    try:
        arr = np.array(img)
        if len(arr.shape) == 3:
            gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        else:
            gray = arr
        coords = np.column_stack(np.where(gray < 128))
        if len(coords) < 100:
            return img
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle
        elif angle > 45:
            angle = angle - 90
        if abs(angle) < 0.5:
            return img
        (h, w) = arr.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            arr, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )
        return Image.fromarray(rotated)
    except Exception:
        return img


def _preprocess_image_for_ocr(img: Image.Image) -> Image.Image:
    """
    Preprocess a PIL image to improve OCR on camera-scanned or poor-quality pages:
    optional deskew, grayscale, contrast, sharpen, and optionally upscale small images.
    """
    img = _deskew_image(img)
    if img.mode != "L":
        img = img.convert("L")
    # Boost contrast (helps shadows/uneven lighting and faint hand-scanned text)
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.2)
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.6)
    # Upscale small images so Tesseract has enough resolution (hand-scanned often benefits from more pixels)
    w, h = img.size
    min_side = 1500
    if min(w, h) < min_side and min(w, h) > 0:
        scale = min_side / min(w, h)
        new_size = (int(w * scale), int(h * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    return img


def _pdf_to_images(pdf_bytes: bytes, dpi: int | None = None) -> list[Image.Image]:
    """Convert PDF to list of PIL images. dpi defaults to OCR_DPI."""
    use_dpi = dpi if dpi is not None else OCR_DPI
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp.flush()
            tmp_path = tmp.name
        return convert_from_path(tmp_path, dpi=use_dpi)
    except Exception as e:
        err_msg = str(e).strip()
        if "poppler" in err_msg.lower() or "page count" in err_msg.lower():
            raise RuntimeError(
                "PDF to image failed: poppler is required. "
                "Install it (e.g. brew install poppler on macOS, apt install poppler-utils on Linux)."
            ) from e
        raise RuntimeError(f"PDF to image failed: {err_msg}") from e
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception:
                pass


def _extract_text_ocr_from_images(images: list[Image.Image]) -> str:
    """Run Tesseract OCR on preprocessed images."""
    tess_config = f"--psm {TESSERACT_PSM}"
    parts = []
    for img in images:
        img = _preprocess_image_for_ocr(img)
        text = pytesseract.image_to_string(img, config=tess_config)
        if text:
            parts.append(text)
    return "\n".join(parts)


def _extract_text_scanned(pdf_bytes: bytes, scanned_method: str | None = None) -> str:
    """Get images from PDF and run OCR only. scanned_method: \"ocr\" | None (auto). No AI vision; Datalab is used when DATALAB_API_KEY is set (see extract_text_from_pdf)."""
    t0 = time.perf_counter()
    images = _pdf_to_images(pdf_bytes, dpi=OCR_DPI)
    logger.info("extract_text_scanned: PDF -> %d images, dpi=%d (%.2f s)", len(images), OCR_DPI, time.perf_counter() - t0)
    if not images:
        return ""
    try:
        ocr_text = _extract_text_ocr_from_images(images)
        logger.info("extract_text_scanned: OCR done, len=%d (%.2f s total)", len(ocr_text), time.perf_counter() - t0)
        return ocr_text or ""
    except Exception as e:
        err_msg = str(e).strip()
        if "tesseract" in err_msg.lower() or "pytesseract" in err_msg.lower():
            raise RuntimeError(
                "OCR failed: Tesseract is required for scanned PDFs. "
                "Install it (e.g. brew install tesseract on macOS) and ensure it is on PATH."
            ) from e
        raise
