import os
import zipfile
import tempfile
import re
from parser import parse_uploaded_file

def natural_sort_key(s):
    """Helper to sort filenames naturally (e.g., 2 comes before 10)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

def extract_and_parse_archive(archive_path: str, book_type: str, format_size: str, column_count: int = 2) -> dict:
    """
    Extracts a ZIP archive securely, sorts files in exact natural numerical order (1 to 19+),
    parses each file individually via Universal Parser, and merges them sequentially without missing chapters.
    """
    extracted_dir = tempfile.mkdtemp()
    
    try:
        # Extract archive contents with strict security validation
        if zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                file_count = len(zip_ref.namelist())
                if file_count > 100:
                    raise ValueError("Archive contains too many files. Maximum allowed limit is 100 files.")
                
                total_uncompressed_size = 0
                for zinfo in zip_ref.infolist():
                    total_uncompressed_size += zinfo.file_size
                    filename = zinfo.filename
                    if filename.startswith('/') or '..' in filename or os.path.isabs(filename):
                        raise ValueError(f"Malicious file path traversal detected in archive: {filename}")
                
                if total_uncompressed_size > 100 * 1024 * 1024:
                    raise ValueError("Archive uncompressed size exceeds the 100MB safety limit.")
                
                zip_ref.extractall(extracted_dir)
        else:
            raise ValueError("Only standard ZIP archives are currently supported for batch extraction.")

        all_chapters = []
        master_title = "Exampress Master Consolidated Edition"
        
        # Collect all files recursively
        file_entries = []
        for root, dirs, files in os.walk(extracted_dir):
            for file in files:
                if file.startswith('.') or '__MACOSX' in root:
                    continue
                file_path = os.path.join(root, file)
                file_entries.append((file, file_path))

        # Sort files naturally (1.docx, 2.docx ... 10.docx ... 19.docx)
        file_entries.sort(key=lambda x: natural_sort_key(x[0]))

        for file, file_path in file_entries:
            ext = os.path.splitext(file)[1].lower()
            
            if ext in [".json", ".xlsx", ".xls", ".csv", ".docx", ".txt", ".pdf"]:
                try:
                    # Parse individual file into Canonical Schema format
                    parsed_book = parse_uploaded_file(
                        file_path=file_path,
                        file_extension=ext,
                        book_type=book_type,
                        format_size=format_size,
                        column_count=column_count
                    )
                    
                    # Collect all chapters from this parsed file and ensure clean titles
                    if isinstance(parsed_book, dict) and "chapters" in parsed_book:
                        for chap in parsed_book.get("chapters", []):
                            current_title = chap.get("chapter_title", "").strip()
                            
                            # Clean garbage/filename artifacts if present
                            if not current_title or ".docx" in current_title.lower() or "section" in current_title.lower():
                                clean_name = re.sub(r'\.[^.]+$', '', file)
                                clean_name = re.sub(r'^(section\s*\d+[\:\-]?\s*)?(\d+[\.\-\s]*)?', '', clean_name, flags=re.IGNORECASE).strip()
                                clean_name = re.sub(r'\s*\(\d+\)\s*$', '', clean_name).strip()
                                chap["chapter_title"] = clean_name if clean_name else "Practice Chapter"
                            
                            all_chapters.append(chap)
                except Exception as sub_err:
                    print(f"Skipping inner file {file} due to parse error: {str(sub_err)}")
                    continue

        if not all_chapters:
            raise ValueError("No valid document files found inside the archive.")

        master_canonical_book = {
            "title": master_title,
            "book_type": book_type,
            "format_size": format_size,
            "column_count": column_count,
            "author": "Exampur Editorial Board (Batch Engine)",
            "chapters": all_chapters
        }
        
        return master_canonical_book

    finally:
        if os.path.exists(extracted_dir):
            import shutil
            try:
                shutil.rmtree(extracted_dir)
            except Exception:
                pass