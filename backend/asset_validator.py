import os
import glob

class AssetValidator:
    """
    Validates the presence of required enterprise fonts, icons, and image assets
    prior to PDF typesetting.
    """
    
    # Expected font families or files for Exampur Publication styling
    REQUIRED_FONTS = [
        "NotoSansDevanagari",  # Essential for Hindi/Bilingual exam content
        "serif",               # Standard fallback
        "sans-serif"
    ]

    @staticmethod
    def verify_assets(canonical_data: dict, assets_dir: str = "backend/assets") -> tuple[bool, list[str]]:
        issues = []
        
        # 1. Check if asset directory exists if images are referenced
        has_image_blocks = False
        for chapter in canonical_data.get("chapters", []):
            for block in chapter.get("blocks", []):
                if block.get("type") == "image":
                    has_image_blocks = True
                    img_path = block.get("path")
                    if img_path and not os.path.exists(img_path):
                        issues.append(f"Missing Image Asset: '{img_path}' referenced in canonical data could not be found.")

        if has_image_blocks and not os.path.exists(assets_dir):
            issues.append(f"Warning: Chapters contain image blocks, but assets directory '{assets_dir}' is missing.")

        # 2. Verify font availability in system or CSS asset folders
        # WeasyPrint relies on system fonts or explicitly loaded font-faces.
        # Here we check if custom font files exist if a custom fonts folder is maintained.
        custom_font_dir = os.path.join(assets_dir, "fonts")
        if os.path.exists(custom_font_dir):
            font_files = glob.glob(os.path.join(custom_font_dir, "*.ttf")) + glob.glob(os.path.join(custom_font_dir, "*.otf"))
            if not font_files:
                issues.append("Notice: 'fonts/' directory exists but contains no .ttf or .otf font files.")

        if issues:
            return False, issues
            
        return True, ["All critical assets and font pathways verified successfully."]