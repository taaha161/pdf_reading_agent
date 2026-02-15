"""Extract text from PDF: direct text extraction or OCR for scanned pages; optional AI vision."""
import base64
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

# OCR: higher DPI helps camera-scanned / low-quality pages
OCR_DPI = 300
# Tesseract PSM 3 = fully automatic page segmentation (good for documents)
TESSERACT_PSM = 3

# Vision: Groq model for image-based extraction (max 5 images per request, 4MB base64 per image)
GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
VISION_MAX_PIXELS_LONG_SIDE = 2000  # resize to stay under 4MB base64
VISION_JPEG_QUALITY = 85
# For scanned PDFs with this many pages or fewer, skip OCR and use vision only (OCR is very slow on camera scans)
VISION_ONLY_MAX_PAGES = 5


def extract_text_from_pdf(
    file_content: bytes,
    filename: str = "statement.pdf",
    scanned_method: str | None = None,
) -> str:
    """
    Load PDF, try text extraction first (pdfplumber, then pypdf fallback).
    If too little text per page, use scanned path. scanned_method: "ocr" | "vision" | None (auto).
    Returns raw text string.
    """
    t0 = time.perf_counter()
    logger.info("extract_text_from_pdf: start, filename=%s, size=%d bytes, scanned_method=%s", filename, len(file_content), scanned_method or "auto")
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
    # Boost contrast (helps shadows/uneven lighting from camera)
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(1.5)
    # Upscale small images so Tesseract has enough resolution
    w, h = img.size
    min_side = 1200
    if min(w, h) < min_side and min(w, h) > 0:
        scale = min_side / min(w, h)
        new_size = (int(w * scale), int(h * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    return img


def _pdf_to_images(pdf_bytes: bytes, dpi: int | None = None) -> list[Image.Image]:
    """Convert PDF to list of PIL images. dpi defaults to OCR_DPI; use lower (e.g. 150) for vision-only to speed up."""
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


def _image_to_base64_jpeg(img: Image.Image, max_long_side: int = VISION_MAX_PIXELS_LONG_SIDE) -> str:
    """Resize if needed and encode as JPEG base64 for vision API (under 4MB)."""
    w, h = img.size
    if max(w, h) > max_long_side:
        ratio = max_long_side / max(w, h)
        new_size = (int(w * ratio), int(h * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    if img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=VISION_JPEG_QUALITY, optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _extract_text_vision(images: list[Image.Image]) -> str:
    """Use Groq vision model to extract text from each page image. Requires GROQ_API_KEY."""
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        logger.info("extract_text_vision: skipped (no GROQ_API_KEY)")
        return ""
    try:
        from groq import Groq
    except ImportError:
        logger.info("extract_text_vision: skipped (groq not installed)")
        return ""
    client = Groq(api_key=api_key)
    logger.info("extract_text_vision: calling Groq for %d page(s)", len(images))
    prompt = (
        "Extract all text from this bank statement or financial document image. "
        "Include: dates, descriptions, debit/credit amounts, account numbers, headers, and any other visible text. "
        "Preserve the order and layout. "
        "IMPORTANT: In transaction tables, include ONLY rows that are actual transactions (each has a date, description, and an amount that is a debit or credit). "
        "Do NOT include running balance columns or rows that show only a balance figure (e.g. 'Balance 1,234.56' or a column that repeats the balance after each transaction). "
        "If there is a 'Balance' column, omit it from each transaction row; only keep date, description, and amount. "
        "Do not add commentary."
    )
    parts = []
    for i, img in enumerate(images):
        try:
            t_page = time.perf_counter()
            b64 = _image_to_base64_jpeg(img)
            url = f"data:image/jpeg;base64,{b64}"
            completion = client.chat.completions.create(
                model=GROQ_VISION_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": url}},
                        ],
                    }
                ],
                temperature=0,
                max_tokens=4096,
            )
            content = (completion.choices[0].message.content or "").strip()
            if content:
                parts.append(content)
            logger.info("extract_text_vision: page %d/%d done (%.2f s)", i + 1, len(images), time.perf_counter() - t_page)
        except Exception as e:
            logger.warning("extract_text_vision: page %d failed: %s", i + 1, e)
            continue
    return "\n\n".join(parts)


def _extract_text_scanned(pdf_bytes: bytes, scanned_method: str | None = None) -> str:
    """Get images from PDF. scanned_method: "ocr" | "vision" | None (auto). When "ocr" use only OCR; when "vision" use only AI vision; when None use auto (vision-only for few pages, else OCR+vision and pick best)."""
    t0 = time.perf_counter()
    num_pages = _count_pages(io.BytesIO(pdf_bytes))
    force_ocr = (scanned_method or "").strip().lower() == "ocr"
    force_vision = (scanned_method or "").strip().lower() == "vision"
    if not force_ocr and not force_vision:
        vision_only = num_pages <= VISION_ONLY_MAX_PAGES
    else:
        vision_only = force_vision
    dpi = 150 if vision_only or force_vision else OCR_DPI
    images = _pdf_to_images(pdf_bytes, dpi=dpi)
    logger.info("extract_text_scanned: PDF -> %d images, dpi=%d, force_ocr=%s force_vision=%s (%.2f s)", len(images), dpi, force_ocr, force_vision, time.perf_counter() - t0)
    if not images:
        return ""
    if force_vision or (vision_only and not force_ocr):
        logger.info("extract_text_scanned: vision path (%d pages)", len(images))
        vision_text = _extract_text_vision(images)
        logger.info("extract_text_scanned: vision done, len=%d (%.2f s total)", len(vision_text), time.perf_counter() - t0)
        return vision_text.strip() if vision_text else ""
    if force_ocr:
        logger.info("extract_text_scanned: OCR-only path (%d pages)", len(images))
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
    # Auto: run both, pick best
    ocr_text = ""
    try:
        t1 = time.perf_counter()
        ocr_text = _extract_text_ocr_from_images(images)
        logger.info("extract_text_scanned: OCR done, len=%d (%.2f s)", len(ocr_text), time.perf_counter() - t1)
    except Exception as e:
        err_msg = str(e).strip()
        if "tesseract" in err_msg.lower() or "pytesseract" in err_msg.lower():
            raise RuntimeError(
                "OCR failed: Tesseract is required for scanned PDFs. "
                "Install it (e.g. brew install tesseract on macOS) and ensure it is on PATH."
            ) from e
        raise
    t2 = time.perf_counter()
    vision_text = _extract_text_vision(images)
    if vision_text:
        logger.info("extract_text_scanned: vision done, len=%d (%.2f s)", len(vision_text), time.perf_counter() - t2)
    if vision_text and len(vision_text.strip()) > len(ocr_text.strip()):
        logger.info("extract_text_scanned: using vision result (%.2f s total)", time.perf_counter() - t0)
        return vision_text.strip()
    logger.info("extract_text_scanned: using OCR result (%.2f s total)", time.perf_counter() - t0)
    return ocr_text or ""
