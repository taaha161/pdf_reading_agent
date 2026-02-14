"""Extract text from PDF: direct text extraction or OCR for scanned pages; optional AI vision."""
import base64
import io
import os
import tempfile

import pdfplumber
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


def extract_text_from_pdf(file_content: bytes, filename: str = "statement.pdf") -> str:
    """
    Load PDF, try text extraction first (pdfplumber, then pypdf fallback).
    If too little text per page, use OCR. Returns raw text string.
    """
    stream = io.BytesIO(file_content)
    text = _extract_text_direct(stream)
    stream.seek(0)
    pages = _count_pages(stream)
    if pages == 0:
        return ""
    # If pdfplumber got little or no text, try pypdf (handles some PDFs better)
    if not text or len(text.strip()) < 50:
        stream.seek(0)
        text = _extract_text_pypdf(stream)
    avg_chars = len(text) / pages if pages else 0
    if avg_chars < MIN_TEXT_PER_PAGE:
        # Scanned or image-only PDF: OCR + optional AI vision (use best result)
        text = _extract_text_scanned(file_content)
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


def _pdf_to_images(pdf_bytes: bytes) -> list[Image.Image]:
    """Convert PDF to list of PIL images at OCR_DPI."""
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp.flush()
            tmp_path = tmp.name
        return convert_from_path(tmp_path, dpi=OCR_DPI)
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
        return ""
    try:
        from groq import Groq
    except ImportError:
        return ""
    client = Groq(api_key=api_key)
    prompt = (
        "Extract all text from this bank statement or financial document image. "
        "Return the raw text exactly as you see it: dates, descriptions, amounts, debits, credits, "
        "account numbers, and any other visible text. Preserve the order and layout. Do not add commentary."
    )
    parts = []
    for i, img in enumerate(images):
        try:
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
        except Exception:
            continue
    return "\n\n".join(parts)


def _extract_text_scanned(pdf_bytes: bytes) -> str:
    """Get images from PDF, run OCR and optionally AI vision; return the best result."""
    images = _pdf_to_images(pdf_bytes)
    if not images:
        return ""
    ocr_text = ""
    try:
        ocr_text = _extract_text_ocr_from_images(images)
    except Exception as e:
        err_msg = str(e).strip()
        if "tesseract" in err_msg.lower() or "pytesseract" in err_msg.lower():
            raise RuntimeError(
                "OCR failed: Tesseract is required for scanned PDFs. "
                "Install it (e.g. brew install tesseract on macOS) and ensure it is on PATH."
            ) from e
        raise
    vision_text = _extract_text_vision(images)
    # Use vision result if it has more content than OCR (often better for camera scans)
    if vision_text and len(vision_text.strip()) > len(ocr_text.strip()):
        return vision_text.strip()
    return ocr_text or ""
