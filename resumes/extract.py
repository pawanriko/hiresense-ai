"""Extract plain text from an uploaded resume file.

WHY A SEPARATE MODULE: extraction is file-format plumbing (PDF vs DOCX),
while scoring.py is pure rules. Keeping them apart means the scoring tests
never need a real file, and a new format (e.g. .txt) only touches this file.

SUPPORTED: .pdf (via pypdf) and .docx (via python-docx). Anything else
raises ValueError, which the upload view turns into a friendly form error.
NOTE: image-only PDFs extract almost no text — that is a real limitation,
not a bug in this code, and the ATS score will say so (low word count).
"""

from docx import Document
from pypdf import PdfReader


def extract_text(uploaded_file, filename):
    """Return the resume's plain text. ``uploaded_file`` is Django's
    UploadedFile (a file-like object); both libraries accept it directly,
    but we rewind it first because Django may already have read from it
    (e.g. during validation)."""
    name = filename.lower()
    uploaded_file.seek(0)
    if name.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        pages = [(page.extract_text() or "") for page in reader.pages]
        return "\n".join(pages)
    if name.endswith(".docx"):
        document = Document(uploaded_file)
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    raise ValueError("Only PDF and DOCX resumes are supported.")
