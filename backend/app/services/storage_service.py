import os
import re
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
import httpx

from config import settings

logger = logging.getLogger(__name__)


# ==============================================================================
# Storage Exceptions Hierarchy
# ==============================================================================

class StorageError(Exception):
    """Base exception for all storage provider operations."""
    pass


class StorageNotFoundError(StorageError, FileNotFoundError):
    """
    Raised when an object or physical file is not found in storage.
    Inherits from FileNotFoundError for seamless backward compatibility.
    """
    pass


class StorageAuthenticationError(StorageError):
    """Raised when authentication with remote storage fails (e.g. invalid service-role key)."""
    pass


class StoragePermissionError(StorageError):
    """Raised when the caller lacks permission to access the target storage resource."""
    pass


class StorageConnectionError(StorageError):
    """Raised when network connectivity to remote storage fails or times out."""
    pass


# ==============================================================================
# Path Safety & Sanitization Helpers
# ==============================================================================

def sanitize_storage_path(path: str) -> str:
    """
    Sanitizes and normalizes an object or file path, strictly preventing
    path traversal vulnerabilities (e.g. '../', '..\\', absolute drive paths).
    """
    if not path or not path.strip():
        raise StorageError("Storage path cannot be empty.")

    # Normalize Windows/Unix path separators to standard forward slash
    normalized = path.replace("\\", "/").strip()

    # Reject absolute root / drive specifications (e.g. /etc/passwd, C:/windows)
    if normalized.startswith("/") or bool(re.match(r"^[a-zA-Z]:", normalized)):
        normalized = re.sub(r"^[a-zA-Z]:[/]*", "", normalized).lstrip("/")

    # Disallow directory traversal sequences
    parts = [p for p in normalized.split("/") if p]
    if ".." in parts:
        raise StorageError(f"Path traversal sequence detected in storage path: '{path}'")

    sanitized = "/".join(parts)
    if not sanitized:
        raise StorageError("Sanitized storage path resulted in empty path.")

    return sanitized


def validate_bucket_name(bucket: str) -> str:
    """Validates that bucket name contains only valid characters."""
    if not bucket or not re.match(r"^[a-zA-Z0-9_\-\.]+$", bucket):
        raise StorageError(f"Invalid bucket identifier: '{bucket}'")
    return bucket


# ==============================================================================
# Storage Provider Abstract Interface
# ==============================================================================

class StorageProvider(ABC):
    """
    Abstract storage provider defining the contract for physical/object file persistence.
    """

    @abstractmethod
    def save_file(
        self,
        bucket: str,
        path: str,
        file_bytes: bytes,
        content_type: Optional[str] = None
    ) -> str:
        """
        Persists binary bytes to the specified bucket and path.
        Returns canonical storage path or object key.
        """
        pass

    @abstractmethod
    def read_file(self, bucket: str, path: str) -> bytes:
        """
        Retrieves binary bytes from the specified bucket and path.
        Raises StorageNotFoundError if the target file/object does not exist.
        """
        pass

    @abstractmethod
    def file_exists(self, bucket: str, path: str) -> bool:
        """
        Checks whether the specified file/object exists.
        Returns True if present, False otherwise.
        """
        pass

    @abstractmethod
    def delete_file(self, bucket: str, path: str) -> bool:
        """
        Deletes the file/object from storage.
        Idempotent: returns True if deleted or already absent.
        Raises StorageError on permission or server failures.
        """
        pass

    @abstractmethod
    def get_file_size(self, bucket: str, path: str) -> int:
        """
        Returns file size in bytes, or 0 if missing.
        """
        pass


# ==============================================================================
# Local Filesystem Storage Provider
# ==============================================================================

