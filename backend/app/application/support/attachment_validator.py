from pathlib import Path
class AttachmentValidator:
    def execute(self, filename: str, content_type: str, content: bytes, max_mb: int) -> str:
        extension = Path(filename).suffix.lower()
        expected = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".txt": "text/plain", ".csv": "text/csv"}
        if extension not in expected: raise ValueError("Only PDF, PNG, JPG, JPEG, TXT and CSV files are allowed")
        if not content: raise ValueError("The uploaded file is empty")
        if len(content) > max_mb * 1024 * 1024: raise ValueError(f"Each file must be {max_mb} MB or smaller")
        signatures = {".pdf": content.startswith(b"%PDF-"), ".png": content.startswith(b"\x89PNG\r\n\x1a\n"), ".jpg": content.startswith(b"\xff\xd8\xff"), ".jpeg": content.startswith(b"\xff\xd8\xff")}
        if extension in signatures and not signatures[extension]: raise ValueError("The file contents do not match the declared file type")
        if content_type and content_type not in {expected[extension], "application/octet-stream"}: raise ValueError("The declared content type does not match the file extension")
        return expected[extension]
