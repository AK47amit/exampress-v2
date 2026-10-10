import os

class PreflightValidator:
    """
    Enterprise Preflight Checker: Validates canonical structure, questions integrity, 
    and asset references prior to WeasyPrint rendering.
    """
    
    @staticmethod
    def run_preflight_checks(canonical_data: dict) -> tuple[bool, list[str]]:
        warnings = []
        errors = []
        
        # 1. Check basic metadata
        if not canonical_data.get("title"):
            warnings.warn("Missing book title. Defaulting to Untitled.")
            canonical_data["title"] = "Untitled Publication"
            
        chapters = canonical_data.get("chapters", [])
        if not chapters:
            errors.append("Critical: The book contains zero chapters or sections to render.")
            return False, errors
            
        # 2. Iterate and inspect chapters & blocks
        for ch_idx, chapter in enumerate(chapters):
            ch_title = chapter.get(f"chapter_title", f"Chapter {ch_idx + 1}")
            blocks = chapter.get("blocks", [])
            
            if not blocks:
                warnings.append(f"Warning: '{ch_title}' has no content blocks.")
                
            for b_idx, block in enumerate(blocks):
                b_type = block.get("type")
                
                if b_type == "question":
                    # Check question text
                    if not block.get("text"):
                        errors.append(f"Error in {ch_title}, Question #{b_idx + 1}: Missing question text.")
                        
                    # Check options for MCQ
                    options = block.get("options", [])
                    if not options or len(options) < 2:
                        warnings.append(f"Warning in {ch_title}, Question #{b_idx + 1}: MCQ has fewer than 2 options.")
                        
                    # Check correct answer key
                    answer = block.get("answer")
                    if not answer:
                        warnings.append(f"Warning in {ch_title}, Question #{b_idx + 1}: Answer key is missing.")
                        
                elif b_type == "image":
                    img_path = block.get("path")
                    if img_path and not os.path.exists(img_path):
                        errors.append(f"Error in {ch_title}, Image block #{b_idx + 1}: Referenced image file not found on disk ({img_path}).")

        # If critical errors found, reject compilation
        if errors:
            return False, errors + warnings
            
        return True, warnings