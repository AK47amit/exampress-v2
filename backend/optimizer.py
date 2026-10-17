import os
import re
import gc
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib import colors

# --- STEP 1: Devanagari Hindi Font Registration ---
FONT_NAME = "HindiFont"
font_paths = [
    "assets/NotoSansDevanagari-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
    "C:/Windows/Fonts/mangal.ttf",  # Windows Mangal font fallback
    "C:/Windows/Fonts/Nirmala.ttf"   # Windows Nirmala UI fallback
]

font_registered = False
for path in font_paths:
    if os.path.exists(path):
        try:
            pdfmetrics.registerFont(TTFont(FONT_NAME, path))
            font_registered = True
            break
        except Exception:
            continue


# --- STEP 2: Paragraph Styles Setup with Hindi Font & CJK Wrapping ---
styles = getSampleStyleSheet()

hindi_question_style = ParagraphStyle(
    'HindiQuestionStyle',
    parent=styles['Normal'],
    fontName=FONT_NAME if font_registered else 'Helvetica',
    fontSize=10,
    leading=14,
    textColor=colors.black,
    wordWrap='CJK',
    spaceAfter=6,
    keepWithNext=True  # Ensures question stays attached to its options/next flowable
)

hindi_option_style = ParagraphStyle(
    'HindiOptionStyle',
    parent=styles['Normal'],
    fontName=FONT_NAME if font_registered else 'Helvetica',
    fontSize=9.5,
    leading=13,
    textColor=colors.black,
    wordWrap='CJK',
    leftIndent=15,
    spaceAfter=4
)


class DocumentOptimizer:
    """
    Handles memory optimization, chapter-wise chunking, garbage collection,
    and high-fidelity text preservation for massive publishing projects using ReportLab.
    """

    @staticmethod
    def clean_hindi_text(text: str) -> str:
        """
        High-fidelity text preservation for Devanagari Hindi text extracted from manuscripts.
        Safely preserves all original characters, matras, and formatting without aggressive alterations.
        """
        if not text or not isinstance(text, str):
            return ""

        # Safe whitespace cleanup while preserving all original Devanagari characters and matras
        cleaned = text.strip()
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)

        return cleaned

    @staticmethod
    def optimize_canonical_book(canonical_data: dict) -> dict:
        """
        Iterates through the entire canonical book data structure 
        and applies high-fidelity safe preservation and multi-column atomic block rules.
        """
        if not canonical_data or "chapters" not in canonical_data:
            return canonical_data

        # Ensure column count constraints are explicitly preserved (Supports 1, 2, or 3 columns)
        column_count = canonical_data.get("column_count", 2)
        if column_count not in [1, 2, 3]:
            canonical_data["column_count"] = 2

        for chapter in canonical_data.get("chapters", []):
            if "chapter_title" in chapter:
                chapter["chapter_title"] = DocumentOptimizer.clean_hindi_text(chapter["chapter_title"])

            for block in chapter.get("blocks", []):
                if "text" in block:
                    block["text"] = DocumentOptimizer.clean_hindi_text(block["text"])

                if "options" in block and isinstance(block["options"], list):
                    block["options"] = [DocumentOptimizer.clean_hindi_text(opt) for opt in block["options"]]

                if "explanation" in block and block["explanation"]:
                    block["explanation"] = DocumentOptimizer.clean_hindi_text(block["explanation"])
                
                # --- STEP 3: Enforce Atomic Indivisible Block Flag for Multi-Column Layouts ---
                # Marks each question block so the rendering engine prevents column/page splitting
                block["cant_split"] = True

        return canonical_data

    @staticmethod
    def chunk_canonical_data(canonical_data: dict, chunk_size: int = 5) -> list[dict]:
        """
        Splits a massive book's chapters into smaller manageable chunks 
        to prevent memory spikes during ReportLab story compilation.
        """
        chapters = canonical_data.get("chapters", [])
        if len(chapters) <= chunk_size:
            return [canonical_data]

        chunks = []
        for i in range(0, len(chapters), chunk_size):
            chunk_chapters = chapters[i:i + chunk_size]
            chunk_data = canonical_data.copy()
            chunk_data["chapters"] = chunk_chapters
            chunk_data["title"] = f"{canonical_data.get('title', 'Book')} (Part {len(chunks) + 1})"
            chunks.append(chunk_data)
            
        return chunks

    @staticmethod
    def optimize_memory_after_render():
        """
        Forces Python garbage collection to release heavy flowable structures 
        and image buffers immediately after ReportLab PDF compilation.
        """
        gc.collect()