"""Sequential stability soak for the real Step-2B service boundary.

Run this with the backend environment while the isolated service is running in
the foreground. It uses the same frozen corpus and the real production parser
route; it never restarts the service or hides a service exit.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

import httpx

try:
    import psutil
except ImportError:  # pragma: no cover - optional local diagnostics dependency
    psutil = None

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(ROOT / "benchmarks"))

from app.services.parsing_service import parse_document_result  # noqa: E402
from step2a_document_ai_benchmark import _make_corpus  # noqa: E402


def health(url: str) -> dict[str, Any]:
    try:
        response = httpx.get(f"{url.rstrip('/')}/health", timeout=2.0)
        payload = response.json()
        payload["http_status"] = response.status_code
        return payload
    except Exception as exc:
        return {"status": "unreachable", "error": f"{type(exc).__name__}: {str(exc)[:240]}"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--passes", type=int, default=3)
    parser.add_argument("--service-url", default="http://127.0.0.1:8765")
    parser.add_argument("--service-pid", type=int, default=0)
    parser.add_argument("--output", default=str(ROOT / "implementation_reports" / "STEP2B_SERVICE_SOAK.json"))
    args = parser.parse_args()

    os.environ.setdefault("DOCUMENT_AI_ENABLED", "true")
    corpus = _make_corpus(ROOT / "benchmarks" / ".step2a_frozen_corpus")
    observations: list[dict[str, Any]] = []
    resource_samples: list[dict[str, Any]] = []
    stop_monitor = threading.Event()

    def monitor() -> None:
        while not stop_monitor.is_set():
            current_health = health(args.service_url)
            item = {"at": time.time(), "health": current_health}
            if current_health.get("resources", {}).get("rss_mb") is not None:
                item["rss_mb"] = current_health["resources"]["rss_mb"]
            item["process"] = {"alive": current_health.get("process_alive") is True}
            if args.service_pid and psutil is not None:
                try:
                    process = psutil.Process(args.service_pid)
                    item["process"] = {"alive": process.is_running(), "rss_mb": round(process.memory_info().rss / 1024 / 1024, 2)}
                except (psutil.Error, OSError) as exc:
                    item["process"] = {"alive": False, "error": type(exc).__name__}
            resource_samples.append(item)
            stop_monitor.wait(1.0)

    monitor_thread = threading.Thread(target=monitor, name="document-ai-soak-monitor", daemon=True)
    monitor_thread.start()
    started = time.time()
    initial_health = health(args.service_url)
    try:
        for pass_number in range(1, args.passes + 1):
            for entry in corpus:
                path = Path(entry["path"])
                case_started = time.perf_counter()
                result: dict[str, Any] = {}
                error = None
                try:
                    result_obj = parse_document_result(str(path), path.suffix.lower(), filename=path.name)
                    if hasattr(result_obj, "model_dump"):
                        result = result_obj.model_dump()
                    elif hasattr(result_obj, "as_dict"):
                        result = result_obj.as_dict()
                    else:
                        result = result_obj.dict()
                except Exception as exc:  # record and continue; do not mask one bad document
                    error = f"{type(exc).__name__}: {str(exc)[:400]}"
                pages = result.get("pages") or []
                paddle_pages = [p for p in pages if (p.get("metadata") or {}).get("ocr_engine") == "paddle_ppocrv6"]
                fallback_pages = [p for p in pages if (p.get("metadata") or {}).get("fallback_from")]
                observations.append({
                    "pass": pass_number,
                    "document": path.name,
                    "path": str(path),
                    "success": error is None,
                    "error": error,
                    "latency_seconds": round(time.perf_counter() - case_started, 3),
                    "pages": len(pages),
                    "paddle_pages": len(paddle_pages),
                    "fallback_pages": len(fallback_pages),
                    "tables": len(result.get("tables") or []),
                    "health_after": health(args.service_url),
                })
    finally:
        stop_monitor.set()
        monitor_thread.join(timeout=3)

    final_health = health(args.service_url)
    alive_samples = [s["process"]["alive"] for s in resource_samples if "process" in s]
    rss_samples = [s["rss_mb"] for s in resource_samples if s.get("rss_mb") is not None]
    output = {
        "started_at": started,
        "finished_at": time.time(),
        "passes_requested": args.passes,
        "documents_per_pass": len(corpus),
        "initial_health": initial_health,
        "final_health": final_health,
        "observations": observations,
        "resource_samples": resource_samples,
        "summary": {
            "passes_completed": max((item["pass"] for item in observations), default=0),
            "requests_attempted": len(observations),
            "successful_requests": sum(1 for item in observations if item["success"]),
            "failed_requests": sum(1 for item in observations if not item["success"]),
            "paddle_pages": sum(item["paddle_pages"] for item in observations),
            "fallback_pages": sum(item["fallback_pages"] for item in observations),
            "structure_tables": sum(item["tables"] for item in observations),
            "service_alive_through_samples": bool(alive_samples) and all(alive_samples),
            "service_alive_at_end": final_health.get("process_alive") is True,
            "observed_process_restarts": 0 if alive_samples and all(alive_samples) else "possible_or_unavailable",
            "rss_start_mb": min(rss_samples) if rss_samples else None,
            "rss_peak_mb": max(rss_samples) if rss_samples else None,
            "rss_end_mb": rss_samples[-1] if rss_samples else None,
            "model_reinitializations": (final_health.get("stats") or {}).get("model_initializations"),
            "structure_model_initializations": (final_health.get("stats") or {}).get("structure_initializations"),
        },
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(output["summary"], indent=2))
    return 0 if output["summary"]["failed_requests"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
