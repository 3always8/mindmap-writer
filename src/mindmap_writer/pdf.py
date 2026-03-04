from __future__ import annotations

import base64
import io

import pymupdf
from PIL import Image


def load_pdf_as_images(
    pdf_path: str,
    dpi: int = 150,
    quality: int = 85,
) -> list[str]:
    """Load PDF and convert each page to a base64-encoded JPEG string."""
    doc = pymupdf.open(pdf_path)
    page_images: list[str] = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=dpi)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
        page_images.append(b64)

    doc.close()
    return page_images
