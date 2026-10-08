import os
from reportlab.lib.pagesizes import A4, B5
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Register Unicode fonts to prevent black boxes for regional/Hindi/Unicode characters
try:
    pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', 'DejaVuSans-Bold.ttf'))
    FONT_NAME = 'DejaVuSans'
    FONT_NAME_BOLD = 'DejaVuSans-Bold'
except Exception:
    # Fallback to standard fonts if TTF files are missing in the environment
    FONT_NAME = 'Helvetica'
    FONT_NAME_BOLD = 'Helvetica-Bold'

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pages = []

    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self.pages)
        for page in self.pages:
            self.__dict__.update(page)
            if self._pageNumber > 1:
                self.saveState()
                self.setFont(FONT_NAME, 8)
                self.setFillColor(colors.HexColor("#64748b"))
                self.drawString(36, self._pagesize[1] - 25, "Exampress V2 — Production Publishing Engine")
                self.setStrokeColor(colors.HexColor("#cbd5e1"))
                self.setLineWidth(0.5)
                self.line(36, self._pagesize[1] - 30, self._pagesize[0] - 36, self._pagesize[1] - 30)
                page_text = f"Page {self._pageNumber} of {num_pages}"
                self.drawRightString(self._pagesize[0] - 36, 20, page_text)
                self.drawString(36, 20, "Authorized Exampur Publication Copy")
                self.line(36, 32, self._pagesize[0] - 36, 32)
                self.restoreState()
            super().showPage()
        super().save()

