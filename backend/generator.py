import os
from weasyprint import HTML, CSS

def generate_exampur_book(output_filename="exampress_final_book.pdf", book_type="quiz", format_size="B5", book_data=None, canonical_data=None, column_count=2):
    """
    Enterprise Layout Engine using WeasyPrint supporting dynamic column counts (2 or 3),
    clean question structures, Specialized Book Type Templates (Section 3.2),
    and Robust Canonical Data Pipeline Integration (Section 3.4).
    """
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
        answer_key_list = []
        for chap in canonical_data.get("chapters", []):
            formatted_questions = []
            for block in chap.get("blocks", []):
                if block.get("type") == "question":
                    q_no = block.get("q_no", 1)
                    formatted_questions.append({
                        "q_no": q_no,
                        "question": block.get("text", ""),
                        "options": block.get("options", []),
                        "answer": block.get("answer", ""),
                        "explanation": block.get("explanation", "")
                    })
                    if block.get("answer"):
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
                            "question": "Which institution is organizing the Critical Minerals Innovation Hackathon 2026?",
                            "options": ["[A] IICT / आईआईसीटी", "[B] JNARDDC, Nagpur", "[C] DRDO / डीआरडीओ", "[D] T-Hub / टी-हब"],
                            "answer": "[B] JNARDDC, Nagpur",
                            "explanation": "Verified by editorial board."
                        }
                    ]
                }
            ],
            "answer_key": [
                {"q": 1, "ans": "[B]", "exp": "JNARDDC, Nagpur"}
            ]
        }

    # Dimensions and running footers/headers for B5 vs A4
    page_size_val = "b5" if format_size.upper() == "B5" else "a4"
    page_css = f"""
        @page {{
            size: {page_size_val};
            margin: 15mm;
            @bottom-right {{
                content: "Page " counter(page) " of " counter(pages);
                font-family: 'Noto Sans Devanagari', 'DejaVu Sans', Arial, sans-serif;
                font-size: 8pt;
                color: #64748b;
            }}
            @bottom-left {{
                content: "Exampur Publication Division — {book_type.upper()} Enterprise Edition";
                font-family: 'Noto Sans Devanagari', 'DejaVu Sans', Arial, sans-serif;
                font-size: 8pt;
                color: #64748b;
            }}
        }}
    """

    # Specialized Template Theme based on book_type (Section 3.2)
    theme_accent = "#047857" if book_type == "quiz" else ("#1d4ed8" if book_type == "theory" else "#b91c1c")
    theme_bg = "#ecfdf5" if book_type == "quiz" else ("#eff6ff" if book_type == "theory" else "#fef2f2")

    # Build clean HTML content with multi-column and specialized styles
    html_content = f"""
    <!DOCTYPE html>
    <html lang="hi">
    <head>
        <meta charset="UTF-8">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400;700&display=swap');
            
            {page_css}
            body {{
                font-family: 'Noto Sans Devanagari', 'DejaVu Sans', Arial, sans-serif;
                color: #1e293b;
                line-height: 1.4;
                font-size: 9pt;
            }}
            .cover {{
                text-align: center;
                page-break-after: always;
                padding-top: 100px;
            }}
            .publisher {{
                font-size: 12pt;
                color: {theme_accent};
                font-weight: bold;
                text-transform: uppercase;
                margin-bottom: 20px;
            }}
            .title {{
                font-size: 22pt;
                color: #0f172a;
                font-weight: bold;
                margin-bottom: 15px;
            }}
            .subtitle {{
                font-size: 11pt;
                color: #64748b;
            }}
            .meta-box {{
                margin-top: 40px;
                background-color: {theme_bg};
                border: 1px solid {theme_accent};
                padding: 12px;
                text-align: center;
                color: {theme_accent};
                font-weight: bold;
                font-size: 10pt;
            }}
            .chapter-title {{
                font-size: 12pt;
                color: #0f172a;
                font-weight: bold;
                border-bottom: 2px solid {theme_accent};
                padding-bottom: 4px;
                margin-top: 15px;
                margin-bottom: 10px;
                page-break-before: always;
            }}
            .questions-container {{
                column-count: {column_count};
                column-gap: 12px;
                column-fill: auto;
                orphans: 3;
                widows: 3;
            }}
            .question-box {{
                break-inside: avoid;
                page-break-inside: avoid;
                margin-bottom: 10px;
                background: #fff;
                border: 1px solid #e2e8f0;
                border-left: 3px solid {theme_accent};
                padding: 6px 8px;
                border-radius: 4px;
            }}
            .q-text {{
                font-weight: bold;
                color: #0f172a;
                margin-bottom: 4px;
            }}
            .options-grid {{
                margin-left: 4px;
                margin-bottom: 4px;
            }}
            .option-row {{
                margin-bottom: 2px;
                color: #334155;
            }}
            .answer-text {{
                font-weight: bold;
                color: {theme_accent};
                margin-top: 2px;
                font-size: 8.5pt;
            }}
            .explanation-box {{
                margin-top: 4px;
                font-size: 8pt;
                color: #475569;
                background: #f8fafc;
                padding: 3px 6px;
                border-radius: 3px;
                border-left: 2px solid #cbd5e1;
            }}
            .answer-section {{
                page-break-before: always;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
                font-size: 9pt;
            }}
            th, td {{
                border: 1px solid #cbd5e1;
                padding: 6px 8px;
                text-align: left;
                vertical-align: top;
            }}
            th {{
                background-color: #f1f5f9;
                color: #0f172a;
            }}
        </style>
    </head>
    <body>

        <div class="cover">
            <div class="publisher">{book_data.get("publisher", "EXAMPUR PUBLICATION DIVISION")}</div>
            <div class="title">{book_data.get('title')}</div>
            <div class="subtitle">Curated & Typeset by {book_data.get('author', 'Exampur Editorial')}</div>
            <div class="meta-box">
                Mode: {book_type.upper()} &nbsp;|&nbsp; Format: {format_size} &nbsp;|&nbsp; Columns: {column_count} &nbsp;|&nbsp; Engine: V2 Enterprise Pipeline
            </div>
        </div>
    """

    # Chapters & Questions Rendering
    for chap in book_data.get("chapters", []):
        html_content += f'<div class="chapter-title">{chap.get("chapter_title")}</div>'
        html_content += '<div class="questions-container">'
        
        for q in chap.get("questions", []):
            html_content += f"""
            <div class="question-box">
                <div class="q-text">Q.{q.get('q_no')} {q.get('question')}</div>
                <div class="options-grid">
            """
            for opt in q.get("options", []):
                html_content += f'<div class="option-row">{opt}</div>'
            html_content += "</div>"
            
            if q.get('answer'):
                html_content += f'<div class="answer-text">Answer: {q.get("answer")}</div>'
            
            if book_type == "solutions" and q.get('explanation'):
                html_content += f'<div class="explanation-box">Exp: {q.get("explanation")}</div>'
            
            html_content += "</div>"
        html_content += '</div>'

    # Answer Key Table Rendering
    if book_data.get("answer_key"):
        html_content += """
        <div class="answer-section">
            <div class="chapter-title">Answer Key & Detailed Explanations</div>
            <table>
                <thead>
                    <tr>
                        <th style="width: 40px;">Q.No</th>
                        <th style="width: 80px;">Ans</th>
                        <th>Detailed Explanation (Editorial Verified)</th>
                    </tr>
                </thead>
                <tbody>
        """
        for item in book_data.get("answer_key", []):
            html_content += f"""
                    <tr>
                        <td>{item.get('q')}</td>
                        <td>{item.get('ans')}</td>
                        <td>{item.get('exp')}</td>
                    </tr>
            """
        html_content += """
                </tbody>
            </table>
        </div>
        """

    html_content += """
    </body>
    </html>
    """

    HTML(string=html_content).write_pdf(output_filename)
    return output_filename