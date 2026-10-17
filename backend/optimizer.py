import os
import re
import gc

class DocumentOptimizer:
    """
    Handles memory optimization, chapter-wise chunking, garbage collection,
    and Hindi text normalization for massive publishing projects using ReportLab.
    """

    @staticmethod
    def clean_hindi_text(text: str) -> str:
        """
        Normalizes and cleans Devanagari Hindi text extracted from manuscripts.
        Fixes spacing issues around punctuation, broken matras, double spaces, and Unicode artifacts.
        """
        if not text or not isinstance(text, str):
            return ""

        # 1. Strip leading/trailing whitespaces
        cleaned = text.strip()

        # 2. Remove invisible Unicode whitespace characters & zero-width spaces
        cleaned = re.sub(r'[\u200b\u200c\u200d\uFEFF]', '', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)  # Collapse multiple spaces into single space

        # 3. Standardize punctuation spacing in bilingual/Hindi text
        cleaned = re.sub(r'\s*/\s*', ' / ', cleaned)
        
        # Fix spacing before question marks, commas, or full stops (Purna Viram `।`)
        cleaned = re.sub(r'\s+([।\?,\.])', r'\1', cleaned)
        
        # Ensure a single space after full stops or question marks if followed by text
        cleaned = re.sub(r'([।\?,\.])([^\s\d])', r'\1 \2', cleaned)

        # 4. Standardize option markers (e.g., convert [ a ], ( a ), {A} into uniform [A] format)
        cleaned = re.sub(r'[\(\{\[]\s*([A-Da-d])\s*[\)\}\]]', r'[\1]', cleaned)

        # 5. Fix common Devanagari / Hindi typesetting spacing bugs around hyphens
        cleaned = re.sub(r'\s*-\s*', ' - ', cleaned)

        return cleaned.strip()

    @staticmethod
    def optimize_canonical_book(canonical_data: dict) -> dict:
        """
        Iterates through the entire canonical book data structure 
        and applies Hindi text cleaning to all chapters, questions, options, and explanations.
        """
        if not canonical_data or "chapters" not in canonical_data:
            return canonical_data

        for chapter in canonical_data.get("chapters", []):
            # Optimize chapter title
            if "chapter_title" in chapter:
                chapter["chapter_title"] = DocumentOptimizer.clean_hindi_text(chapter["chapter_title"])

            for block in chapter.get("blocks", []):
                # Optimize question text
                if "text" in block:
                    block["text"] = DocumentOptimizer.clean_hindi_text(block["text"])

                # Optimize options list
                if "options" in block and isinstance(block["options"], list):
                    block["options"] = [DocumentOptimizer.clean_hindi_text(opt) for opt in block["options"]]

                # Optimize explanation
                if "explanation" in block and block["explanation"]:
                    block["explanation"] = DocumentOptimizer.clean_hindi_text(block["explanation"])

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