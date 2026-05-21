"""
PDF generation utilities for OmniSight reports.

Thai font strategy:
  1. Bundled Leelawadee TTF (backend/app/assets/fonts/) — always available
  2. Falls back to Helvetica (ReportLab built-in) if TTF missing

Usage:
    from app.core.pdf_utils import get_font, get_font_bold, BODY_SIZE, HEADER_SIZE
    Paragraph("สวัสดี", ParagraphStyle("n", fontName=get_font(), fontSize=BODY_SIZE))
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

# Font constants — use everywhere so there's one place to change
BODY_SIZE = 9
HEADER_SIZE = 10
TITLE_SIZE = 14

_FONT_DIR = Path(__file__).parent.parent / "assets" / "fonts"
_FONT_REGULAR = _FONT_DIR / "Leelawadee.ttf"
_FONT_BOLD = _FONT_DIR / "Leelawadee-Bold.ttf"

_REGISTERED = False


def _register() -> bool:
    """Register Leelawadee TTF with ReportLab once. Returns True if successful."""
    global _REGISTERED
    if _REGISTERED:
        return True
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        if _FONT_REGULAR.exists():
            pdfmetrics.registerFont(TTFont("Leelawadee", str(_FONT_REGULAR)))
            if _FONT_BOLD.exists():
                pdfmetrics.registerFont(TTFont("Leelawadee-Bold", str(_FONT_BOLD)))
            _REGISTERED = True
            logger.debug("Leelawadee TTF registered for PDF output")
            return True
        logger.warning("Leelawadee.ttf not found at %s — Thai text will render as boxes", _FONT_REGULAR)
        return False
    except Exception as exc:
        logger.warning("Could not register Thai font: %s", exc)
        return False


@lru_cache(maxsize=1)
def get_font() -> str:
    """Return the registered Thai-capable font name (or Helvetica fallback)."""
    return "Leelawadee" if _register() else "Helvetica"


@lru_cache(maxsize=1)
def get_font_bold() -> str:
    """Return bold variant of the Thai-capable font (or Helvetica-Bold fallback)."""
    _register()
    if _REGISTERED and _FONT_BOLD.exists():
        return "Leelawadee-Bold"
    return "Helvetica-Bold"
