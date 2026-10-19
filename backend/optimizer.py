import os
import re
import gc

class DocumentOptimizer:
    """
    Handles memory optimization, chapter-wise chunking, garbage collection,
    and high-fidelity text preservation for Playwright HTML pipelines.
    """

    @staticmethod
    def clean_hindi_text(text: str) -> str:
        if not text or not isinstance(text, str):
            return ""
        cleaned = text.strip()
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        return cleaned

    @staticmethod
    def optimize_canonical_book(canonical_data: dict) -> dict:
        if not canonical_data or "chapters" not in canonical_data:
            return canonical_data

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
                
                block["cant_split"] = True

        return canonical_data

    @staticmethod
    def chunk_canonical_data(canonical_data: dict, chunk_size: int = 5) -> list[dict]:
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
        gc.collect()