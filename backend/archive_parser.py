import os
import zipfile
import tempfile
import re
import shutil
from parser import parse_uploaded_file

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

def extract_and_parse_archive(archive_path: str, book_type: str, format_size: str, column_count: int = 2) -> dict:
    """
    Extracts uploaded zip archives securely, validates file constraints, sorts files naturally,
    and consolidates parsed chapters into a single master canonical book schema for Playwright PDF rendering.
    """
    extracted_dir = tempfile.mkdtemp()
    
    try:
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
        
        file_entries = []
        for root, dirs, files in os.walk(extracted_dir):
            for file in files:
                if file.startswith('.') or '__MACOSX' in root or file.startswith('~$'):
                    file_path = os.path.join(root, file)
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
                    continue
                
                file_path = os.path.join(root, file)
                file_entries.append((file, file_path))

        file_entries.sort(key=lambda x: natural_sort_key(x[0]))

        if not file_entries:
            raise ValueError("No valid document files found inside the archive (empty or hidden files only).")

        for file, file_path in file_entries:
            ext = os.path.splitext(file)[1].lower()
            
            if ext in [".json", ".xlsx", ".xls", ".csv", ".docx", ".txt", ".pdf"]:
                try:
                    base_clean_name = re.sub(r'\.[^.]+$', '', file)
                    display_title = re.sub(r'^(section\s*\d+[\:\-]?\s*)?(\d+[\.\-\s]*)?', '', base_clean_name, flags=re.IGNORECASE).strip()
                    display_title = re.sub(r'\s*\(\d+\)\s*$', '', display_title).strip()
                    if not display_title:
                        display_title = base_clean_name if base_clean_name else "Practice Chapter"

                    # Parses inner file into canonical data structure compatible with Playwright generator
                    parsed_book = parse_uploaded_file(
                        file_path=file_path,
                        file_extension=ext,
                        book_type=book_type,
                        format_size=format_size,
                        column_count=column_count
                    )
                    
                    file_blocks = []
                    if isinstance(parsed_book, dict) and "chapters" in parsed_book:
                        for chap in parsed_book.get("chapters", []):
                            if "blocks" in chap:
                                file_blocks.extend(chap["blocks"])

                    if file_blocks:
                        consolidated_chapter = {
                            "chapter_title": display_title,
                            "blocks": file_blocks
                        }
                        all_chapters.append(consolidated_chapter)

                except Exception as sub_err:
                    print(f"Error parsing inner file {file}: {str(sub_err)}")
                    raise ValueError(f"Error parsing inner file {file}: {str(sub_err)}")

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
            try:
                shutil.rmtree(extracted_dir)
            except Exception:
                pass