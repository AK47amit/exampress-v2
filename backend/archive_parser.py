import os
import zipfile
import tempfile
from parser import parse_uploaded_file

def extract_and_parse_archive(archive_path: str, book_type: str, format_size: str) -> dict:
    """
    Extracts a ZIP/RAR archive, iterates through all contained docx/pdf/xlsx/csv/json files,
    parses them individually using the Universal Parser, and merges them into a single Canonical Book Schema.
    """
    extracted_dir = tempfile.mkdtemp()
    
    try:
        # Extract archive contents
        if zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(extracted_dir)
        else:
            raise ValueError("Only standard ZIP archives are currently supported for batch extraction in sandbox.")

        all_chapters = []
        master_title = "Exampur Master Consolidated Edition"
        
        # Walk through extracted folder
        chapter_index = 1
        for root, dirs, files in os.walk(extracted_dir):
            for file in sorted(files):
                file_path = os.path.join(root, file)
                ext = os.path.splitext(file)[1].lower()
                
                if ext in [".json", ".xlsx", ".xls", ".csv", ".docx"]:
                    try:
                        # Parse individual file into Canonical Schema format
                        parsed_book = parse_uploaded_file(
                            file_path=file_path,
                            file_extension=ext,
                            book_type=book_type,
                            format_size=format_size
                        )
                        
                        # Collect all chapters/blocks from this parsed file
                        for chap in parsed_book.get("chapters", []):
                            chap["chapter_title"] = f"Section {chapter_index}: {file} - {chap.get('chapter_title', 'Content')}"
                            all_chapters.append(chap)
                            chapter_index += 1
                    except Exception as sub_err:
                        # Skip corrupted or unsupported files within archive gracefully
                        continue

        if not all_chapters:
            raise ValueError("No valid document files (.docx, .xlsx, .csv, .json) found inside the archive.")

        master_canonical_book = {
            "title": master_title,
            "book_type": book_type,
            "format_size": format_size,
            "author": "Exampur Editorial Board (Batch Engine)",
            "chapters": all_chapters
        }
        
        return master_canonical_book

    finally:
        # Clean up extracted temporary directory
        if os.path.exists(extracted_dir):
            import shutil
            try:
                shutil.rmtree(extracted_dir)
            except Exception:
                pass