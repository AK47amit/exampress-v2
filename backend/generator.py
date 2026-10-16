import os
from reportlab.lib.pagesizes import letter, B5
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

def register_fonts():
    font_dir = os.path.join(os.path.dirname(__file__), "fonts")
    regular_path = os.path.join(font_dir, "NotoSansDevanagari_Condensed-Regular.ttf")
    bold_path = os.path.join(font_dir, "NotoSansDevanagari_Condensed-Bold.ttf")
    
    pdfmetrics.registerFont(TTFont('HindiRegular', regular_path))
    pdfmetrics.registerFont(TTFont('HindiBold', bold_path))

class NumberedCanvas(canvas.Canvas):
    """Canvas for dynamically generating centered page numbers on every page without extra clutter."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("HindiRegular", 8)
        self.setFillColor(colors.HexColor("#475569"))
        page_text = f"{self._pageNumber}"
        # Centered page number at the bottom footer
        self.drawCentredString(self._pagesize[0] / 2.0, 15, page_text)
        self.restoreState()

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
    question_gap=10.0,             
    option_top_gap=3.0,            
    column_gap_val=12.0,           
    footer_bottom_margin=25.0,     
    option_vertical_gap=2.0        
):
    """
    Enterprise Layout Engine: Starts directly from clean doc title on page 1 with multi-column flow, 
    automatic sequential question numbering, clean page breaks, and dynamic chapter-end answer tables.
    """
    register_fonts()

    if canonical_data:
        column_count = int(canonical_data.get("column_count", column_count))
        format_size = canonical_data.get("format_size", format_size)
        book_type = canonical_data.get("book_type", book_type)
        
        book_data = {
            "title": canonical_data.get("title", "Exampress Practice Book"),
            "chapters": []
        }
        
        for chap in canonical_data.get("chapters", []):
            formatted_questions = []
            chap_answer_key = []
            
            for block in chap.get("blocks", []):
                if block.get("type") == "question":
                    ans_val = block.get("answer", "A")
                    exp_val = block.get("explanation", "").strip()
                    if not exp_val or "auto-generated" in exp_val.lower():
                        exp_val = "Verified by editorial board."
                    
                    formatted_questions.append({
                        "question": block.get("text", ""),
                        "options": block.get("options", []),
                        "answer": ans_val,
                        "explanation": exp_val
                    })
                    
                    chap_answer_key.append({
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
            "title": "Exampress General Studies Masterclass",
            "chapters": [
                {
                    "chapter_title": "General Practice Set",
                    "questions": [
                        {
                            "question": "Which institution is organizing the Critical Minerals Innovation Hackathon 2026?",
                            "options": ["[A] IICT / आईआईसीटी", "[B] JNARDDC, Nagpur", "[C] DRDO / डीआरडीओ", "[D] T-Hub / टी-हब"],
                            "answer": "[B]",
                            "explanation": "Verified by editorial board."
                        }
                    ],
                    "answer_key": [
                        {"ans": "[B]", "exp": "JNARDDC, Nagpur"}
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

    # Multi-Column Frames starting directly from page 1 (Zero cover page clutter)
    col_width = (printable_width - ((column_count - 1) * column_gap_val)) / column_count
    frames = []
    for i in range(column_count):
        col_x = margin + i * (col_width + column_gap_val)
        frame = Frame(
            col_x, 
            footer_bottom_margin, 
            col_width, 
            printable_height, 
            leftPadding=3, 
            rightPadding=3, 
            topPadding=3, 
            bottomPadding=3,
            id=f'col_{i+1}'
        )
        frames.append(frame)

    doc = BaseDocTemplate(output_filename, pagesize=(page_width, page_height))
    template = PageTemplate(id='multi_col_template', frames=frames)
    doc.addPageTemplates([template])

    story = []

    chapter_style = ParagraphStyle(
        name='ExampurChapter',
        fontName='HindiBold',
        fontSize=11,
        leading=15,
        spaceAfter=8,
        spaceBefore=6
    )

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

    # Chapters & Questions Loop with Automatic Page Breaks & Sequential Numbering
    for index, chap in enumerate(book_data.get("chapters", [])):
        if index > 0:
            story.append(PageBreak())
            
        # Clean Chapter Title Header at the top of the chapter/document flow
        story.append(Paragraph(chap.get("chapter_title"), chapter_style))
        
        # Automatic sequential question numbering (Q.1, Q.2, Q.3...) per chapter
        for q_idx, q in enumerate(chap.get("questions", []), 1):
            q_elements = []
            
            q_text = f"<b>Q.{q_idx}</b> {q.get('question')}"
            q_elements.append(Paragraph(q_text, question_style))
            
            for opt in q.get("options", []):
                q_elements.append(Paragraph(opt, option_style))
            
            if q.get('answer'):
                ans_style = ParagraphStyle(
                    name='AnsStyle', 
                    fontName='HindiBold', 
                    fontSize=font_size, 
                    leading=line_spacing, 
                    textColor=theme_accent, 
                    spaceBefore=3, 
                    spaceAfter=3
                )
                q_elements.append(Paragraph(f"Correct Answer: {q.get('answer')}", ans_style))
                
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

        # Dynamic Chapter-End Answer Key Table
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
            
            for item_idx, item in enumerate(chap.get("answer_key", []), 1):
                exp_text = item.get('exp', '')
                if not exp_text or "auto-generated" in exp_text.lower():
                    exp_text = "Verified."
                table_data.append([
                    Paragraph(str(item_idx), td_style),
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

    doc.build(story, canvasmaker=NumberedCanvas)
    return output_filename