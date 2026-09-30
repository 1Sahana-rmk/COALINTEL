import os
import sys
import io
import tempfile
import pytest
import httpx

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.storage_service import (
    StorageError,
    StorageNotFoundError,
    StorageAuthenticationError,
    StoragePermissionError,
    StorageConnectionError,
    sanitize_storage_path,
    validate_bucket_name,
    LocalStorageProvider,
    SupabaseStorageProvider,
    get_storage_provider,
    save_uploaded_file,
    read_uploaded_file,
    file_exists,
    delete_uploaded_file,
    get_file_size,
    get_storage_upload_dir,
)
from config import settings


# ==============================================================================
# 1. Path Sanitization & Validation Tests
# ==============================================================================

def test_sanitize_storage_path_valid():
    assert sanitize_storage_path("documents/report.pdf") == "documents/report.pdf"
    assert sanitize_storage_path("subfolder/doc_1.txt") == "subfolder/doc_1.txt"
    assert sanitize_storage_path("a\\b\\c.pdf") == "a/b/c.pdf"
    assert sanitize_storage_path("/leading/slash.pdf") == "leading/slash.pdf"
    assert sanitize_storage_path("C:/windows/path.pdf") == "windows/path.pdf"


def test_sanitize_storage_path_traversal_rejections():
    with pytest.raises(StorageError, match="Path traversal sequence"):
        sanitize_storage_path("../secret.txt")

    with pytest.raises(StorageError, match="Path traversal sequence"):
        sanitize_storage_path("docs/../../etc/passwd")

    with pytest.raises(StorageError, match="Path traversal sequence"):
        sanitize_storage_path("folder/..\\sub")

    with pytest.raises(StorageError, match="cannot be empty"):
        sanitize_storage_path("   ")


def test_validate_bucket_name():
    assert validate_bucket_name("documents") == "documents"
    assert validate_bucket_name("reports-v2_prod.1") == "reports-v2_prod.1"

    with pytest.raises(StorageError, match="Invalid bucket identifier"):
        validate_bucket_name("invalid bucket with spaces")

    with pytest.raises(StorageError, match="Invalid bucket identifier"):
        validate_bucket_name("bad/bucket")


# ==============================================================================
# 2. LocalStorageProvider Tests
# ==============================================================================

def test_local_storage_provider_crud():
    with tempfile.TemporaryDirectory() as tmp_dir:
        provider = LocalStorageProvider(base_dir=tmp_dir)
        bucket = "test_bucket"
        path = "test_file.txt"
        content = b"Hello COALINTEL Storage Abstraction!"

        # 1. Exists before save
        assert provider.file_exists(bucket, path) is False
        assert provider.get_file_size(bucket, path) == 0

        # 2. Save
        saved_path = provider.save_file(bucket, path, content, content_type="text/plain")
        assert os.path.exists(saved_path)

        # 3. Exists after save
        assert provider.file_exists(bucket, path) is True
        assert provider.get_file_size(bucket, path) == len(content)

        # 4. Read
        read_bytes = provider.read_file(bucket, path)
        assert read_bytes == content

        # 5. Delete
        assert provider.delete_file(bucket, path) is True
        assert provider.file_exists(bucket, path) is False

        # 6. Idempotent delete (deleting non-existent returns True)
        assert provider.delete_file(bucket, path) is True


def test_local_storage_provider_not_found():
    with tempfile.TemporaryDirectory() as tmp_dir:
        provider = LocalStorageProvider(base_dir=tmp_dir)
        with pytest.raises(StorageNotFoundError) as exc_info:
            provider.read_file("test_bucket", "non_existent.pdf")
        
        # Verify it is also a FileNotFoundError for backward compatibility
        assert isinstance(exc_info.value, FileNotFoundError)


def test_local_storage_provider_path_traversal():
    with tempfile.TemporaryDirectory() as tmp_dir:
        provider = LocalStorageProvider(base_dir=tmp_dir)
        with pytest.raises(StorageError, match="Path traversal sequence"):
            provider.save_file("test_bucket", "../escaped.txt", b"hack")


# ==============================================================================
# 3. SupabaseStorageProvider Tests (Mocked Transport)
# ==============================================================================

def test_supabase_storage_missing_credentials():
    provider = SupabaseStorageProvider(supabase_url="", service_role_key="")
    with pytest.raises(StorageAuthenticationError, match="SUPABASE_URL is not configured"):
        provider.save_file("documents", "test.pdf", b"data")

    provider_no_key = SupabaseStorageProvider(supabase_url="https://xyz.supabase.co", service_role_key="")
    with pytest.raises(StorageAuthenticationError, match="SUPABASE_SERVICE_ROLE_KEY is not configured"):
        provider_no_key.save_file("documents", "test.pdf", b"data")


