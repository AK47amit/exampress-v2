import os
import zipfile
import tempfile
from parser import parse_uploaded_file

def extract_and_parse_archive(archive_path: str, book_type: str, format_size: str, column_count: int = 2) -> dict:
    """
    Extracts a ZIP archive with strict security validation (Zip Bomb & Path Traversal protection),
    iterates through all contained files, parses them via Universal Parser, and merges them into a single Canonical Book Schema.
    """
    extracted_dir = tempfile.mkdtemp()
    
    try:
        # Extract archive contents with strict security validation
        if zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                # Security checks: Limit total uncompressed size, file count, and check for path traversal
                file_count = len(zip_ref.namelist())
                if file_count > 100:
                    raise ValueError("Archive contains too many files. Maximum allowed limit is 100 files.")
                
                total_uncompressed_size = 0
                for zinfo in zip_ref.infolist():
                    total_uncompressed_size += zinfo.file_size
                    filename = zinfo.filename
                    # Path traversal protection
                    if filename.startswith('/') or '..' in filename or os.path.isabs(filename):
                        raise ValueError(f"Malicious file path traversal detected in archive: {filename}")
                
                if total_uncompressed_size > 100 * 1024 * 1024:  # 100MB uncompressed limit (Zip Bomb protection)
                    raise ValueError("Archive uncompressed size exceeds the 100MB safety limit.")
                
                zip_ref.extractall(extracted_dir)
        else:
            raise ValueError("Only standard ZIP archives are currently supported for batch extraction.")

        all_chapters = []
        master_title = "Exampress Master Consolidated Edition"
        
        # Walk through extracted folder recursively to catch files in nested folders
        chapter_index = 1
        for root, dirs, files in os.walk(extracted_dir):
            for file in sorted(files):
                # Ignore hidden system files like __MACOSX or .DS_Store
                if file.startswith('.') or '__MACOSX' in root:
                    continue
                
                file_path = os.path.join(root, file)
                ext = os.path.splitext(file)[1].lower()
                
                if ext in [".json", ".xlsx", ".xls", ".csv", ".docx", ".txt", ".pdf"]:
                    try:
                        # Parse individual file into Canonical Schema format with column support
                        parsed_book = parse_uploaded_file(
                            file_path=file_path,
                            file_extension=ext,
                            book_type=book_type,
                            format_size=format_size,
                            column_count=column_count
                        )
                        
                        # Collect all chapters/blocks from this parsed file
                        if isinstance(parsed_book, dict) and "chapters" in parsed_book:
                            for chap in parsed_book.get("chapters", []):
                                chap["chapter_title"] = f"Section {chapter_index}: {file} - {chap.get('chapter_title', 'Content')}"
                                all_chapters.append(chap)
                                chapter_index += 1
                    except Exception as sub_err:
                        # Skip corrupted or unsupported files within archive gracefully without crashing pipeline
                        print(f"Skipping inner file {file} due to parse error: {str(sub_err)}")
                        continue

        if not all_chapters:
            raise ValueError("No valid document files (.docx, .xlsx, .csv, .json, .txt, .pdf) found inside the archive.")

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
        # Clean up extracted temporary directory safely
        if os.path.exists(extracted_dir):
            import shutil
            try:
                shutil.rmtree(extracted_dir)
            except Exception:
                pass