class LocalStorageProvider(StorageProvider):
    """
    Local filesystem storage implementation for development, offline execution,
    and fallback testing.
    """

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = os.path.abspath(base_dir or "./storage")

    def _resolve_bucket_dir(self, bucket: str) -> str:
        """Maps bucket identifier to designated local directory."""
        clean_bucket = validate_bucket_name(bucket)
        if clean_bucket in ["uploads", getattr(settings, "SUPABASE_DOCUMENTS_BUCKET", "documents")]:
            target_dir = os.path.abspath(settings.UPLOAD_DIR)
        elif clean_bucket in ["reports", getattr(settings, "SUPABASE_REPORTS_BUCKET", "reports")]:
            target_dir = os.path.abspath(settings.REPORT_DIR)
        else:
            target_dir = os.path.join(self.base_dir, clean_bucket)

        os.makedirs(target_dir, exist_ok=True)
        return target_dir

    def _resolve_target_path(self, bucket: str, path: str) -> str:
        """Safely resolves and validates absolute path within local bucket directory."""
        bucket_dir = self._resolve_bucket_dir(bucket)
        clean_rel_path = sanitize_storage_path(path)
        abs_target = os.path.abspath(os.path.join(bucket_dir, clean_rel_path))

        # Enforce that resolved path resides strictly inside bucket directory
        if not abs_target.startswith(bucket_dir):
            raise StorageError(f"Resolved path '{abs_target}' escapes designated bucket directory '{bucket_dir}'.")
        return abs_target

    def save_file(
        self,
        bucket: str,
        path: str,
        file_bytes: bytes,
        content_type: Optional[str] = None
    ) -> str:
        target_path = self._resolve_target_path(bucket, path)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)

        try:
            with open(target_path, "wb") as f:
                f.write(file_bytes)
            logger.info(f"[LocalStorage] Saved {len(file_bytes)} bytes to '{target_path}'")
            # Return standard relative-safe canonical path
            return target_path.replace("\\", "/")
        except Exception as e:
            logger.error(f"[LocalStorage] Failed to write file to '{target_path}': {e}")
            raise StorageError(f"Failed to write file to local storage: {e}") from e

    def read_file(self, bucket: str, path: str) -> bytes:
        target_path = self._resolve_target_path(bucket, path)
        if not os.path.exists(target_path):
            raise StorageNotFoundError(f"File '{path}' not found in local bucket '{bucket}' ({target_path}).")

        try:
            with open(target_path, "rb") as f:
                return f.read()
        except Exception as e:
            logger.error(f"[LocalStorage] Failed reading file '{target_path}': {e}")
            raise StorageError(f"Failed reading local file '{target_path}': {e}") from e

    def file_exists(self, bucket: str, path: str) -> bool:
        try:
            target_path = self._resolve_target_path(bucket, path)
            return os.path.exists(target_path)
        except StorageError:
            return False

    def delete_file(self, bucket: str, path: str) -> bool:
        try:
            target_path = self._resolve_target_path(bucket, path)
            if os.path.exists(target_path):
                os.remove(target_path)
                logger.info(f"[LocalStorage] Deleted file: '{target_path}'")
            return True
        except StorageError as se:
            logger.warning(f"[LocalStorage] Note on delete validation: {se}")
            return False
        except Exception as e:
            logger.error(f"[LocalStorage] Failed to delete file at '{target_path}': {e}")
            raise StorageError(f"Failed to delete local file '{target_path}': {e}") from e

    def get_file_size(self, bucket: str, path: str) -> int:
        try:
            target_path = self._resolve_target_path(bucket, path)
            if os.path.exists(target_path):
                return os.path.getsize(target_path)
            return 0
        except Exception:
            return 0


# ==============================================================================
# Supabase Storage Provider (HTTPS REST via httpx)
# ==============================================================================

