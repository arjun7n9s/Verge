"""Bytes → plain text. Docling when installed; honest UTF-8 / PDF fallbacks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TextifyResult:
    text: str
    page_count: int
    backend: str  # docling | utf8 | pypdf | empty
    degraded: bool = False
    reason: str = ""


def textify_bytes(data: bytes, *, filename: str = "", mime: str = "") -> TextifyResult:
    name = (filename or "").lower()
    mime = (mime or "").lower()

    # Prefer Docling when available (OSS document parse).
    try:
        from docling.document_converter import DocumentConverter  # type: ignore

        import tempfile
        from pathlib import Path

        suffix = Path(name).suffix if name else ".bin"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(data)
            path = tmp.name
        try:
            conv = DocumentConverter()
            result = conv.convert(path)
            text = result.document.export_to_markdown()
            pages = getattr(result.document, "num_pages", None) or max(1, text.count("\n\n") // 40)
            return TextifyResult(text=text or "", page_count=int(pages), backend="docling")
        finally:
            Path(path).unlink(missing_ok=True)
    except Exception:
        pass

    if name.endswith((".txt", ".md", ".csv", ".json", ".log")) or mime.startswith("text/"):
        try:
            return TextifyResult(text=data.decode("utf-8"), page_count=1, backend="utf8")
        except UnicodeDecodeError:
            return TextifyResult(
                text=data.decode("utf-8", errors="replace"),
                page_count=1,
                backend="utf8",
                degraded=True,
                reason="utf8-replace",
            )

    if name.endswith(".pdf") or mime == "application/pdf":
        try:
            from pypdf import PdfReader  # type: ignore
            import io

            reader = PdfReader(io.BytesIO(data))
            parts = []
            for page in reader.pages:
                parts.append(page.extract_text() or "")
            text = "\n\n".join(parts).strip()
            return TextifyResult(
                text=text,
                page_count=len(reader.pages),
                backend="pypdf",
                degraded=not bool(text),
                reason="" if text else "empty-pdf-text",
            )
        except Exception as exc:
            return TextifyResult(
                text="",
                page_count=0,
                backend="empty",
                degraded=True,
                reason=f"pdf-failed:{type(exc).__name__}",
            )

    # Last resort: try utf-8
    try:
        text = data.decode("utf-8")
        return TextifyResult(text=text, page_count=1, backend="utf8", degraded=True, reason="unknown-mime")
    except UnicodeDecodeError:
        return TextifyResult(
            text="",
            page_count=0,
            backend="empty",
            degraded=True,
            reason="unsupported-binary",
        )
