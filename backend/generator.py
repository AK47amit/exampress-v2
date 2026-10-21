
import os
from xml.sax.saxutils import escape

from fastapi import HTTPException

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, B5
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    Spacer,
    BaseDocTemplate,
    PageTemplate,
    Frame,
)


class PDFGenerator:
    def __init__(self, template_dir=None):
        self.template_dir = template_dir or os.path.dirname(
            os.path.abspath(__file__)
        )

        self.font_dir = os.path.join(self.template_dir, "fonts")

        self.regular_font_path = os.path.join(
            self.font_dir, "NotoSansDevanagari-Regular.ttf"
        )
        self.bold_font_path = os.path.join(
            self.font_dir, "NotoSansDevanagari-Bold.ttf"
        )

        self.body_font = "Devanagari"
        self.bold_font = "Devanagari-Bold"

        self._register_fonts()

    def _register_fonts(self):
        """Register Devanagari fonts with ReportLab shaping enabled."""

        if not os.path.isfile(self.regular_font_path):
            raise RuntimeError(
                f"Hindi regular font not found: {self.regular_font_path}"
            )

        try:
            import uharfbuzz  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "Hindi shaping requires uharfbuzz. "
                "Install dependencies using: "
                "pip install 'reportlab[shaping]'"
            ) from exc

        # Avoid registering the same font repeatedly.
        registered = set(pdfmetrics.getRegisteredFontNames())

        if self.body_font not in registered:
            pdfmetrics.registerFont(
                TTFont(
                    self.body_font,
                    self.regular_font_path,
                    shapable=True,
                )
            )

        if os.path.isfile(self.bold_font_path):
            if self.bold_font not in registered:
                pdfmetrics.registerFont(
                    TTFont(
                        self.bold_font,
                        self.bold_font_path,
                        shapable=True,
                    )
                )
        else:
            # Use the regular Hindi font rather than a font
            # that may not contain Devanagari glyphs.
            self.bold_font = self.body_font

        # Map <b> and <i> tags to fonts that support Hindi.
        pdfmetrics.registerFontFamily(
            "Devanagari",
            normal=self.body_font,
            bold=self.bold_font,
            italic=self.body_font,
            boldItalic=self.bold_font,
        )

        # Fail early if shaping is not actually enabled.
        regular = pdfmetrics.getFont(self.body_font)

        if not getattr(regular, "shapable", False):
            raise RuntimeError(
                "Hindi font shaping is disabled. Check ReportLab "
                "and uharfbuzz versions."
            )

    @staticmethod
    def _safe_text(value):
        """Convert plain input to safe Paragraph XML text."""
        if value is None:
            return ""
        if isinstance(value, (dict, list, tuple)):
            value = str(value)
        return escape(str(value))

    @staticmethod
    def _get_question_text(block):
        return block.get("text") or block.get("question") or ""

    @staticmethod
    def _get_option_text(option):
        if isinstance(option, dict):
            return (
                option.get("text")
                or option.get("value")
                or option.get("option")
                or ""
            )
        return option if option is not None else ""

    def generate_pdf(
        self,
        output_filename="exampress_final_book.pdf",
        book_type="quiz",
        format_size="B5",
        book_data=None,
        canonical_data=None,
        column_count=2,
        font_size=9.0,
        line_spacing=13.0,
        question_gap=6.0,
        option_top_gap=2.0,
        column_gap_val=10.0,
        footer_bottom_margin=22.0,
        top_header_margin=15.0,
        option_vertical_gap=1.5,
        header_font_size=16.0,
        header_bold=True,
        header_italic=False,
        header_alignment=0,
    ):
        # 1. Normalize and validate the incoming data.
        data = canonical_data if isinstance(canonical_data, dict) else book_data

        if not isinstance(data, dict):
            raise HTTPException(
                status_code=400,
                detail="Content Integrity Error: Missing book data.",
            )

        # Do not mutate the caller's canonical_data.
        data = dict(data)

        column_count = int(data.get("column_count", column_count))
        format_size = str(data.get("format_size", format_size)).upper()
        book_type = data.get("book_type", book_type)

        chapters = data.get("chapters") or []

        if not chapters:
            blocks = data.get("blocks", data.get("questions", []))
            if blocks:
                chapters = [
                    {
                        "chapter_title": "Main Chapter",
                        "blocks": blocks,
                    }
                ]

        if not isinstance(chapters, list) or not chapters:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Content Integrity Error: No valid chapters "
                    "or questions were supplied."
                ),
            )

        if column_count < 1 or column_count > 4:
            raise HTTPException(
                status_code=400,
                detail="column_count must be between 1 and 4.",
            )

        if font_size <= 0 or line_spacing <= 0:
            raise HTTPException(
                status_code=400,
                detail="font_size and line_spacing must be positive.",
            )

        # 2. Resolve page size.
        page_sizes = {
            "A4": A4,
            "B5": B5,
        }

        if format_size not in page_sizes:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported page size: {format_size}. Use A4 or B5.",
            )

        pagesize = page_sizes[format_size]
        page_width, page_height = pagesize

        # 3. Calculate margins and column frames.
        margin = 36.0

        usable_width = page_width - (2 * margin)
        usable_height = (
            page_height
            - (2 * margin)
            - float(footer_bottom_margin)
            - float(top_header_margin)
        )

        if usable_width <= 0 or usable_height <= 0:
            raise HTTPException(
                status_code=400,
                detail="Margins leave no usable page area.",
            )

        column_gap_val = float(column_gap_val)
        col_width = (
            usable_width - ((column_count - 1) * column_gap_val)
        ) / column_count

        if col_width <= 0:
            raise HTTPException(
                status_code=400,
                detail="Column width is invalid. Reduce the column gap.",
            )

        frames = []

        for i in range(column_count):
            col_x = margin + i * (col_width + column_gap_val)

            frame = Frame(
                col_x,
                margin + float(footer_bottom_margin),
                col_width,
                usable_height,
                id=f"col_{i + 1}",
                leftPadding=0,
                rightPadding=0,
                topPadding=0,
                bottomPadding=0,
            )
            frames.append(frame)

        # 4. Prepare the output path.
        abs_output_path = os.path.abspath(output_filename)
        output_dir = os.path.dirname(abs_output_path)

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        doc = BaseDocTemplate(
            abs_output_path,
            pagesize=pagesize,
            leftMargin=margin,
            rightMargin=margin,
            topMargin=margin,
            bottomMargin=margin,
            title=str(data.get("title") or "Exampress Practice Book"),
        )

        doc.addPageTemplates(
            [
                PageTemplate(
                    id="multi_column_template",
                    frames=frames,
                )
            ]
        )

        # 5. Typography styles.
        alignment_map = {
            0: TA_LEFT,
            1: TA_CENTER,
            2: TA_RIGHT,
        }
        alignment = alignment_map.get(header_alignment, TA_LEFT)

        title_font = self.bold_font if header_bold else self.body_font

        title_style = ParagraphStyle(
            "BookTitle",
            fontName=title_font,
            fontSize=float(header_font_size) + 4,
            leading=float(header_font_size) + 7,
            alignment=alignment,
            textColor=colors.HexColor("#1e293b"),
            wordWrap="LTR",
        )

        chapter_style = ParagraphStyle(
            "ChapterTitle",
            fontName=self.bold_font,
            fontSize=float(header_font_size),
            leading=float(header_font_size) + 5,
            alignment=alignment,
            textColor=colors.HexColor("#0f766e"),
            wordWrap="LTR",
        )

        question_style = ParagraphStyle(
            "QuestionText",
            fontName=self.body_font,
            fontSize=float(font_size),
            leading=float(line_spacing),
            textColor=colors.HexColor("#334155"),
            wordWrap="LTR",
        )

        option_style = ParagraphStyle(
            "OptionText",
            fontName=self.body_font,
            fontSize=float(font_size),
            leading=float(line_spacing),
            textColor=colors.HexColor("#475569"),
            wordWrap="LTR",
        )

        story = []

        # 6. Book title.
        book_title = data.get("title") or "Exampress Practice Book"

        if header_italic:
            safe_title = (
                f'<i>{self._safe_text(book_title)}</i>'
            )
        else:
            safe_title = self._safe_text(book_title)

        story.append(Paragraph(safe_title, title_style))
        story.append(Spacer(1, 15))

        # 7. Chapters, questions and options.
        for chapter_index, chapter in enumerate(chapters):
            if not isinstance(chapter, dict):
                continue

            chapter_title = chapter.get("chapter_title") or "Chapter"
            story.append(
                Paragraph(
                    self._safe_text(chapter_title),
                    chapter_style,
                )
            )
            story.append(Spacer(1, float(question_gap)))

            blocks = chapter.get("blocks") or chapter.get("questions") or []

            if not isinstance(blocks, list):
                continue

            for question_index, block in enumerate(blocks, start=1):
                if not isinstance(block, dict):
                    continue

                question_text = self._get_question_text(block)
                if not str(question_text).strip():
                    continue

                # Escape user content, but keep our own markup.
                question_number = (
                    f"<b>Q{question_index}.</b> "
                )
                question_markup = (
                    question_number + self._safe_text(question_text)
                )

                story.append(
                    Paragraph(question_markup, question_style)
                )
                story.append(Spacer(1, float(option_top_gap)))

                options = block.get("options") or []

                if isinstance(options, list):
                    for option_index, option in enumerate(options):
                        label = chr(65 + option_index)
                        option_text = self._get_option_text(option)

                        option_markup = (
                            f"<b>({label})</b> "
                            f"{self._safe_text(option_text)}"
                        )

                        story.append(
                            Paragraph(option_markup, option_style)
                        )
                        story.append(
                            Spacer(1, float(option_vertical_gap))
                        )

                story.append(Spacer(1, float(question_gap)))

        # 8. Build the PDF.
        try:
            doc.build(story)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"PDF generation failed: {type(exc).__name__}: {exc}",
            ) from exc

        if not os.path.isfile(abs_output_path):
            raise HTTPException(
                status_code=500,
                detail="PDF generation finished but the output file was not found.",
            )

        return abs_output_path
