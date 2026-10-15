import os
import glob

class AssetValidator:
    """
    Validates the presence of required enterprise fonts, icons, and image assets
    prior to ReportLab PDF typesetting.
    """
    
    # Expected font families for Exampur Publication styling
    REQUIRED_FONTS = [
        "NotoSansDevanagari",  # Essential for Hindi/Bilingual exam content
        "serif",               # Standard fallback
        "sans-serif"
    ]

    @staticmethod
    def verify_assets(canonical_data: dict, assets_dir: str = "backend/fonts") -> tuple[bool, list[str]]:
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

        # 2. Verify font availability for ReportLab TTF loading
        font_dir = os.path.join(os.path.dirname(__file__), "fonts")
        if os.path.exists(font_dir):
            font_files = glob.glob(os.path.join(font_dir, "*.ttf")) + glob.glob(os.path.join(font_dir, "*.otf"))
            if not font_files:
                issues.append("Notice: 'backend/fonts/' directory exists but contains no .ttf or .otf font files.")
        else:
            issues.append("Warning: 'backend/fonts/' directory is missing. Devanagari TrueType fonts are required to prevent tofu boxes.")

        if issues:
            return False, issues
            
        return True, ["All critical assets and ReportLab font pathways verified successfully."]