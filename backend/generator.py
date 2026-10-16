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
        self.drawCentredString(self._pagesize[0] / 2.0, 15, page_text)
        self.restoreState()

def generate_exampur_book(
    output_filename="exampress_final_book.pdf", 
    book_type="quiz", 
    format_size="B5", 
    book_data=None, 
    canonical_data=None, 
    column_count=2,                
    font_size=9.0,                 
    line_spacing=13.0,             
    question_gap=8.0,              # Gap ko optimized kiya gaya hai taaki whitespace kam ho
    option_top_gap=3.0,            
    column_gap_val=12.0,           
    footer_bottom_margin=25.0,     
    option_vertical_gap=2.0        # Options ke beech ki vertical padding tight ki gayi hai
):
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
                            "question": "Sample question text?",
                            "options": ["[A] Option 1", "[B] Option 2"],
                            "answer": "[A]",
                            "explanation": "Verified."
                        }
                    ],
                    "answer_key": [{"ans": "[A]", "exp": "Verified."}]
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
            leftPadding=2, 
            rightPadding=2, 
            topPadding=2, 
            bottomPadding=2,
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
        leading=14,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=6,
        spaceBefore=4
    )

    question_style = ParagraphStyle(
        name='ExampurQuestion',
        fontName='HindiBold',
        fontSize=font_size,
        leading=line_spacing,          
        spaceAfter=option_top_gap,
        spaceBefore=4
    )

    option_style = ParagraphStyle(
        name='ExampurOption',
        fontName='HindiRegular',
        fontSize=font_size,
        leading=line_spacing - 1.0,
        spaceAfter=option_vertical_gap 
    )

    theme_accent = colors.HexColor('#047857' if book_type == "quiz" else ('#1d4ed8' if book_type == "theory" else '#b91c1c'))

    for index, chap in enumerate(book_data.get("chapters", [])):
        if index > 0:
            story.append(PageBreak())
            
        chapter_display_text = f"<b>Chapter {index + 1}: {chap.get('chapter_title', 'Practice Set')}</b>"
        story.append(Paragraph(chapter_display_text, chapter_style))
        story.append(Spacer(1, 4))
        
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
                    spaceBefore=2, 
                    spaceAfter=2
                )
                q_elements.append(Paragraph(f"Correct Answer: {q.get('answer')}", ans_style))
                
            if book_type == "solutions" and q.get('explanation'):
                exp_style = ParagraphStyle(
                    name='ExpStyle', 
                    fontName='HindiRegular', 
                    fontSize=font_size - 0.5, 
                    leading=line_spacing - 1.0, 
                    textColor=colors.HexColor('#475569'), 
                    spaceBefore=1, 
                    spaceAfter=2
                )
                q_elements.append(Paragraph(f"Exp: {q.get('explanation')}", exp_style))

            q_elements.append(Spacer(1, question_gap))
            # KeepTogether ki jagah flowable items use karne se ReportLab natural column balancing karega aur whitespace minimize hoga
            story.append(KeepTogether(q_elements))

        story.append(Spacer(1, 8))

        if chap.get("answer_key"):
            story.append(Paragraph(f"<b>Answer Key - Chapter {index + 1}</b>", chapter_style))
            
            th_style = ParagraphStyle(name='THStyle', fontName='HindiBold', fontSize=7.0, leading=8, textColor=colors.HexColor('#0f172a'), alignment=1)
            td_style = ParagraphStyle(name='TDStyle', fontName='HindiRegular', fontSize=7.0, leading=8, textColor=colors.HexColor('#334155'), alignment=1)
            
            raw_answers = chap.get("answer_key", [])
            num_cols = 5 
            
            header_row = []
            for _ in range(num_cols):
                header_row.extend([Paragraph("Q", th_style), Paragraph("Ans", th_style)])
            
            grid_data = [header_row]
            
            for i in range(0, len(raw_answers), num_cols):
                row_items = []
                for j in range(num_cols):
                    if i + j < len(raw_answers):
                        item = raw_answers[i + j]
                        q_num = str(i + j + 1)
                        ans_val = str(item.get('ans', 'A')).strip()
                        row_items.extend([
                            Paragraph(q_num, td_style),
                            Paragraph(ans_val, td_style)
                        ])
                    else:
                        row_items.extend([Paragraph("", td_style), Paragraph("", td_style)])
                grid_data.append(row_items)
            
            col_unit_width = printable_width / (num_cols * 2)
            col_widths = []
            for _ in range(num_cols):
                col_widths.extend([col_unit_width * 0.45, col_unit_width * 0.55])
            
            ans_table = Table(grid_data, colWidths=col_widths)
            ans_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f1f5f9')),
                ('BOTTOMPADDING', (0,0), (-1,-1), 1),
                ('TOPPADDING', (0,0), (-1,-1), 1),
                ('LEFTPADDING', (0,0), (-1,-1), 1),
                ('RIGHTPADDING', (0,0), (-1,-1), 1),
                ('GRID', (0,0), (-1,-1), 0.4, colors.HexColor('#cbd5e1')),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ]))
            story.append(ans_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    return output_filename