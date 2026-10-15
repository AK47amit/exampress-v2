import os
from reportlab.lib.pagesizes import letter, B5
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def register_fonts():
    font_dir = os.path.join(os.path.dirname(__file__), "fonts")
    regular_path = os.path.join(font_dir, "NotoSansDevanagari_Condensed-Regular.ttf")
    bold_path = os.path.join(font_dir, "NotoSansDevanagari_Condensed-Bold.ttf")
    
    # Register Devanagari fonts to completely eliminate tofu/boxes
    pdfmetrics.registerFont(TTFont('HindiRegular', regular_path))
    pdfmetrics.registerFont(TTFont('HindiBold', bold_path))

def generate_exampur_book(
    output_filename="exampress_final_book.pdf", 
    book_type="quiz", 
    format_size="B5", 
    book_data=None, 
    canonical_data=None, 
    column_count=2,                # Dynamic Support for 2 or 3 Columns
    # --- Manual Spacing & Typesetting Controls (Parameters a to g) ---
    font_size=9.0,                 # Base Font Size
    line_spacing=13.0,             # Line Spacing / Leading (Parameter a & b)
    question_gap=10.0,             # Space after a question / before next question (Parameter d)
    option_top_gap=4.0,            # Space between question text and options (Parameter c)
    column_gap_val=12.0,           # Gutter space between columns (Parameter e)
    footer_bottom_margin=30.0,     # Page footer / margin spacing (Parameter f)
    option_vertical_gap=2.0        # Vertical spacing between individual options (Parameter g)
):
    """
    Enterprise Layout Engine using ReportLab BaseDocTemplate & Frames for 
    True Multi-Column (2-Column or 3-Column) Flowable Typesetting with Chapter Page Breaks.
    """
    register_fonts()

    # Section 3.4: Robust Pipeline Integration from Canonical Model
    if canonical_data:
        column_count = int(canonical_data.get("column_count", column_count))
        format_size = canonical_data.get("format_size", format_size)
        book_type = canonical_data.get("book_type", book_type)
        
        book_data = {
            "title": canonical_data.get("title", "Exampress Practice Book"),
            "publisher": "EXAMPUR PUBLICATION DIVISION",
            "author": canonical_data.get("author", "Editorial Board (V2 Engine)"),
            "chapters": []
        }
        
        for chap in canonical_data.get("chapters", []):
            formatted_questions = []
            chap_answer_key = []
            
            for block in chap.get("blocks", []):
                if block.get("type") == "question":
                    q_no = block.get("q_no", 1)
                    ans_val = block.get("answer", "A")
                    exp_val = block.get("explanation", "Verified by editorial board.")
                    
                    formatted_questions.append({
                        "q_no": q_no,
                        "question": block.get("text", ""),
                        "options": block.get("options", []),
                        "answer": ans_val,
                        "explanation": exp_val
                    })
                    
                    chap_answer_key.append({
                        "q": q_no,
                        "ans": ans_val,
                        "exp": exp_val
                    })
                    
            book_data["chapters"].append({
                "chapter_title": chap.get("chapter_title", "Chapter"),
                "questions": formatted_questions,
                "answer_key": chap_answer_key
            })

    if not book_data or not book_data.get("chapters"):
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
                            "question": "Which institution is organizing the Critical Minerals Innovation Hackathon 2026?",
                            "options": ["[A] IICT / आईआईसीटी", "[B] JNARDDC, Nagpur", "[C] DRDO / डीआरडीओ", "[D] T-Hub / टी-हब"],
                            "answer": "[B]",
                            "explanation": "Verified by editorial board."
                        }
                    ],
                    "answer_key": [
                        {"q": 1, "ans": "[B]", "exp": "JNARDDC, Nagpur"}
                    ]
                }
            ]
        }

    # Page dimensions setup (B5 standard for Exampur books)
    page_width, page_height = B5 if format_size.upper() == "B5" else letter
    
    # Margins setup
    margin = 30
    printable_width = page_width - (2 * margin)
    printable_height = page_height - margin - footer_bottom_margin

    # True Multi-Column Frame Calculation (Supports 2 or 3 columns dynamically)
    if column_count not in [2, 3]:
        column_count = 2  # Default fallback

    col_width = (printable_width - ((column_count - 1) * column_gap_val)) / column_count

    frames = []
    for i in range(column_count):
        col_x = margin + i * (col_width + column_gap_val)
        frame = Frame(
            col_x, 
            footer_bottom_margin, 
            col_width, 
            printable_height, 
            leftPadding=4, 
            rightPadding=4, 
            topPadding=4, 
            bottomPadding=4,
            id=f'col_{i+1}'
        )
        frames.append(frame)

    doc = BaseDocTemplate(output_filename, pagesize=(page_width, page_height))
    template = PageTemplate(id='multi_col_template', frames=frames)
    doc.addPageTemplates([template])

    story = []

    # Styles mapped with config parameters (a to g)
    title_style = ParagraphStyle(
        name='ExampurTitle',
        fontName='HindiBold',
        fontSize=16,
        leading=20,
        alignment=1, # Center
        spaceAfter=15
    )
    
    chapter_style = ParagraphStyle(
        name='ExampurChapter',
        fontName='HindiBold',
        fontSize=12,
        leading=16,
        spaceAfter=10,
        spaceBefore=15
    )

    question_style = ParagraphStyle(
        name='ExampurQuestion',
        fontName='HindiBold',
        fontSize=font_size,
        leading=line_spacing,          # Parameter a & b
        spaceAfter=option_top_gap      # Parameter c
    )

    option_style = ParagraphStyle(
        name='ExampurOption',
        fontName='HindiRegular',
        fontSize=font_size - 0.5,
        leading=line_spacing - 2,
        spaceAfter=option_vertical_gap # Parameter g
    )

    # 1. Cover / Header Title Section
    theme_accent = colors.HexColor('#047857' if book_type == "quiz" else ('#1d4ed8' if book_type == "theory" else '#b91c1c'))
    
    story.append(Paragraph(book_data.get("publisher", "EXAMPUR PUBLICATION DIVISION"), ParagraphStyle(name='Pub', fontName='HindiBold', fontSize=9, alignment=1, textColor=theme_accent, spaceAfter=8)))
    story.append(Paragraph(book_data.get("title"), title_style))
    story.append(Spacer(1, 10))

    # 2. Chapters Loop with Page Breaks & Chapter-End Answer Keys
    for index, chap in enumerate(book_data.get("chapters", [])):
        if index > 0:
            story.append(PageBreak()) # Har naya chapter naye page se start hoga
            
        story.append(Paragraph(chap.get("chapter_title"), chapter_style))
        
        for q in chap.get("questions", []):
            q_elements = []
            q_text = f"<b>Q.{q.get('q_no')}</b> {q.get('question')}"
            q_elements.append(Paragraph(q_text, question_style))
            
            # Append options line by line
            for opt in q.get("options", []):
                q_elements.append(Paragraph(opt, option_style))
            
            if q.get('answer'):
                ans_style = ParagraphStyle(name='AnsStyle', fontName='HindiBold', fontSize=8, textColor=theme_accent)
                q_elements.append(Paragraph(f"Correct Answer: {q.get('answer')}", ans_style))
                
            if book_type == "solutions" and q.get('explanation'):
                exp_style = ParagraphStyle(name='ExpStyle', fontName='HindiRegular', fontSize=7.5, textColor=colors.HexColor('#475569'))
                q_elements.append(Paragraph(f"Exp: {q.get('explanation')}", exp_style))

            q_elements.append(Spacer(1, question_gap)) # Parameter d: Question gap
            
            # Keep question block together to avoid breaking awkwardly across columns/pages
            story.append(KeepTogether(q_elements))

        # 3. Chapter-End Answer Key Table
        if chap.get("answer_key"):
            story.append(Spacer(1, 10))
            story.append(Paragraph(f"Answer Key - {chap.get('chapter_title')}", chapter_style))
            
            th_style = ParagraphStyle(name='THStyle', fontName='HindiBold', fontSize=7.5, textColor=colors.HexColor('#0f172a'))
            td_style = ParagraphStyle(name='TDStyle', fontName='HindiRegular', fontSize=7.5, textColor=colors.HexColor('#334155'))
            
            table_data = [[
                Paragraph("Q", th_style), 
                Paragraph("Ans", th_style), 
                Paragraph("Explanation", th_style)
            ]]
            
            for item in chap.get("answer_key", []):
                table_data.append([
                    Paragraph(str(item.get('q')), td_style),
                    Paragraph(str(item.get('ans')), td_style),
                    Paragraph(str(item.get('exp')), td_style)
                ])
            
            ans_table = Table(table_data, colWidths=[30, 40, printable_width - 70])
            ans_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ]))
            story.append(ans_table)

    # Build PDF via ReportLab Multi-Column BaseDocTemplate Engine
    doc.build(story)
    return output_filename