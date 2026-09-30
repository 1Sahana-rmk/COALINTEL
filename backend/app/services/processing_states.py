"""Persisted state machine for document processing."""
from typing import Dict, Set

PROCESSING_STATES = {"DISCOVERED", "DOWNLOADING", "DOWNLOADED", "CLASSIFYING", "EXTRACTING", "OCR", "TABLE_EXTRACTION", "VALIDATING", "READY", "DOWNLOAD_FAILED", "OCR_FAILED", "UNSUPPORTED_FORMAT", "EXTRACTION_FAILED", "VALIDATION_WARNING", "REVIEW_RECOMMENDED"}
TRANSITIONS: Dict[str, Set[str]] = {
    "DISCOVERED": {"DOWNLOADING", "DOWNLOADED", "UNSUPPORTED_FORMAT", "DOWNLOAD_FAILED"},
    "DOWNLOADING": {"DOWNLOADED", "DOWNLOAD_FAILED"}, "DOWNLOADED": {"CLASSIFYING", "EXTRACTING", "UNSUPPORTED_FORMAT"},
    "CLASSIFYING": {"EXTRACTING", "OCR", "EXTRACTION_FAILED"}, "EXTRACTING": {"OCR", "TABLE_EXTRACTION", "VALIDATING", "EXTRACTION_FAILED"},
    "OCR": {"TABLE_EXTRACTION", "VALIDATING", "OCR_FAILED", "EXTRACTION_FAILED"}, "TABLE_EXTRACTION": {"VALIDATING", "EXTRACTION_FAILED"},
    "VALIDATING": {"READY", "VALIDATION_WARNING", "REVIEW_RECOMMENDED"}, "VALIDATION_WARNING": {"READY", "REVIEW_RECOMMENDED"},
    "REVIEW_RECOMMENDED": {"VALIDATING", "READY"}, "READY": {"CLASSIFYING", "EXTRACTING"}, "DOWNLOAD_FAILED": {"DOWNLOADING"},
    "OCR_FAILED": {"OCR", "REVIEW_RECOMMENDED"}, "EXTRACTION_FAILED": {"EXTRACTING", "REVIEW_RECOMMENDED"}, "UNSUPPORTED_FORMAT": set(),
}

def can_transition(current: str, target: str) -> bool:
    return target in TRANSITIONS.get(current, set())

def transition(document, target: str, *, error: str = None) -> None:
    current = document.processing_status or "DISCOVERED"
    if current != target and not can_transition(current, target):
        raise ValueError(f"Invalid document state transition: {current} -> {target}")
    document.processing_status = target
    if error:
        warnings = list(document.processing_warnings or [])
        warnings.append(error)
        document.processing_warnings = warnings
