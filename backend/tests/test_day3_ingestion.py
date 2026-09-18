import unittest
import os
import sys

# Ensure backend directory is in sys.path for module resolution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from jose import jwt
    from app.core.security import verify_password, get_password_hash, create_access_token
    HAS_JOSE = True
except ModuleNotFoundError:
    HAS_JOSE = False

from config import settings
from app.services.ingestion_service import (
    sanitize_filename,
    validate_file_upload,
    calculate_sha256,
    MAX_FILE_SIZE_BYTES
)


class TestDay3IngestionAndSecurity(unittest.TestCase):

    def test_path_traversal_sanitization(self):
        """Verify filename sanitization strips malicious path traversal inputs."""
        test_cases = [
            ("../../etc/passwd", "passwd"),
            ("..\\..\\Windows\\System32\\cmd.exe", "cmd.exe"),
            ("../../../secret.pdf", "secret.pdf"),
            ("normal_document.pdf", "normal_document.pdf"),
            ("spaces in name (1).docx", "spaces_in_name__1_.docx"),
            ("", "unnamed_document.pdf"),
        ]
        for input_name, expected_substring in test_cases:
            sanitized = sanitize_filename(input_name)
            self.assertNotIn("..", sanitized)
            self.assertNotIn("/", sanitized)
            self.assertNotIn("\\", sanitized)
            self.assertIn(expected_substring.split('.')[0], sanitized)

    def test_file_type_and_size_validation(self):
        """Verify size limits (50MB) and extension whitelist enforcement."""
        # Supported extensions
        self.assertEqual(validate_file_upload("report.pdf", 1024), "PDF")
        self.assertEqual(validate_file_upload("data.docx", 2048), "DOCX")
        self.assertEqual(validate_file_upload("table.xlsx", 512), "XLSX")
        self.assertEqual(validate_file_upload("log.csv", 128), "CSV")

        # Unsupported extension failure
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx_ext:
            validate_file_upload("malicious.exe", 1024)
        self.assertEqual(ctx_ext.exception.status_code, 400)
        self.assertIn("not supported", ctx_ext.exception.detail)

        # Oversized file failure (> 50MB)
        with self.assertRaises(HTTPException) as ctx_size:
            validate_file_upload("huge.pdf", MAX_FILE_SIZE_BYTES + 1)
        self.assertEqual(ctx_size.exception.status_code, 400)
        self.assertIn("exceeds maximum allowed limit", ctx_size.exception.detail)

    def test_sha256_hash_calculation(self):
        """Verify SHA-256 digest calculation accuracy."""
        content_a = b"COALINTEL Mining Report Sample A"
        content_b = b"COALINTEL Mining Report Sample B"

        hash_a = calculate_sha256(content_a)
        hash_a_dup = calculate_sha256(content_a)
        hash_b = calculate_sha256(content_b)

        self.assertEqual(len(hash_a), 64)
        self.assertEqual(hash_a, hash_a_dup)
        self.assertNotEqual(hash_a, hash_b)

    def test_security_bcrypt_and_jwt(self):
        """Verify bcrypt password hashing and OAuth2 JWT bearer token claims."""
        if not HAS_JOSE:
            self.skipTest("jose/passlib not installed on host Python")
        password = "AdminSecurePassword@123"
        hashed = get_password_hash(password)

        self.assertTrue(verify_password(password, hashed))
        self.assertFalse(verify_password("WrongPassword", hashed))

        token = create_access_token(subject="admin", role="Admin", subsidiary="CIL HQ")
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        self.assertEqual(payload["sub"], "admin")
        self.assertEqual(payload["role"], "Admin")
        self.assertEqual(payload["subsidiary"], "CIL HQ")
        self.assertIn("exp", payload)


if __name__ == "__main__":
    unittest.main()
