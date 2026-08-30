from pathlib import Path
import pymupdf

def extract_pdf_text(pdf_path: str) -> str:
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(pdf_path)
    parts = []
    with pymupdf.open(path) as doc:
        for n, page in enumerate(doc, 1):
            parts.append(f"\n--- PAGE {n} ---\n{page.get_text()}")
    text = "\n".join(parts).strip()
    if not text:
        raise ValueError(f"No extractable text found in {pdf_path}")
    return text
