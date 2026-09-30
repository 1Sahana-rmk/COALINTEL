import unittest
import os
import re
import hashlib

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB Limit
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".csv"}


def sanitize_filename(filename: str) -> str:
    if not filename:
        return "unnamed_document.pdf"
    basename = os.path.basename(filename).replace("\\", "/").split("/")[-1]
    clean = re.sub(r"[^\w\.\-]", "_", basename)
    if not clean or clean.startswith("."):
        clean = f"document_{clean}"
    return clean[:200]


def validate_file_upload(filename: str, file_size: int):
    if file_size > MAX_FILE_SIZE_BYTES:
        raise ValueError(f"File size ({file_size} bytes) exceeds maximum 50MB limit.")
    _, ext = os.path.splitext(filename)
    ext_lower = ext.lower()
    if ext_lower not in ALLOWED_EXTENSIONS:
        raise ValueError(f"File extension '{ext}' is not supported.")
    return ext_lower[1:].upper()


def calculate_sha256(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


class TestStandaloneIngestionLogic(unittest.TestCase):

    def test_path_traversal_sanitization(self):
        """Verify path traversal patterns strictly sanitized."""
        self.assertNotIn("..", sanitize_filename("../../etc/passwd"))
        self.assertNotIn("/", sanitize_filename("..\\..\\Windows\\System32\\cmd.exe"))
        self.assertEqual(sanitize_filename("report_2023.pdf"), "report_2023.pdf")
        self.assertIn("secret.pdf", sanitize_filename("../../../secret.pdf"))

    def test_file_type_and_size_validation(self):
        """Verify 50MB size ceiling and extension whitelist."""
        self.assertEqual(validate_file_upload("report.pdf", 1024), "PDF")
        self.assertEqual(validate_file_upload("data.docx", 2048), "DOCX")
        self.assertEqual(validate_file_upload("sheet.xlsx", 512), "XLSX")
        self.assertEqual(validate_file_upload("log.csv", 128), "CSV")

        with self.assertRaises(ValueError):
            validate_file_upload("executable.exe", 1024)

        with self.assertRaises(ValueError):
            validate_file_upload("huge.pdf", MAX_FILE_SIZE_BYTES + 1)

    def test_sha256_hash_calculation(self):
        """Verify SHA-256 digest consistency."""
        data_a = b"COALINTEL Mining Report A"
        data_b = b"COALINTEL Mining Report B"

        hash_a1 = calculate_sha256(data_a)
        hash_a2 = calculate_sha256(data_a)
        hash_b = calculate_sha256(data_b)

        self.assertEqual(len(hash_a1), 64)
        self.assertEqual(hash_a1, hash_a2)
        self.assertNotEqual(hash_a1, hash_b)


if __name__ == "__main__":
    unittest.main()
