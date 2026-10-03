import os
from reportlab.lib.pagesizes import A4, B5
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """Canvas for adding running headers and professional page numbers."""
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
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, total_pages):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Skip header/footer on cover page (page 1)
        if self._pageNumber > 1:
            # Header
            self.drawString(36, self._pagesize[1] - 25, "Exampress V2 — AI Typesetting Engine")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(36, self._pagesize[1] - 30, self._pagesize[0] - 36, self._pagesize[1] - 30)
            
            # Footer
            page_text = f"Page {self._pageNumber} of {total_pages}"
            self.drawRightString(self._pagesize[0] - 36, 20, page_text)
            self.drawString(36, 20, "Confidential — Exampur Publication")
            self.line(36, 32, self._pagesize[0] - 36, 32)
            
        self.restoreState()

def generate_exampur_book(output_filename="exampress_final_book.pdf", book_type="quiz", format_size="B5"):
    pagesize = B5 if format_size == "B5" else A4
    
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=pagesize,
        rightMargin=36,
        leftMargin=36,
        topMargin=45,
        bottomMargin=45
    )
    
    # Calculate exact printable width dynamically based on page size & margins
    printable_width = pagesize[0] - 72  # 36 left + 36 right margin
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CoverTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=22,
        textColor=colors.HexColor("#1e293b"), alignment=1, spaceAfter=15
    )
    subtitle_style = ParagraphStyle(
        'CoverSubtitle', parent=styles['Normal'], fontName='Helvetica', fontSize=13,
        textColor=colors.HexColor("#475569"), alignment=1, spaceAfter=30
    )
    heading_style = ParagraphStyle(
        'ChapterHeading', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=13,
        textColor=colors.HexColor("#0f172a"), spaceBefore=10, spaceAfter=6
    )
    body_style = ParagraphStyle(
        'BookBody', parent=styles['Normal'], fontName='Helvetica', fontSize=10,
        leading=14, textColor=colors.HexColor("#334155"), spaceAfter=4
    )
    
    story = []
    
    # Cover Page
    story.append(Spacer(1, 80))
    story.append(Paragraph("EXAMPUR PUBLICATION DIVISION", subtitle_style))
    story.append(Paragraph("<b>AI-Powered Automated Typesetting Engine (V2)</b>", title_style))
    story.append(Paragraph(f"Book Type: {book_type.upper()} | Format: {format_size}", subtitle_style))
    story.append(Spacer(1, 120))
    story.append(Paragraph("Generated via Exampress V2 Core Engine | Press-Ready 300 DPI", ParagraphStyle('Footer', parent=body_style, alignment=1, textColor=colors.HexColor("#64748b"))))
    story.append(PageBreak())
    
    # Content Generation
    if book_type == "quiz":
        story.append(Paragraph("Chapter 1: Mock Practice Set (Automated Grid Flow)", heading_style))
        story.append(Spacer(1, 8))
        for i in range(1, 16):
            q_text = f"<b>Q.{i}</b> Sample exam question dynamically formatted via Exampress V2 engine."
            opt_text = f"(A) Option Alpha<br/>(B) Option Beta<br/>(C) Option Gamma<br/>(D) Option Delta"
            story.append(Paragraph(q_text, body_style))
            story.append(Paragraph(opt_text, ParagraphStyle('Opt', parent=body_style, leftIndent=12)))
            story.append(Spacer(1, 4))
    else:
        story.append(Paragraph("Chapter 1: Comprehensive Theory & Concepts", heading_style))
        story.append(Paragraph("Detailed study notes, structured headings, and bullet points designed under Exampur guidelines.", body_style))
        story.append(Spacer(1, 10))
        for i in range(1, 6):
            story.append(Paragraph(f"<b>1.{i} Core Concept Breakdown</b>", heading_style))
            story.append(Paragraph("Lorem ipsum dolor sit amet, consectetur adipiscing elit. Automated layout engine ensures clean pagination.", body_style))
            
            box_data = [[Paragraph("<b>Important Shortcut / Note:</b> Remember formula derivations for high-speed calculation.", body_style)]]
            t = Table(box_data, colWidths=[printable_width])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
                ('PADDING', (0,0), (-1,-1), 8),
            ]))
            story.append(Spacer(1, 4))
            story.append(t)
            story.append(Spacer(1, 10))
            
    doc.build(story, canvasmaker=NumberedCanvas)
    return output_filename