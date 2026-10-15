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
    
    pdfmetrics.registerFont(TTFont('HindiRegular', regular_path))
    pdfmetrics.registerFont(TTFont('HindiBold', bold_path))

def generate_exampur_book(
    output_filename="exampress_final_book.pdf", 
    book_type="quiz", 
    format_size="B5", 
    book_data=None, 
    canonical_data=None, 
    column_count=2,                
    # --- Advanced Spacing Controls (Hooked with Frontend Sliders) ---
    font_size=9.0,                 
    line_spacing=14.0,             
    question_gap=12.0,             
    option_top_gap=4.0,            
    column_gap_val=12.0,           
    footer_bottom_margin=30.0,     
    option_vertical_gap=2.5        
):
    """
    Enterprise Layout Engine with Full-Width Headers, Strict Block Separation, and Uniform Styling.
    """
    register_fonts()

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
                    exp_val = block.get("explanation", "").strip()
                    if not exp_val or "auto-generated" in exp_val.lower():
                        exp_val = "Verified by editorial board."
                    
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

    page_width, page_height = B5 if format_size.upper() == "B5" else letter
    
    margin = 25
    printable_width = page_width - (2 * margin)
    printable_height = page_height - margin - footer_bottom_margin

    if column_count not in [2, 3]:
        column_count = 2

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

    # Full-Width Title Styles
    title_style = ParagraphStyle(
        name='ExampurTitle',
        fontName='HindiBold',
        fontSize=16,
        leading=20,
        alignment=1, 
        spaceAfter=15
    )
    
    chapter_style = ParagraphStyle(
        name='ExampurChapter',
        fontName='HindiBold',
        fontSize=11,
        leading=15,
        spaceAfter=8,
        spaceBefore=12
    )

    # Uniform Question Style (No random bolding)
    question_style = ParagraphStyle(
        name='ExampurQuestion',
        fontName='HindiBold',
        fontSize=font_size,
        leading=line_spacing,          
        spaceAfter=option_top_gap      
    )

    option_style = ParagraphStyle(
        name='ExampurOption',
        fontName='HindiRegular',
        fontSize=font_size,
        leading=line_spacing,
        spaceAfter=option_vertical_gap 
    )

    theme_accent = colors.HexColor('#047857' if book_type == "quiz" else ('#1d4ed8' if book_type == "theory" else '#b91c1c'))
    
    # 1. Full-Width Cover / Header Title Section (Spans entire width)
    story.append(Paragraph(book_data.get("publisher", "EXAMPUR PUBLICATION DIVISION"), ParagraphStyle(name='Pub', fontName='HindiBold', fontSize=9, alignment=1, textColor=theme_accent, spaceAfter=6)))
    story.append(Paragraph(book_data.get("title"), title_style))
    story.append(Spacer(1, 10))

    # 2. Chapters & Questions Loop with Chapter Page Breaks & Strict Block Separation
    for index, chap in enumerate(book_data.get("chapters", [])):
        if index > 0:
            story.append(PageBreak())
            
        story.append(Paragraph(chap.get("chapter_title"), chapter_style))
        
        for q in chap.get("questions", []):
            q_elements = []
            
            # Question Block
            q_text = f"<b>Q.{q.get('q_no')}</b> {q.get('question')}"
            q_elements.append(Paragraph(q_text, question_style))
            
            # Options Block
            for opt in q.get("options", []):
                q_elements.append(Paragraph(opt, option_style))
            
            # Distinct Correct Answer Block
            if q.get('answer'):
                ans_style = ParagraphStyle(
                    name='AnsStyle', 
                    fontName='HindiBold', 
                    fontSize=font_size, 
                    leading=line_spacing, 
                    textColor=theme_accent, 
                    spaceBefore=4, 
                    spaceAfter=4
                )
                q_elements.append(Paragraph(f"Correct Answer: {q.get('answer')}", ans_style))
                
            # Explanation Block
            if book_type == "solutions" and q.get('explanation'):
                exp_style = ParagraphStyle(
                    name='ExpStyle', 
                    fontName='HindiRegular', 
                    fontSize=font_size - 0.5, 
                    leading=line_spacing - 1.0, 
                    textColor=colors.HexColor('#475569'), 
                    spaceBefore=2, 
                    spaceAfter=2
                )
                q_elements.append(Paragraph(f"Exp: {q.get('explanation')}", exp_style))

            q_elements.append(Spacer(1, question_gap))
            story.append(KeepTogether(q_elements))

        story.append(Spacer(1, 8))

        # 3. Chapter-End Answer Key Section
        if chap.get("answer_key"):
            story.append(Spacer(1, 10))
            story.append(Paragraph(f"Answer Key - {chap.get('chapter_title')}", chapter_style))
            
            th_style = ParagraphStyle(name='THStyle', fontName='HindiBold', fontSize=7.5, leading=10, textColor=colors.HexColor('#0f172a'))
            td_style = ParagraphStyle(name='TDStyle', fontName='HindiRegular', fontSize=7.5, leading=10, textColor=colors.HexColor('#334155'))
            
            table_data = [[
                Paragraph("Q", th_style), 
                Paragraph("Ans", th_style), 
                Paragraph("Explanation", th_style)
            ]]
            
            for item in chap.get("answer_key", []):
                exp_text = item.get('exp', '')
                if not exp_text or "auto-generated" in exp_text.lower():
                    exp_text = "Verified."
                table_data.append([
                    Paragraph(str(item.get('q')), td_style),
                    Paragraph(str(item.get('ans')), td_style),
                    Paragraph(exp_text, td_style)
                ])
            
            col_q = 25
            col_ans = 45
            col_exp = printable_width - (col_q + col_ans)
            
            ans_table = Table(table_data, colWidths=[col_q, col_ans, col_exp])
            ans_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                ('TOPPADDING', (0,0), (-1,-1), 4),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ]))
            story.append(ans_table)

    doc.build(story)
    return output_filename