class SupabaseStorageProvider(StorageProvider):
    """
    Production-grade Supabase Storage provider interacting via REST API
    with explicit timeouts, error mappings, and service-role authentication.
    """

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        service_role_key: Optional[str] = None,
        connect_timeout: Optional[float] = None,
        read_timeout: Optional[float] = None,
        http_client: Optional[httpx.Client] = None
    ):
        raw_url = (supabase_url or getattr(settings, "SUPABASE_URL", "")).strip()
        self.supabase_url = raw_url.rstrip("/")
        self.service_role_key = (service_role_key or getattr(settings, "SUPABASE_SERVICE_ROLE_KEY", "")).strip()

        self.connect_timeout = connect_timeout or getattr(settings, "STORAGE_HTTP_CONNECT_TIMEOUT", 15.0)
        self.read_timeout = read_timeout or getattr(settings, "STORAGE_HTTP_READ_TIMEOUT", 60.0)

        # Allow injected client for unit testing / mocking
        if http_client is not None:
            self._client = http_client
            self._owns_client = False
        else:
            self._client = httpx.Client(
                timeout=httpx.Timeout(self.read_timeout, connect=self.connect_timeout)
            )
            self._owns_client = True

    def _validate_credentials(self) -> None:
        """Verifies that mandatory Supabase endpoint and service-role credentials exist."""
        if not self.supabase_url:
            raise StorageAuthenticationError("SUPABASE_URL is not configured.")
        if not self.service_role_key:
            raise StorageAuthenticationError("SUPABASE_SERVICE_ROLE_KEY is not configured.")

    def _build_headers(self, content_type: Optional[str] = None, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Constructs authenticated service-role request headers."""
        self._validate_credentials()
        headers = {
            "Authorization": f"Bearer {self.service_role_key}",
            "apikey": self.service_role_key,
        }
        if content_type:
            headers["Content-Type"] = content_type
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def save_file(
        self,
        bucket: str,
        path: str,
        file_bytes: bytes,
        content_type: Optional[str] = None
    ) -> str:
        clean_bucket = validate_bucket_name(bucket)
        clean_path = sanitize_storage_path(path)
        url = f"{self.supabase_url}/storage/v1/object/{clean_bucket}/{clean_path}"
        headers = self._build_headers(
            content_type=content_type or "application/octet-stream",
            extra_headers={"x-upsert": "true"}
        )

        try:
            resp = self._client.post(url, headers=headers, content=file_bytes)
            if resp.status_code in [200, 201]:
                canonical_key = f"{clean_bucket}/{clean_path}"
                logger.info(f"[SupabaseStorage] Uploaded {len(file_bytes)} bytes to '{canonical_key}'")
                return canonical_key

            if resp.status_code == 401:
                raise StorageAuthenticationError(f"Supabase Storage authentication failed (401): {resp.text}")
            if resp.status_code == 403:
                raise StoragePermissionError(f"Supabase Storage access forbidden (403): {resp.text}")

            raise StorageError(f"Supabase Storage upload failed ({resp.status_code}): {resp.text}")

        except (StorageError, StorageAuthenticationError, StoragePermissionError):
            raise
        except (httpx.TimeoutException, httpx.NetworkError, httpx.RequestError) as net_err:
            logger.error(f"[SupabaseStorage] Network exception uploading to '{url}': {net_err}")
            raise StorageConnectionError(f"Supabase Storage connection failure: {net_err}") from net_err

    def read_file(self, bucket: str, path: str) -> bytes:
        clean_bucket = validate_bucket_name(bucket)
        clean_path = sanitize_storage_path(path)
        url = f"{self.supabase_url}/storage/v1/object/authenticated/{clean_bucket}/{clean_path}"
        headers = self._build_headers()

        try:
            resp = self._client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.content
            if resp.status_code == 404:
                raise StorageNotFoundError(f"Object '{clean_path}' not found in Supabase bucket '{clean_bucket}'.")
            if resp.status_code == 401:
                raise StorageAuthenticationError(f"Supabase Storage authentication failed (401): {resp.text}")
            if resp.status_code == 403:
                raise StoragePermissionError(f"Supabase Storage access forbidden (403): {resp.text}")

            raise StorageError(f"Supabase Storage read failed ({resp.status_code}): {resp.text}")

        except (StorageError, StorageNotFoundError, StorageAuthenticationError, StoragePermissionError):
            raise
        except (httpx.TimeoutException, httpx.NetworkError, httpx.RequestError) as net_err:
            logger.error(f"[SupabaseStorage] Network exception reading from '{url}': {net_err}")
            raise StorageConnectionError(f"Supabase Storage connection failure: {net_err}") from net_err

    def file_exists(self, bucket: str, path: str) -> bool:
        clean_bucket = validate_bucket_name(bucket)
        clean_path = sanitize_storage_path(path)
        url = f"{self.supabase_url}/storage/v1/object/info/authenticated/{clean_bucket}/{clean_path}"
        headers = self._build_headers()

        try:
            resp = self._client.get(url, headers=headers)
            if resp.status_code == 200:
                return True
            if resp.status_code == 404:
                return False
            if resp.status_code in [401, 403]:
                raise StorageAuthenticationError(f"Supabase Storage authentication error ({resp.status_code}): {resp.text}")

            logger.warning(f"[SupabaseStorage] Unexpected status checking existence for '{clean_path}': {resp.status_code}")
            return False
        except (StorageAuthenticationError, StoragePermissionError):
            raise
        except (httpx.TimeoutException, httpx.NetworkError, httpx.RequestError) as net_err:
            logger.error(f"[SupabaseStorage] Network exception checking existence for '{clean_path}': {net_err}")
            raise StorageConnectionError(f"Supabase Storage connection failure: {net_err}") from net_err

    def delete_file(self, bucket: str, path: str) -> bool:
        clean_bucket = validate_bucket_name(bucket)
        clean_path = sanitize_storage_path(path)
        url = f"{self.supabase_url}/storage/v1/object/{clean_bucket}/{clean_path}"
        headers = self._build_headers()

        try:
            resp = self._client.delete(url, headers=headers)
            # Idempotent success: 200, 204, or 404 (already absent)
            if resp.status_code in [200, 204, 404]:
                logger.info(f"[SupabaseStorage] Deleted (or confirmed absent) object '{clean_path}' in bucket '{clean_bucket}'")
                return True

            if resp.status_code == 401:
                raise StorageAuthenticationError(f"Supabase Storage authentication failed (401): {resp.text}")
            if resp.status_code == 403:
                raise StoragePermissionError(f"Supabase Storage access forbidden (403): {resp.text}")

            raise StorageError(f"Supabase Storage delete failed ({resp.status_code}): {resp.text}")

        except (StorageAuthenticationError, StoragePermissionError):
            raise
        except (httpx.TimeoutException, httpx.NetworkError, httpx.RequestError) as net_err:
            logger.error(f"[SupabaseStorage] Network exception deleting '{clean_path}': {net_err}")
            raise StorageConnectionError(f"Supabase Storage connection failure: {net_err}") from net_err

    def get_file_size(self, bucket: str, path: str) -> int:
        clean_bucket = validate_bucket_name(bucket)
        clean_path = sanitize_storage_path(path)
        url = f"{self.supabase_url}/storage/v1/object/info/authenticated/{clean_bucket}/{clean_path}"
        headers = self._build_headers()

        try:
            resp = self._client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json() if resp.content else {}
                metadata = data.get("metadata", {})
                size = metadata.get("size") or data.get("size")
                return int(size) if size is not None else 0
            return 0
        except Exception:
            return 0

    def close(self) -> None:
        """Closes internal HTTP client if owned by this provider instance."""
        if self._owns_client and hasattr(self, "_client") and self._client:
            self._client.close()


# ==============================================================================
# Provider Factory & Global Registry
# ==============================================================================

_storage_provider_singleton: Optional[StorageProvider] = None


def get_storage_provider(provider_type: Optional[str] = None, force_new: bool = False) -> StorageProvider:
    """
    Factory returning the configured StorageProvider instance.
    Defaults to settings.STORAGE_PROVIDER ('local' or 'supabase').
    """
    global _storage_provider_singleton
    if _storage_provider_singleton is not None and not force_new and provider_type is None:
        return _storage_provider_singleton

    active_type = (provider_type or getattr(settings, "STORAGE_PROVIDER", "local")).lower().strip()

    if active_type == "supabase":
        logger.info("Initializing SupabaseStorageProvider.")
        provider = SupabaseStorageProvider()
    elif active_type == "local":
        provider = LocalStorageProvider()
    else:
        logger.warning(f"Unrecognized storage provider '{active_type}'. Defaulting to LocalStorageProvider.")
        provider = LocalStorageProvider()

    if provider_type is None and not force_new:
        _storage_provider_singleton = provider

    return provider


# ==============================================================================
# ==============================================================================
# Reference-Aware Storage Routing & Lifecycle Helpers
# ==============================================================================

def parse_storage_reference(storage_ref: Optional[str]) -> Tuple[str, str, str]:
    """
    Parses a stored file_path string into (provider_type, bucket, object_path_or_file_path).
    Distinguishes legacy local filesystem paths from Supabase object references.

    Returns:
        ('supabase', bucket_name, object_path)
        or
        ('local', bucket_or_dir, file_path)
        or
        ('unknown', '', '')
    """
    if not storage_ref or not storage_ref.strip():
        return ("unknown", "", "")

    clean_ref = storage_ref.strip()

    # 1. Explicit supabase:// scheme
    if clean_ref.startswith("supabase://"):
        without_scheme = clean_ref[len("supabase://"):].lstrip("/")
        parts = without_scheme.split("/", 1)
        bucket = parts[0] if parts else getattr(settings, "SUPABASE_DOCUMENTS_BUCKET", "documents")
        obj_path = parts[1] if len(parts) > 1 else ""
        return ("supabase", validate_bucket_name(bucket), sanitize_storage_path(obj_path))

    # Normalize slashes for inspection
    normalized = clean_ref.replace("\\", "/")

    # 2. Legacy local filesystem paths: starts with ./, ../, /, drive letter, or contains storage/
    if (
        normalized.startswith("./")
        or normalized.startswith("../")
        or normalized.startswith("/")
        or bool(re.match(r"^[a-zA-Z]:", normalized))
        or "storage/uploads" in normalized
        or "storage/reports" in normalized
    ):
        bucket_hint = "reports" if "storage/reports" in normalized or "reports" in normalized else "uploads"
        return ("local", bucket_hint, clean_ref)

    # 3. Supabase object keys: e.g. "documents/{doc_id}/{filename}" or "reports/{report_id}/{filename}"
    doc_bucket = getattr(settings, "SUPABASE_DOCUMENTS_BUCKET", "documents")
    rep_bucket = getattr(settings, "SUPABASE_REPORTS_BUCKET", "reports")

    parts = normalized.split("/", 1)
    first_segment = parts[0]
    if first_segment in [doc_bucket, "documents", rep_bucket, "reports"]:
        bucket = first_segment
        obj_path = parts[1] if len(parts) > 1 else ""
        return ("supabase", validate_bucket_name(bucket), sanitize_storage_path(obj_path))

    # 4. Fallback for unclassified paths: treat as local filesystem path
    return ("local", "uploads", clean_ref)


def save_document_binary(
    file_bytes: bytes,
    document_id: int,
    filename: str,
    file_hash: str,
    content_type: Optional[str] = None
) -> str:
    """
    Persists document binary bytes using the currently configured StorageProvider.
    In Local mode:
        Saves to local upload directory (e.g. ./storage/uploads/{file_hash}_{filename}).
        Returns local relative path.
    In Supabase mode:
        Saves to Supabase Storage documents bucket under 'documents/{document_id}/{filename}'.
        Returns canonical object reference 'documents/{document_id}/{filename}'.
    """
    provider = get_storage_provider()

    if isinstance(provider, SupabaseStorageProvider):
        bucket = getattr(settings, "SUPABASE_DOCUMENTS_BUCKET", "documents")
        clean_name = sanitize_storage_path(filename)
        # Store under {document_id}/{sanitized_filename} in the documents bucket
        object_path = f"{document_id}/{clean_name}"
        canonical_key = provider.save_file(
            bucket=bucket,
            path=object_path,
            file_bytes=file_bytes,
            content_type=content_type or "application/pdf"
        )
        logger.info(f"Persisted document #{document_id} binary to Supabase Storage: '{canonical_key}'")
        return canonical_key
    else:
        # LocalStorageProvider
        saved_path = save_uploaded_file(file_bytes=file_bytes, file_hash=file_hash, sanitized_filename=filename)
        logger.info(f"Persisted document #{document_id} binary to Local Storage: '{saved_path}'")
        return saved_path


def read_document_binary(storage_ref: str) -> bytes:
    """
    Reference-aware binary reader.
    Retrieves document binary from Supabase Storage or Local filesystem based on storage_ref.
    """
    if not storage_ref or not storage_ref.strip():
        raise StorageNotFoundError("Document storage reference is empty.")

    ref_type, bucket, path = parse_storage_reference(storage_ref)
    if ref_type == "supabase":
        provider = get_storage_provider("supabase")
        return provider.read_file(bucket=bucket, path=path)

    # Local fallback
    return read_uploaded_file(storage_ref)


def document_binary_exists(storage_ref: Optional[str]) -> bool:
    """
    Reference-aware existence checker.
    Returns True if binary exists in Supabase Storage or Local filesystem, False otherwise.
    """
    if not storage_ref or not storage_ref.strip():
        return False

    ref_type, bucket, path = parse_storage_reference(storage_ref)
    if ref_type == "supabase":
        try:
            provider = get_storage_provider("supabase")
            return provider.file_exists(bucket=bucket, path=path)
        except Exception as e:
            logger.warning(f"Error checking Supabase storage existence for '{storage_ref}': {e}")
            return False

    return file_exists(storage_ref)


def delete_document_binary(storage_ref: Optional[str]) -> bool:
    """
    Reference-aware binary deletion.
    Removes document binary from Supabase Storage or Local filesystem.
    Idempotent: returns True if deleted or already absent.
    """
    if not storage_ref or not storage_ref.strip():
        return False

    ref_type, bucket, path = parse_storage_reference(storage_ref)
    if ref_type == "supabase":
        try:
            provider = get_storage_provider("supabase")
            return provider.delete_file(bucket=bucket, path=path)
        except Exception as e:
            logger.warning(f"Error deleting Supabase object '{storage_ref}': {e}")
            raise

    return delete_uploaded_file(storage_ref)


def get_document_binary_size(storage_ref: Optional[str]) -> int:
    """
    Reference-aware size lookup in bytes.
    """
    if not storage_ref or not storage_ref.strip():
        return 0

    ref_type, bucket, path = parse_storage_reference(storage_ref)
    if ref_type == "supabase":
        try:
            provider = get_storage_provider("supabase")
            return provider.get_file_size(bucket=bucket, path=path)
        except Exception:
            return 0

    return get_file_size(storage_ref)


# ==============================================================================
# Report Storage Routing & Lifecycle Helpers
# ==============================================================================

def save_report_binary(
    file_bytes: bytes,
    report_id: int,
    filename: str,
    content_type: Optional[str] = "application/pdf"
) -> str:
    """
    Persists report PDF binary bytes using the currently configured StorageProvider.
    In Local mode:
        Saves to local report directory (e.g. ./storage/reports/{filename}).
        Returns local relative path (e.g. ./storage/reports/{filename}).
    In Supabase mode:
        Saves to Supabase Storage reports bucket under 'reports/{report_id}/{filename}'.
        Returns canonical object reference 'reports/{report_id}/{filename}'.
    """
    provider = get_storage_provider()
    clean_name = sanitize_storage_path(filename)

    if isinstance(provider, SupabaseStorageProvider):
        bucket = getattr(settings, "SUPABASE_REPORTS_BUCKET", "reports")
        object_path = f"{report_id}/{clean_name}"
        canonical_key = provider.save_file(
            bucket=bucket,
            path=object_path,
            file_bytes=file_bytes,
            content_type=content_type or "application/pdf"
        )
        logger.info(f"Persisted report #{report_id} binary to Supabase Storage: '{canonical_key}'")
        return canonical_key
    else:
        # LocalStorageProvider
        report_dir = os.path.abspath(settings.REPORT_DIR)
        os.makedirs(report_dir, exist_ok=True)
        target_path = os.path.join(report_dir, clean_name)
        with open(target_path, "wb") as f:
            f.write(file_bytes)
        rel_path = os.path.join(settings.REPORT_DIR, clean_name).replace("\\", "/")
        logger.info(f"Persisted report #{report_id} binary to Local Storage: '{rel_path}'")
        return rel_path


def read_report_binary(storage_ref: str) -> bytes:
    """
    Reference-aware report binary reader.
    Retrieves report binary from Supabase Storage or Local filesystem based on storage_ref.
    """
    if not storage_ref or not storage_ref.strip():
        raise StorageNotFoundError("Report storage reference is empty.")

    ref_type, bucket, path = parse_storage_reference(storage_ref)
    if ref_type == "supabase":
        provider = get_storage_provider("supabase")
        return provider.read_file(bucket=bucket, path=path)

    abs_path = os.path.abspath(storage_ref)
    if not os.path.exists(abs_path):
        raise StorageNotFoundError(f"Stored report file not found at '{storage_ref}'.")
    with open(abs_path, "rb") as f:
        return f.read()


def report_binary_exists(storage_ref: Optional[str]) -> bool:
    """
    Reference-aware report existence checker.
    Returns True if report binary exists in Supabase Storage or Local filesystem, False otherwise.
    """
    if not storage_ref or not storage_ref.strip():
        return False

    ref_type, bucket, path = parse_storage_reference(storage_ref)
    if ref_type == "supabase":
        try:
            provider = get_storage_provider("supabase")
            return provider.file_exists(bucket=bucket, path=path)
        except Exception as e:
            logger.warning(f"Error checking Supabase storage existence for report '{storage_ref}': {e}")
            return False

    return os.path.exists(os.path.abspath(storage_ref))


def delete_report_binary(storage_ref: Optional[str]) -> bool:
    """
    Reference-aware report binary deletion.
    Removes report binary from Supabase Storage or Local filesystem.
    Idempotent: returns True if deleted or already absent.
    """
    if not storage_ref or not storage_ref.strip():
        return False

    ref_type, bucket, path = parse_storage_reference(storage_ref)
    if ref_type == "supabase":
        try:
            provider = get_storage_provider("supabase")
            return provider.delete_file(bucket=bucket, path=path)
        except Exception as e:
            logger.warning(f"Error deleting Supabase report object '{storage_ref}': {e}")
            raise

    abs_path = os.path.abspath(storage_ref)
    if os.path.exists(abs_path):
        try:
            os.remove(abs_path)
            logger.info(f"Deleted local report file: {abs_path}")
            return True
        except Exception as e:
            logger.warning(f"Could not delete local report file at '{abs_path}': {e}")
            return False
    return False


def get_report_binary_size(storage_ref: Optional[str]) -> int:
    """
    Reference-aware report size lookup in bytes.
    """
    if not storage_ref or not storage_ref.strip():
        return 0

    ref_type, bucket, path = parse_storage_reference(storage_ref)
    if ref_type == "supabase":
        try:
            provider = get_storage_provider("supabase")
            return provider.get_file_size(bucket=bucket, path=path)
        except Exception:
            return 0

    abs_path = os.path.abspath(storage_ref)
    if os.path.exists(abs_path):
        return os.path.getsize(abs_path)
    return 0


# ==============================================================================
# Backward-Compatible Helper Functions (Delegating to Reference-Aware Helpers)
# ==============================================================================

def get_storage_upload_dir() -> str:
    """Returns absolute path to the local upload directory, ensuring it exists."""
    upload_dir = os.path.abspath(settings.UPLOAD_DIR)
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def save_uploaded_file(file_bytes: bytes, file_hash: str, sanitized_filename: str) -> str:
    """
    Persists uploaded file bytes to local storage.
    Returns relative or canonical storage path string stored in database.
    """
    upload_dir = get_storage_upload_dir()
    storage_filename = f"{file_hash}_{sanitized_filename}"
    target_path = os.path.join(upload_dir, storage_filename)

    with open(target_path, "wb") as f:
        f.write(file_bytes)

    logger.info(f"Saved uploaded file to local storage: {target_path} ({len(file_bytes)} bytes)")
    return os.path.join(settings.UPLOAD_DIR, storage_filename).replace("\\", "/")


def read_uploaded_file(file_path: str) -> bytes:
    """
    Reads and returns raw bytes of stored document file.
    Supports both legacy local paths and remote storage references.
    Raises StorageNotFoundError / FileNotFoundError if file is missing.
    """
    if not file_path:
        raise StorageNotFoundError("Stored document file path cannot be empty.")

    ref_type, bucket, path = parse_storage_reference(file_path)
    if ref_type == "supabase":
        provider = get_storage_provider("supabase")
        return provider.read_file(bucket=bucket, path=path)

    abs_path = os.path.abspath(file_path)
    if not os.path.exists(abs_path):
        raise StorageNotFoundError(f"Stored document file not found at '{file_path}'.")

    with open(abs_path, "rb") as f:
        return f.read()


def file_exists(file_path: Optional[str]) -> bool:
    """Checks whether the physical document file or remote object exists in storage."""
    if not file_path:
        return False

    ref_type, bucket, path = parse_storage_reference(file_path)
    if ref_type == "supabase":
        try:
            provider = get_storage_provider("supabase")
            return provider.file_exists(bucket=bucket, path=path)
        except Exception:
            return False

    return os.path.exists(os.path.abspath(file_path))


def delete_uploaded_file(file_path: Optional[str]) -> bool:
    """Safely removes physical document file or remote object from storage if present."""
    if not file_path:
        return False

    ref_type, bucket, path = parse_storage_reference(file_path)
    if ref_type == "supabase":
        try:
            provider = get_storage_provider("supabase")
            return provider.delete_file(bucket=bucket, path=path)
        except Exception as e:
            logger.warning(f"Could not delete Supabase object at '{file_path}': {e}")
            return False

    abs_path = os.path.abspath(file_path)
    if os.path.exists(abs_path):
        try:
            os.remove(abs_path)
            logger.info(f"Deleted file from local storage: {abs_path}")
            return True
        except Exception as e:
            logger.warning(f"Could not delete local file at '{abs_path}': {e}")
            return False
    return False


def get_file_size(file_path: Optional[str]) -> int:
    """Returns file or object size in bytes, or 0 if missing."""
    if not file_path:
        return 0

    ref_type, bucket, path = parse_storage_reference(file_path)
    if ref_type == "supabase":
        try:
            provider = get_storage_provider("supabase")
            return provider.get_file_size(bucket=bucket, path=path)
        except Exception:
            return 0

    abs_path = os.path.abspath(file_path)
    if os.path.exists(abs_path):
        return os.path.getsize(abs_path)
    return 0