def test_supabase_storage_upload_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert "/storage/v1/object/documents/hash123_test.pdf" in str(request.url)
        assert request.headers["Authorization"] == "Bearer test-service-key"
        assert request.headers["apikey"] == "test-service-key"
        assert request.headers["x-upsert"] == "true"
        assert request.headers["Content-Type"] == "application/pdf"
        assert request.content == b"PDF DATA"
        return httpx.Response(200, json={"Key": "documents/hash123_test.pdf"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = SupabaseStorageProvider(
        supabase_url="https://mock.supabase.co",
        service_role_key="test-service-key",
        http_client=client
    )

    result_key = provider.save_file("documents", "hash123_test.pdf", b"PDF DATA", content_type="application/pdf")
    assert result_key == "documents/hash123_test.pdf"


def test_supabase_storage_upload_errors():
    def handler_401(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="Unauthorized service role key")

    client_401 = httpx.Client(transport=httpx.MockTransport(handler_401))
    provider_401 = SupabaseStorageProvider(
        supabase_url="https://mock.supabase.co",
        service_role_key="bad-key",
        http_client=client_401
    )
    with pytest.raises(StorageAuthenticationError, match="authentication failed \\(401\\)"):
        provider_401.save_file("documents", "test.pdf", b"DATA")

    def handler_403(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="Forbidden bucket access")

    client_403 = httpx.Client(transport=httpx.MockTransport(handler_403))
    provider_403 = SupabaseStorageProvider(
        supabase_url="https://mock.supabase.co",
        service_role_key="key",
        http_client=client_403
    )
    with pytest.raises(StoragePermissionError, match="access forbidden \\(403\\)"):
        provider_403.save_file("documents", "test.pdf", b"DATA")


def test_supabase_storage_read_and_not_found():
    def handler(request: httpx.Request) -> httpx.Response:
        if "found.pdf" in str(request.url):
            return httpx.Response(200, content=b"FILE CONTENTS")
        return httpx.Response(404, text="Object not found")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = SupabaseStorageProvider(
        supabase_url="https://mock.supabase.co",
        service_role_key="test-key",
        http_client=client
    )

    # 1. Success read
    content = provider.read_file("documents", "found.pdf")
    assert content == b"FILE CONTENTS"

    # 2. Not found
    with pytest.raises(StorageNotFoundError, match="Object 'missing.pdf' not found"):
        provider.read_file("documents", "missing.pdf")


def test_supabase_storage_file_exists():
    def handler(request: httpx.Request) -> httpx.Response:
        if "present.pdf" in str(request.url):
            return httpx.Response(200, json={"name": "present.pdf"})
        return httpx.Response(404, text="Not Found")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = SupabaseStorageProvider(
        supabase_url="https://mock.supabase.co",
        service_role_key="test-key",
        http_client=client
    )

    assert provider.file_exists("documents", "present.pdf") is True
    assert provider.file_exists("documents", "absent.pdf") is False


def test_supabase_storage_delete_idempotency():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        if "exists.pdf" in str(request.url):
            return httpx.Response(200, json={"message": "Deleted"})
        return httpx.Response(404, text="Already missing")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = SupabaseStorageProvider(
        supabase_url="https://mock.supabase.co",
        service_role_key="test-key",
        http_client=client
    )

    # Both existing and already-absent files delete cleanly
    assert provider.delete_file("documents", "exists.pdf") is True
    assert provider.delete_file("documents", "absent.pdf") is True


def test_supabase_storage_get_file_size():
    def handler(request: httpx.Request) -> httpx.Response:
        if "sized.pdf" in str(request.url):
            return httpx.Response(200, json={"metadata": {"size": 4096}})
        return httpx.Response(404, text="Not Found")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = SupabaseStorageProvider(
        supabase_url="https://mock.supabase.co",
        service_role_key="test-key",
        http_client=client
    )

    assert provider.get_file_size("documents", "sized.pdf") == 4096
    assert provider.get_file_size("documents", "missing.pdf") == 0


def test_supabase_storage_connection_error():
    def handler_timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("Connection timed out", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler_timeout))
    provider = SupabaseStorageProvider(
        supabase_url="https://mock.supabase.co",
        service_role_key="test-key",
        http_client=client
    )

    with pytest.raises(StorageConnectionError, match="Supabase Storage connection failure"):
        provider.save_file("documents", "test.pdf", b"DATA")


# ==============================================================================
# 4. Factory Function Tests
# ==============================================================================

def test_get_storage_provider_factory():
    local_p = get_storage_provider(provider_type="local", force_new=True)
    assert isinstance(local_p, LocalStorageProvider)

    supa_p = get_storage_provider(provider_type="supabase", force_new=True)
    assert isinstance(supa_p, SupabaseStorageProvider)

    fallback_p = get_storage_provider(provider_type="unrecognized", force_new=True)
    assert isinstance(fallback_p, LocalStorageProvider)


# ==============================================================================
# 5. Backward Compatibility Helper Tests
# ==============================================================================

def test_legacy_helper_functions():
    upload_dir = get_storage_upload_dir()
    assert os.path.exists(upload_dir)

    test_bytes = b"LEGACY STORAGE TEST BYTES"
    test_hash = "abc123456789"
    test_filename = "legacy_test_file.pdf"

    saved_rel_path = save_uploaded_file(test_bytes, test_hash, test_filename)
    assert saved_rel_path.startswith("./storage/uploads") or "storage/uploads" in saved_rel_path

    assert file_exists(saved_rel_path) is True
    assert get_file_size(saved_rel_path) == len(test_bytes)

    read_bytes = read_uploaded_file(saved_rel_path)
    assert read_bytes == test_bytes

    deleted = delete_uploaded_file(saved_rel_path)
    assert deleted is True
    assert file_exists(saved_rel_path) is False
    assert file_exists(None) is False
    assert delete_uploaded_file(None) is False
    assert get_file_size(None) == 0
