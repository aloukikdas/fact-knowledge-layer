import re
import os
from typing import List, Dict, Any, Optional
import pymupdf
from pydantic import BaseModel, Field

class PageChunk(BaseModel):
    document_name: str
    page_number: int  # 1-based page index
    text: str
    footnotes: List[str] = Field(default_factory=list)
    char_count: int = 0

class PDFParser:
    FOOTNOTE_PATTERN = re.compile(
        r"^(?:(?:\*|\dagger|\(\d+\)|\d+\.|\bNote\b|\bSource\b|\bRestated\b)\s*[:\-\)].*|^\*+.*)",
        re.IGNORECASE
    )

    def __init__(self):
        pass

    def parse_page(self, doc_name: str, page_num: int, page: pymupdf.Page) -> PageChunk:
        """Extracts text from a page and isolates footnotes/qualifying notes."""
        raw_text = page.get_text("text") or ""
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        body_lines: List[str] = []
        footnotes: List[str] = []
        in_footnote_section = False
        bottom_lines_collected: List[str] = []
        for line in reversed(lines):
            is_footnote_marker = bool(self.FOOTNOTE_PATTERN.match(line))
            if is_footnote_marker:
                in_footnote_section = True
                bottom_lines_collected.append(line)
            elif in_footnote_section and len(line) < 120 and (line.startswith("(") or line.startswith("*")):
                bottom_lines_collected.append(line)
            else:
                in_footnote_section = False
                body_lines.append(line)
        body_text = "\n".join(reversed(body_lines)).strip()
        footnotes = list(reversed(bottom_lines_collected))

        return PageChunk(
            document_name=doc_name,
            page_number=page_num,
            text=body_text,
            footnotes=footnotes,
            char_count=len(body_text)
        )

    def extract_document(self, file_path: str, max_pages: Optional[int] = None) -> List[PageChunk]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found at: {file_path}")

        doc_name = os.path.basename(file_path)
        doc = pymupdf.open(file_path)
        chunks: List[PageChunk] = []

        total_pages = len(doc)
        pages_to_read = min(total_pages, max_pages) if max_pages else total_pages

        for idx in range(pages_to_read):
            page_num = idx + 1
            page = doc[idx]
            chunk = self.parse_page(doc_name, page_num, page)
            if chunk.char_count > 40:
                chunks.append(chunk)

        doc.close()
        return chunks