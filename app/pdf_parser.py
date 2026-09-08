import re
import os
from typing import List, Optional
import pymupdf
from pydantic import BaseModel, Field

class PageChunk(BaseModel):
    document_name: str
    page_number: int
    text: str
    footnotes: List[str] = Field(default_factory=list)
    char_count: int = 0

class PDFParser:
    def __init__(self):
        self.keywords = [
            "corporate identity", "cin", "u63090", "l63090",
            "revenue from operations", "revenue",
            "pin codes", "pincodes", "pin code",
            "ebitda", "adjusted ebitda"
        ]

    def extract_document(self, file_path: str, max_pages: Optional[int] = None) -> List[PageChunk]:
        doc_name = os.path.basename(file_path)
        doc = pymupdf.open(file_path)
        total_pages = len(doc)
        
        chunks = []
        for idx in range(total_pages):
            page = doc[idx]
            text = page.get_text("text") or ""
            text_lower = text.lower()
            
            # Always grab cover pages, plus any page with target keywords and financial figures
            has_num = bool(re.search(r'\d', text))
            if idx < 3 or (has_num and any(kw in text_lower for kw in self.keywords)):
                footer_rect = pymupdf.Rect(0, page.rect.height * 0.65, page.rect.width, page.rect.height)
                footer_text = page.get_text("text", clip=footer_rect).strip()
                
                chunks.append(PageChunk(
                    document_name=doc_name,
                    page_number=idx + 1,
                    text=text,
                    footnotes=[footer_text] if footer_text else [],
                    char_count=len(text)
                ))
        doc.close()
        return chunks