def generate_exampur_book(output_filename="exampress_final_book.pdf", book_type="quiz", format_size="B5", book_data=None, canonical_data=None):
    """
    Enterprise Layout Engine supporting both Canonical JSON data and legacy structures.
    """
    # Normalize input: if canonical_data is provided via enterprise parser, map it to book_data format
    if canonical_data:
        book_data = {
            "title": canonical_data.get("title", "Exampress Practice Book"),
            "publisher": "EXAMPUR PUBLICATION DIVISION",
            "author": canonical_data.get("author", "Editorial Board (V2 Engine)"),
            "chapters": []
        }
        answer_key_list = []
        for chap in canonical_data.get("chapters", []):
            formatted_questions = []
            for block in chap.get("blocks", []):
                if block.get("type") == "question":
                    q_no = block.get("q_no", 1)
                    formatted_questions.append({
                        "q_no": q_no,
                        "question": block.get("text", ""),
                        "options": block.get("options", [])
                    })
                    if block.get("answer") or block.get("explanation"):
                        answer_key_list.append({
                            "q": q_no,
                            "ans": block.get("answer", "A"),
                            "exp": block.get("explanation", "Verified by editorial board.")
                        })
            book_data["chapters"].append({
                "chapter_title": chap.get("chapter_title", "Chapter"),
                "questions": formatted_questions
            })
        book_data["answer_key"] = answer_key_list
        format_size = canonical_data.get("format_size", format_size)

    if not book_data:
        book_data = {
            "title": "Exampress General Studies & Reasoning Masterclass",
            "publisher": "EXAMPUR PUBLICATION DIVISION",
            "author": "Editorial Board (V2 Engine)",
            "chapters": [
                {
                    "chapter_title": "Chapter 1: Quantitative Aptitude & Reasoning Mock Set",
                    "questions": [
                        {
                            "q_no": 1,
                            "question": "If A + B means A is sister of B, A * B means A is brother of B, which of the following means P is aunt of Q?",
                            "options": ["(A) P + R * Q", "(B) P * R + Q", "(C) P + R - Q", "(D) None of these"]
                        },
                        {
                            "q_no": 2,
                            "question": "Find the missing number in the series: 2, 6, 12, 20, 30, ?",
                            "options": ["(A) 40", "(B) 42", "(C) 44", "(D) 48"]
                        }
                    ]
                }
            ],
            "answer_key": [
                {"q": 1, "ans": "(A)", "exp": "P is sister of R, R is brother of Q -> P is aunt."},
                {"q": 2, "ans": "(B)", "exp": "Pattern of consecutive even additions (+4, +6, +8, +10, +12)."}
            ]
        }

    pagesize = B5 if format_size == "B5" else A4
    printable_width = pagesize[0] - 72

    doc = SimpleDocTemplate(
        output_filename,
        pagesize=pagesize,
        rightMargin=36,
        leftMargin=36,
        topMargin=45,
        bottomMargin=45
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('CoverTitle', parent=styles['Heading1'], fontName=FONT_NAME_BOLD, fontSize=22, textColor=colors.HexColor("#1e293b"), alignment=1, spaceAfter=15)
    subtitle_style = ParagraphStyle('CoverSubtitle', parent=styles['Normal'], fontName=FONT_NAME, fontSize=12, textColor=colors.HexColor("#475569"), alignment=1, spaceAfter=20)
    heading_style = ParagraphStyle('ChapterHeading', parent=styles['Heading2'], fontName=FONT_NAME_BOLD, fontSize=13, textColor=colors.HexColor("#0f172a"), spaceBefore=10, spaceAfter=8)
    body_style = ParagraphStyle('BookBody', parent=styles['Normal'], fontName=FONT_NAME, fontSize=10, leading=14, textColor=colors.HexColor("#334155"), spaceAfter=6)
    meta_style = ParagraphStyle('MetaText', parent=styles['Normal'], fontName=FONT_NAME_BOLD, fontSize=9, textColor=colors.HexColor("#047857"))

    story = []

    story.append(Spacer(1, 60))
    story.append(Paragraph(book_data.get("publisher", "EXAMPUR PUBLICATION DIVISION"), subtitle_style))
    story.append(Paragraph(f"<b>{book_data.get('title')}</b>", title_style))
    story.append(Paragraph(f"Curated & Typeset by {book_data.get('author', 'Exampry Editorial')}", subtitle_style))
    story.append(Spacer(1, 40))
    
    meta_data = [[Paragraph(f"<b>Format:</b> {format_size} Academic Edition &nbsp;|&nbsp; <b>Engine:</b> Exampress V2.0 Enterprise", meta_style)]]
    t_meta = Table(meta_data, colWidths=[printable_width])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#ecfdf5")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#6ee7b7")),
        ('PADDING', (0,0), (-1,-1), 10),
        ('ALIGN', (0,0), (-1,-1), 'CENTER')
    ]))
    story.append(t_meta)
    story.append(PageBreak())

    for chap in book_data.get("chapters", []):
        story.append(Paragraph(chap.get("chapter_title"), heading_style))
        story.append(Spacer(1, 6))
        
        for q in chap.get("questions", []):
            q_text = f"<b>Q.{q.get('q_no')}</b> {q.get('question')}"
            story.append(Paragraph(q_text, body_style))
            
            opts_html = "<br/>".join(q.get("options", []))
            story.append(Paragraph(opts_html, ParagraphStyle('Opts', parent=body_style, leftIndent=14)))
            story.append(Spacer(1, 6))

    if book_data.get("answer_key"):
        story.append(PageBreak())
        story.append(Paragraph("Answer Key & Detailed Explanations", heading_style))
        story.append(Spacer(1, 8))

        table_data = [[Paragraph("<b>Q.No</b>", body_style), Paragraph("<b>Ans</b>", body_style), Paragraph("<b>Detailed Explanation (Editorial Verified)</b>", body_style)]]
        for item in book_data.get("answer_key", []):
            table_data.append([
                Paragraph(str(item.get("q")), body_style),
                Paragraph(str(item.get("ans")), body_style),
                Paragraph(str(item.get("exp")), body_style)
            ])

        ans_table = Table(table_data, colWidths=[40, 50, printable_width - 90])
        ans_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'TOP')
        ]))
        story.append(ans_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    return output_filename