import os
import gc

class DocumentOptimizer:
    """
    Handles memory optimization, chapter-wise chunking, and garbage collection 
    for massive 500+ page publishing projects.
    """

    @staticmethod
    def chunk_canonical_data(canonical_data: dict, chunk_size: int = 5) -> list[dict]:
        """
        Splits a massive book's chapters into smaller manageable chunks 
        to prevent memory spikes during WeasyPrint DOM tree construction.
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
        Forces Python garbage collection to release heavy DOM structures 
        and image buffers immediately after PDF compilation.
        """
        gc.collect()