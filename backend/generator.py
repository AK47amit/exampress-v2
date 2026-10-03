import os
from reportlab.lib.pagesizes import A4, B5
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_exampur_book(output_filename="exampress_final_book.pdf", book_type="quiz", format_size="B5"):
    pagesize = B5 if format_size == "B5" else A4
    
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=pagesize,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
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
            t = Table(box_data, colWidths=[400])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
                ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
                ('PADDING', (0,0), (-1,-1), 8),
            ]))
            story.append(Spacer(1, 4))
            story.append(t)
            story.append(Spacer(1, 10))
            
    doc.build(story)
    return output_filename