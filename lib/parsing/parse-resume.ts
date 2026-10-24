import { extractText, getDocumentProxy } from "unpdf";
import mammoth from "mammoth";
import { segmentSections, type ResumeSections } from "./sections";

export interface ParsedResume {
  text: string;
  sections: ResumeSections;
}

export const MAX_FILE_BYTES = 10 * 1024 * 1024; // 10 MB (docs/06-security-and-privacy.md)

export type ResumeFileType = "pdf" | "docx";

export function detectFileType(fileName: string, mime: string): ResumeFileType | null {
  const lower = fileName.toLowerCase();
  if (lower.endsWith(".pdf") || mime === "application/pdf") return "pdf";
  if (
    lower.endsWith(".docx") ||
    mime === "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
  ) {
    return "docx";
  }
  return null;
}

// Extracts plain text from a PDF or DOCX buffer and segments it into sections.
// Throws with a user-safe message on unreadable input — parse failures are
// visible, never silent (docs/04-workflows.md).
export async function parseResumeBuffer(
  buffer: Buffer,
  fileType: ResumeFileType
): Promise<ParsedResume> {
  let text = "";
  if (fileType === "pdf") {
    const pdf = await getDocumentProxy(new Uint8Array(buffer));
    const extracted = await extractText(pdf, { mergePages: true });
    text = extracted.text ?? "";
  } else {
    const result = await mammoth.extractRawText({ buffer });
    text = result.value ?? "";
  }
  const cleaned = text.replace(/\u0000/g, "").trim();
  if (cleaned.length < 20) {
    throw new Error("No readable text found in this file. Please upload a text-based PDF or DOCX.");
  }
  return { text: cleaned, sections: segmentSections(cleaned) };
}
