"""Tests for the upload flow (views, forms, extraction, ownership).

HOW DJANGO TESTS WORK: ``TestCase`` gives you a throwaway test database
(created empty, destroyed afterwards) and a test ``Client`` (``self.client``)
that makes requests without a real server. ``SimpleUploadedFile`` fakes an
uploaded file in memory — no files are written to disk by these tests.
"""

from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from docx import Document

from resumes.models import Resume

User = get_user_model()

RESUME_PARAGRAPHS = [
    "Pawan Kumar pawanriko@gmail.com github.com/pawanriko",
    "Summary",
    "BCA student building AI and web projects.",
    "Skills",
    "React, JavaScript, Git",
    "Experience",
    ("Frontend Intern — Built a React dashboard used by 200 users. "
     "Wrote JavaScript utilities that reduced load time by 30%."),
    "Education",
    "BCA — Bachelor of Computer Applications, 2024",
]


def make_docx(paragraphs):
    """Build a small .docx in memory (no file on disk)."""
    document = Document()
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)
    buffer = BytesIO()
    document.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def make_minimal_pdf(text):
    """Build a tiny but VALID one-page PDF in memory, with a correct
    cross-reference table (pypdf needs it). Only used to prove the PDF
    extraction path works; real resumes come from real files."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
         b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"),
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_offset = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n".encode()
    pdf += b"0000000000 65535 f \n"
    for offset in offsets:
        pdf += f"{offset:010d} 00000 n \n".encode()
    pdf += (f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n").encode()
    return bytes(pdf)


class UploadFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="demo", password="demo1234")
        self.other = User.objects.create_user(username="other", password="other1234")

    def test_anonymous_upload_redirects_to_login(self):
        response = self.client.get(reverse("resumes:upload"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_docx_upload_scores_and_shows_result(self):
        self.client.force_login(self.user)
        uploaded = SimpleUploadedFile(
            "resume.docx", make_docx(RESUME_PARAGRAPHS),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        response = self.client.post(reverse("resumes:upload"), {"file": uploaded})
        self.assertEqual(response.status_code, 302)  # redirect-after-POST
        resume = Resume.objects.get(owner=self.user)
        self.assertEqual(resume.original_name, "resume.docx")
        self.assertGreater(resume.ats_score, 50)
        self.assertIn("Sections", [c["name"] for c in resume.breakdown["categories"]])
        result_page = self.client.get(
            reverse("resumes:result", kwargs={"pk": resume.pk}))
        self.assertEqual(result_page.status_code, 200)
        self.assertContains(result_page, str(resume.ats_score))

    def test_pdf_text_extraction(self):
        from resumes.extract import extract_text
        pdf_bytes = make_minimal_pdf("Built a React dashboard for 200 users")
        file_like = SimpleUploadedFile("resume.pdf", pdf_bytes,
                                        content_type="application/pdf")
        text = extract_text(file_like, "resume.pdf")
        self.assertIn("React", text)
        self.assertIn("200", text)

    def test_txt_upload_is_rejected_with_friendly_error(self):
        self.client.force_login(self.user)
        uploaded = SimpleUploadedFile("notes.txt", b"hello",
                                      content_type="text/plain")
        response = self.client.post(reverse("resumes:upload"), {"file": uploaded})
        self.assertEqual(response.status_code, 200)  # form re-rendered, not saved
        self.assertContains(response, "Only PDF and DOCX resumes are supported.")
        self.assertEqual(Resume.objects.count(), 0)

    def test_result_page_is_owner_only(self):
        resume = Resume.objects.create(
            owner=self.user, original_name="mine.docx", extracted_text="x",
            ats_score=80, breakdown={},
        )
        self.client.force_login(self.other)
        response = self.client.get(
            reverse("resumes:result", kwargs={"pk": resume.pk}))
        self.assertEqual(response.status_code, 404)

    def test_dashboard_lists_my_resumes(self):
        # The dashboard is the React page now; it reads /api/dashboard/.
        Resume.objects.create(owner=self.user, original_name="a.docx",
                              extracted_text="x", ats_score=70, breakdown={})
        self.client.force_login(self.user)
        data = self.client.get("/api/dashboard/").json()
        self.assertEqual(
            [resume["original_name"] for resume in data["resumes"]],
            ["a.docx"],
        )
