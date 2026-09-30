"""Minimal long-lived HTTP boundary for PaddleOCR 3.x and PP-StructureV3.

Run with the isolated Python 3.12 environment, for example:
    .venv-paddle312\\Scripts\\python.exe -m document_ai_service.server

The service accepts image bytes, not filesystem paths. This keeps the backend
portable and makes a later Docker/WSL deployment use the same contract.
"""

from __future__ import annotations

import base64
import gc
import io
import json
import logging
import os
import time
import threading
from html.parser import HTMLParser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List

import psutil
from PIL import Image

logger = logging.getLogger("coalintel.document_ai")
logging.basicConfig(level=os.environ.get("DOCUMENT_AI_LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s %(message)s")

# Windows CPU Paddle/PaddleX can reserve a very large virtual address space
# and its oneDNN path has exhibited native access violations during long mixed
# OCR/Structure runs. Keep the safe defaults conservative, while allowing a
# deployment to override them explicitly before process startup.
_cpu_threads = os.environ.get("DOCUMENT_AI_CPU_THREADS", "2")
os.environ.setdefault("OMP_NUM_THREADS", _cpu_threads)
os.environ.setdefault("MKL_NUM_THREADS", _cpu_threads)
os.environ.setdefault("FLAGS_paddle_num_threads", _cpu_threads)
if os.environ.get("DOCUMENT_AI_DISABLE_MKLDNN", "true").lower() in {"1", "true", "yes", "on"}:
    os.environ.setdefault("FLAGS_use_mkldnn", "0")


def _json_value(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, dict):
        return {str(k): _json_value(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _result_dict(result: Any) -> Dict[str, Any]:
    for attribute in ("json", "res"):
        try:
            value = getattr(result, attribute)
            if callable(value):
                value = value()
            if isinstance(value, dict):
                value = value.get("res", value)
                if isinstance(value, dict):
                    return _json_value(value)
        except Exception:
            continue
    if isinstance(result, dict):
        return _json_value(result.get("res", result))
    try:
        return _json_value(dict(result))
    except Exception:
        return {}


def _bbox(value: Any) -> List[float] | None:
    value = _json_value(value)
    if isinstance(value, list) and len(value) == 4 and all(isinstance(x, (int, float)) for x in value):
        return [float(x) for x in value]
    if isinstance(value, list) and value and all(isinstance(point, list) and len(point) >= 2 for point in value):
        points = [(float(point[0]), float(point[1])) for point in value]
        return [min(x for x, _ in points), min(y for _, y in points), max(x for x, _ in points), max(y for _, y in points)]
    return None


def _mean(values: list[Any]) -> float | None:
    numbers = [float(value) for value in values if isinstance(value, (int, float))]
    return sum(numbers) / len(numbers) if numbers else None


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._row is not None and self._cell is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row:
            self.rows.append(self._row)
            self._row = None


class PaddleDocumentAI:
    OCR_MODEL = "PP-OCRv6_medium_det + PP-OCRv6_medium_rec"
    OCR_ENGINE = "paddle_ppocrv6"
    STRUCTURE_ENGINE = "paddle_ppstructurev3"

    def __init__(self) -> None:
        self.process = psutil.Process(os.getpid())
        self.inference_lock = threading.Lock()
        self.stats_lock = threading.Lock()
        self.stats = {"requests_total": 0, "requests_completed": 0, "request_failures": 0, "queued_requests": 0, "ocr_requests": 0, "structure_requests": 0, "model_initializations": 0, "structure_initializations": 0}
        self.active_request: Dict[str, Any] | None = None
        self.last_error: str | None = None
        self.startup_rss_mb = self._resources()["rss_mb"]
        logger.info("document_ai_startup model_initialization_begin rss_mb=%.2f", self.startup_rss_mb)
        os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
        from paddleocr import PaddleOCR
        import paddle
        import paddleocr
        import paddlex

        self._paddle = paddle
        self.versions = {"paddlepaddle": paddle.__version__, "paddleocr": paddleocr.__version__, "paddlex": paddlex.__version__}
        self.ocr = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            device=os.environ.get("DOCUMENT_AI_DEVICE", "cpu"),
            engine="paddle",
        )
        self.stats["model_initializations"] += 1
        self.structure = None
        self._structure_lock = threading.Lock()
        logger.info("document_ai_startup ocr_ready=true rss_mb=%.2f versions=%s", self._resources()["rss_mb"], self.versions)

    def _resources(self) -> Dict[str, Any]:
        memory = self.process.memory_info()
        virtual = psutil.virtual_memory()
        return {"rss_mb": round(memory.rss / (1024 * 1024), 2), "vms_mb": round(memory.vms / (1024 * 1024), 2), "available_mb": round(virtual.available / (1024 * 1024), 2)}

    def _run_exclusive(self, kind: str, request_id: str, operation: Any) -> Dict[str, Any]:
        queued_at = time.perf_counter()
        with self.stats_lock:
            self.stats["requests_total"] += 1
            self.stats[f"{kind}_requests"] += 1
            self.stats["queued_requests"] += 1
        logger.info("document_ai_request queued request_id=%s kind=%s resources=%s", request_id, kind, self._resources())
        wait_started = time.perf_counter()
        with self.inference_lock:
            waited = time.perf_counter() - wait_started
            with self.stats_lock:
                self.stats["queued_requests"] -= 1
            started = time.perf_counter()
            self.active_request = {"request_id": request_id, "kind": kind, "queued_seconds": round(waited, 3), "started_at": time.time(), "rss_before_mb": self._resources()["rss_mb"]}
            logger.info("document_ai_request started request_id=%s kind=%s queued_seconds=%.3f active=%s", request_id, kind, waited, self.active_request)
            try:
                result = operation()
                with self.stats_lock:
                    self.stats["requests_completed"] += 1
                self.last_error = None
                logger.info("document_ai_request completed request_id=%s kind=%s latency_seconds=%.3f resources=%s", request_id, kind, time.perf_counter() - started, self._resources())
                return result
            except Exception as exc:
                with self.stats_lock:
                    self.stats["request_failures"] += 1
                self.last_error = f"{type(exc).__name__}: {str(exc)[:400]}"
                logger.exception("document_ai_request failed request_id=%s kind=%s latency_seconds=%.3f resources=%s", request_id, kind, time.perf_counter() - started, self._resources())
                raise
            finally:
                self.active_request = None
                gc.collect()

    def health(self) -> Dict[str, Any]:
        resources = self._resources()
        status = "ready" if self.ocr is not None else "unhealthy"
        if self.last_error and self.ocr is not None:
            status = "degraded"
        return {
            "status": status,
            "process_alive": True,
            "ocr_ready": self.ocr is not None,
            "structure_ready": self.structure is not None,
            "busy": self.active_request is not None,
            "active_request": self.active_request,
            "resources": resources,
            "startup_rss_mb": self.startup_rss_mb,
            "stats": dict(self.stats),
            "last_error": self.last_error,
            "device": os.environ.get("DOCUMENT_AI_DEVICE", "cpu"),
            "versions": self.versions,
            "models": {"ocr": self.OCR_MODEL, "structure": "PP-StructureV3 (current PaddleOCR 3.x models)"},
            "cuda_compiled": bool(self._paddle.is_compiled_with_cuda()),
        }

    @staticmethod
    def _decode_image(payload: Dict[str, Any]) -> tuple[Image.Image, int, Dict[str, Any]]:
        raw = base64.b64decode(payload["image_base64"], validate=True)
        image = Image.open(io.BytesIO(raw)).convert("RGB")
        return image, int(payload.get("page_number") or 1), payload.get("source_raster") or {}

    def _ocr_image_impl(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        image, page_number, source_raster = self._decode_image(payload)
        import tempfile
        path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
                path = handle.name
                image.save(handle, format="PNG")
            blocks: list[dict[str, Any]] = []
            for result in self.ocr.predict(path):
                data = _result_dict(result)
                texts = [str(value) for value in (data.get("rec_texts") or [])]
                scores = list(data.get("rec_scores") or [])
                boxes = list(data.get("rec_boxes") or data.get("rec_polys") or data.get("dt_polys") or [])
                for index, text in enumerate(texts):
                    if not text.strip():
                        continue
                    score = scores[index] if index < len(scores) and isinstance(scores[index], (int, float)) else None
                    block = {
                        "text": text,
                        "bbox": _bbox(boxes[index]) if index < len(boxes) else None,
                        "confidence": float(score) if score is not None else None,
                        "method": self.OCR_ENGINE,
                        "block_type": "TEXT",
                        "metadata": {"engine": self.OCR_ENGINE, "model": self.OCR_MODEL, "version": self.versions["paddleocr"], "source_raster": source_raster},
                    }
                    blocks.append(block)
            text = "\n".join(block["text"] for block in blocks)
            return {
                "status": "OK" if text.strip() else "EMPTY",
                "page_number": page_number,
                "text": text,
                "blocks": blocks,
                "confidence": _mean([block["confidence"] for block in blocks]),
                "engine": self.OCR_ENGINE,
                "model": self.OCR_MODEL,
                "version": self.versions["paddleocr"],
                "source_raster": source_raster,
                "warnings": [],
            }
        finally:
            if path:
                try:
                    os.unlink(path)
                except OSError:
                    pass

    def ocr_image(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        request_id = str(payload.get("request_id") or f"ocr-{time.time_ns()}")
        return self._run_exclusive("ocr", request_id, lambda: self._ocr_image_impl(payload))

    def _get_structure(self) -> Any:
        if self.structure is None:
            with self._structure_lock:
                if self.structure is None:
                    logger.info("document_ai_structure model_initialization_begin resources=%s", self._resources())
                    from paddleocr import PPStructureV3
                    self.structure = PPStructureV3(
                        device=os.environ.get("DOCUMENT_AI_DEVICE", "cpu"),
                        use_doc_orientation_classify=False,
                        use_doc_unwarping=False,
                        use_textline_orientation=False,
                        use_table_recognition=True,
                        use_formula_recognition=False,
                        use_chart_recognition=False,
                        engine="paddle",
                    )
                    self.stats["structure_initializations"] += 1
                    logger.info("document_ai_structure model_ready resources=%s", self._resources())
        return self.structure

    def _structure_image_impl(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        image, page_number, source_raster = self._decode_image(payload)
        import tempfile
        path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
                path = handle.name
                image.save(handle, format="PNG")
            tables: list[dict[str, Any]] = []
            for result in self._get_structure().predict(path):
                data = _result_dict(result)
                for table_index, raw_table in enumerate(data.get("table_res_list") or [], start=1):
                    table = _json_value(raw_table)
                    if not isinstance(table, dict):
                        continue
                    html = table.get("pred_html") if isinstance(table.get("pred_html"), str) else ""
                    parser = _TableParser()
                    parser.feed(html)
                    rows = parser.rows
                    raw_boxes = list(table.get("cell_box_list") or [])
                    cells: list[dict[str, Any]] = []
                    box_alignment = len(raw_boxes) == sum(len(row) for row in rows)
                    for row_index, row in enumerate(rows):
                        for column_index, value in enumerate(row):
                            flat_index = sum(len(previous) for previous in rows[:row_index]) + column_index
                            cell_bbox = _bbox(raw_boxes[flat_index]) if box_alignment else None
                            cells.append({
                                "row_index": row_index,
                                "column_index": column_index,
                                "value": value,
                                "raw_value": value,
                                "bounding_box": cell_bbox,
                                "bbox": cell_bbox,
                                "is_header": row_index == 0,
                                "extraction_method": self.STRUCTURE_ENGINE,
                                "source_raster": source_raster,
                            })
                    table_warnings = []
                    if not rows:
                        table_warnings.append("PP-StructureV3 returned a table region without parseable rows")
                    if raw_boxes and not box_alignment:
                        table_warnings.append("Cell boxes did not align with reconstructed HTML cells; geometry omitted")
                    ocr_pred = table.get("table_ocr_pred") or {}
                    tables.append({
                        "page_number": page_number,
                        "table_number": table_index,
                        "headers": rows[0] if rows else [],
                        "rows": rows[1:] if len(rows) > 1 else [],
                        "bounding_box": _bbox(table.get("table_region_bbox")),
                        "extraction_confidence": _mean(ocr_pred.get("rec_scores") or []),
                        "extraction_method": self.STRUCTURE_ENGINE,
                        "cells": cells,
                        "warnings": table_warnings,
                        "model": "PP-StructureV3",
                        "version": self.versions["paddleocr"],
                        "source_raster": source_raster,
                    })
            return {"status": "OK", "page_number": page_number, "tables": tables, "engine": self.STRUCTURE_ENGINE, "model": "PP-StructureV3", "version": self.versions["paddleocr"], "source_raster": source_raster, "warnings": [] if tables else ["No table structure detected"]}
        finally:
            if path:
                try:
                    os.unlink(path)
                except OSError:
                    pass

    def structure_image(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        request_id = str(payload.get("request_id") or f"structure-{time.time_ns()}")
        return self._run_exclusive("structure", request_id, lambda: self._structure_image_impl(payload))


_ENGINE: PaddleDocumentAI | None = None
_ENGINE_ERROR: str | None = None
try:
    _ENGINE = PaddleDocumentAI()
except Exception as exc:  # keep the process alive so /health explains readiness
    _ENGINE_ERROR = f"{type(exc).__name__}: {str(exc)[:400]}"
    logger.exception("Document AI model initialization failed")


def _health() -> Dict[str, Any]:
    if _ENGINE is None:
        return {"status": "unhealthy", "ocr_ready": False, "structure_ready": False, "error": _ENGINE_ERROR}
    return _ENGINE.health()


class Handler(BaseHTTPRequestHandler):
    server_version = "COALINTEL-DocumentAI/1.0"

    def _send(self, status: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError) as exc:
            # A timed-out backend/client may disconnect while Paddle is still
            # finishing. This is a request-level failure, not a service crash.
            logger.warning("document_ai_response_client_disconnected status=%s error=%s", status, type(exc).__name__)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            health = _health()
            self._send(HTTPStatus.OK if health.get("status") == "ready" else HTTPStatus.SERVICE_UNAVAILABLE, health)
            return
        self._send(HTTPStatus.NOT_FOUND, {"status": "FAILED", "error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path not in {"/v1/ocr", "/v1/structure"}:
            self._send(HTTPStatus.NOT_FOUND, {"status": "FAILED", "error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 30 * 1024 * 1024:
                raise ValueError("Invalid request size")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict) or not payload.get("image_base64"):
                raise ValueError("image_base64 is required")
            if _ENGINE is None:
                raise RuntimeError(_ENGINE_ERROR or "Document AI engine is unavailable")
            result = _ENGINE.ocr_image(payload) if self.path == "/v1/ocr" else _ENGINE.structure_image(payload)
            self._send(HTTPStatus.OK, result)
        except Exception as exc:
            logger.error("Document AI request failed: %s: %s", type(exc).__name__, str(exc)[:300])
            self._send(HTTPStatus.BAD_GATEWAY, {"status": "FAILED", "error": f"{type(exc).__name__}: {str(exc)[:400]}"})

    def log_message(self, format: str, *args: Any) -> None:
        logger.info("%s - %s", self.address_string(), format % args)


def main() -> int:
    logging.basicConfig(level=os.environ.get("DOCUMENT_AI_LOG_LEVEL", "INFO"))
    if _ENGINE is None:
        logger.error("Document AI service cannot start: OCR model is not ready: %s", _ENGINE_ERROR)
        return 2
    host = os.environ.get("DOCUMENT_AI_HOST", "127.0.0.1")
    # Render injects PORT at runtime.  DOCUMENT_AI_PORT remains an explicit
    # override for controlled deployments; when neither is present, preserve
    # the local development default of 8765.
    port = int(os.environ.get("DOCUMENT_AI_PORT") or os.environ.get("PORT") or "8765")
    server = ThreadingHTTPServer((host, port), Handler)
    logger.info("Document AI service listening on %s:%s; health=%s", host, port, _health().get("status"))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Document AI service stopping due to keyboard interrupt")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
