"""
Document parsing service.
Handles: .txt, .md (direct read), .pdf (pdfplumber, with pytesseract OCR fallback)
Also parses questionnaire files (CSV or PDF) into structured question lists.
"""
import csv
import io
import os
from typing import Optional


# ─── Text / Markdown ────────────────────────────────────────────────────────

def parse_text_file(file_bytes: bytes, encoding: str = "utf-8") -> str:
    """Read raw text from .txt or .md bytes."""
    try:
        return file_bytes.decode(encoding)
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1")


# ─── PDF ────────────────────────────────────────────────────────────────────

def _extract_pdf_text(file_bytes: bytes) -> Optional[str]:
    """Try pdfplumber first (text-based PDFs). Returns None if no text extracted."""
    try:
        import pdfplumber

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages_text = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text.strip())
        full_text = "\n\n".join(pages_text)
        return full_text if len(full_text.strip()) > 50 else None
    except Exception:
        return None


def _extract_pdf_ocr(file_bytes: bytes) -> str:
    """Fallback: use pytesseract OCR on each page image."""
    try:
        import fitz  # PyMuPDF
        import pytesseract
        from PIL import Image

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages_text = []
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            text = pytesseract.image_to_string(img)
            if text.strip():
                pages_text.append(text.strip())
        doc.close()
        return "\n\n".join(pages_text)
    except ImportError:
        # PyMuPDF not available; try PIL-based approach with PyPDF2
        return _extract_pdf_ocr_fallback(file_bytes)


def _extract_pdf_ocr_fallback(file_bytes: bytes) -> str:
    """Secondary OCR fallback: PyPDF2 for any remaining text."""
    try:
        import PyPDF2

        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        pages_text = []
        for page in reader.pages:
            text = page.extract_text()
            if text and text.strip():
                pages_text.append(text.strip())
        return "\n\n".join(pages_text)
    except Exception:
        return ""


def parse_pdf(file_bytes: bytes) -> tuple[str, str]:
    """
    Parse a PDF. Returns (extracted_text, file_type).
    file_type is 'pdf' for text-based, 'pdf_ocr' for OCR-processed.
    """
    text = _extract_pdf_text(file_bytes)
    if text:
        return text, "pdf"

    # Fallback to OCR
    text = _extract_pdf_ocr(file_bytes)
    return text or "(No extractable text found)", "pdf_ocr"


# ─── Universal Dispatcher ───────────────────────────────────────────────────

def parse_document(file_bytes: bytes, filename: str) -> tuple[str, str]:
    """
    Parse any supported document type.
    Returns (content_text, file_type).
    """
    ext = os.path.splitext(filename)[1].lower()

    if ext in (".txt", ".md"):
        content = parse_text_file(file_bytes)
        return content, ext.lstrip(".")

    if ext == ".pdf":
        return parse_pdf(file_bytes)

    # Default: treat as plain text
    content = parse_text_file(file_bytes)
    return content, "txt"


# ─── Questionnaire Parsing ──────────────────────────────────────────────────

def parse_questionnaire(file_bytes: bytes, filename: str) -> list[dict]:
    """
    Parse questionnaire file. Returns the raw text content as a single entry.
    Question identification and numbering is delegated to the LLM at generation time.
    """
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".csv":
        # Convert CSV rows into numbered plain text so the LLM can read them naturally
        content = file_bytes.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(content))
        lines = []
        for i, row in enumerate(reader, 1):
            lower_row = {k.lower().strip(): v for k, v in row.items() if k}
            text = (
                lower_row.get("text")
                or lower_row.get("question")
                or lower_row.get("question text")
                or lower_row.get("question_text")
                or ""
            ).strip()
            if text:
                lines.append(f"{i}. {text}")
        raw = "\n".join(lines)
    elif ext == ".pdf":
        raw, _ = parse_pdf(file_bytes)
    else:
        raw = parse_text_file(file_bytes)

    return [{"number": 1, "text": raw.strip()}]
