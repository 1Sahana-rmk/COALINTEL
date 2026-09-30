"""Small HTTP client for the isolated Python 3.12 Document AI service.

The backend deliberately knows only this normalized contract. PaddleOCR and
PP-StructureV3 response objects remain inside the companion service process.
"""

from __future__ import annotations

import base64
import logging
import uuid
from typing import Any, Dict, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)


class DocumentAIError(RuntimeError):
    """A service availability, timeout, protocol, or inference failure."""


class DocumentAIClient:
    def __init__(self, *, base_url: Optional[str] = None):
        configured_url = (base_url or settings.DOCUMENT_AI_URL).strip()
        # Render's `fromService.property: hostport` intentionally returns a
        # scheme-less private-network address.  Local configuration continues
        # to use the existing http:// URL form.
        if configured_url and "://" not in configured_url:
            configured_url = f"http://{configured_url}"
        self.base_url = configured_url.rstrip("/")

    @property
    def enabled(self) -> bool:
        return bool(settings.DOCUMENT_AI_ENABLED)

    def _timeout(self, seconds: float) -> httpx.Timeout:
        return httpx.Timeout(seconds, connect=settings.DOCUMENT_AI_CONNECT_TIMEOUT_SECONDS)

    def _post(self, path: str, payload: Dict[str, Any], timeout_seconds: float) -> Dict[str, Any]:
        try:
            response = httpx.post(
                f"{self.base_url}{path}",
                json=payload,
                timeout=self._timeout(timeout_seconds),
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise DocumentAIError(f"Document AI request failed: {type(exc).__name__}: {str(exc)[:240]}") from exc
        if not isinstance(data, dict):
            raise DocumentAIError("Document AI returned a non-object response")
        if data.get("status") == "FAILED":
            raise DocumentAIError(str(data.get("error") or "Document AI inference failed"))
        return data

    def health(self) -> Dict[str, Any]:
        try:
            response = httpx.get(f"{self.base_url}/health", timeout=self._timeout(settings.DOCUMENT_AI_CONNECT_TIMEOUT_SECONDS))
            response.raise_for_status()
            payload = response.json()
            return payload if isinstance(payload, dict) else {"status": "invalid"}
        except (httpx.HTTPError, ValueError) as exc:
            raise DocumentAIError(f"Document AI health check failed: {type(exc).__name__}: {str(exc)[:240]}") from exc

    def _image_payload(self, image_bytes: bytes, page_number: int, source_raster: Dict[str, Any] | None, filename: str | None) -> Dict[str, Any]:
        return {
            "request_id": str(uuid.uuid4()),
            "image_base64": base64.b64encode(image_bytes).decode("ascii"),
            "page_number": page_number,
            "source_raster": source_raster or {},
            "filename": filename,
        }

    def ocr(self, image_bytes: bytes, *, page_number: int, source_raster: Dict[str, Any] | None = None, filename: str | None = None) -> Dict[str, Any]:
        return self._post("/v1/ocr", self._image_payload(image_bytes, page_number, source_raster, filename), settings.DOCUMENT_AI_OCR_TIMEOUT_SECONDS)

    def structure(self, image_bytes: bytes, *, page_number: int, source_raster: Dict[str, Any] | None = None, filename: str | None = None) -> Dict[str, Any]:
        return self._post("/v1/structure", self._image_payload(image_bytes, page_number, source_raster, filename), settings.DOCUMENT_AI_STRUCTURE_TIMEOUT_SECONDS)


_CLIENT: DocumentAIClient | None = None


def get_document_ai_client() -> DocumentAIClient:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = DocumentAIClient()
    return _CLIENT


def reset_document_ai_client() -> None:
    """Test/development seam; does not affect the remote service process."""
    global _CLIENT
    _CLIENT = None
