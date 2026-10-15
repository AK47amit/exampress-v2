from dataclasses import dataclass

@dataclass
class BookLayoutConfig:
    # Font & Line Spacing (Parameters a & b)
    font_name: str = "HindiFont"  # Noto Sans Devanagari / Mangal
    font_size: float = 10.0       # Base font size for questions/text
    line_spacing: float = 14.0    # Leading / space between lines (a & b)
    
    # Spacings & Gaps (Parameters c, d, e, f, g)
    question_gap: float = 8.0     # Vertical gap between two questions (c)
    option_top_gap: float = 4.0   # Space between question text and options (d)
    column_gap: float = 15.0      # Horizontal gutter spacing between columns (e)
    footer_bottom_margin: float = 20.0  # Space before page footer/margin (f)
    
    # Option Grid Spacing (Parameter g)
    option_horizontal_gap: float = 10.0  # Horizontal spacing between inline options (a, b, c, d)
    option_vertical_gap: float = 4.0     # Vertical spacing if options wrap into rows (g)

# Default Exampur-style configuration instance
DEFAULT_CONFIG = BookLayoutConfig()