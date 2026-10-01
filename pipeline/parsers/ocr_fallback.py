"""
OCR Fallback Parser stub.
Used ONLY if a PDF has no extractable text layer and OCR is explicitly enabled.
Kept behind feature flag so heavy OCR dependencies are not required by default.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Union

logger = logging.getLogger(__name__)

ENABLE_OCR = os.getenv("ENABLE_OCR", "false").lower() in ("true", "1", "yes")


class OCRFallbackParser:
    def __init__(self, file_path: Union[str, Path]):
        self.file_path = Path(file_path)

    def parse(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Execute OCR extraction. Raises RuntimeError if OCR is not enabled.
        """
        if not ENABLE_OCR:
            raise RuntimeError(
                f"OCR parsing requested for {self.file_path.name} but OCR is disabled. "
                f"Set ENABLE_OCR=true and ensure OCR dependencies (tesseract/easyocr) are installed."
            )

        raise NotImplementedError(
            "OCR extraction engine is not configured in this environment. "
            "Please ensure the factsheet PDF has a valid digital text layer."
        )
