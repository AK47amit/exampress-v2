import os
from weasyprint import HTML, CSS

def generate_exampur_book(output_filename="exampress_final_book.pdf", book_type="quiz", format_size="B5", book_data=None, canonical_data=None, column_count=2):
    """
    Enterprise Layout Engine using WeasyPrint supporting dynamic column counts (2 or 3) and clean question structure.
    """
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
        format_size = canonical_data.get("format_size", format_size)
        column_count = int(canonical_data.get("column_count", column_count))

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

    # Dimensions for B5 vs A4
    page_css = "@page { size: b5; margin: 15mm; }" if format_size == "B5" else "@page { size: a4; margin: 15mm; }"

    # Build clean HTML content with dynamic column count support
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
                color: #475569;
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
                background-color: #ecfdf5;
                border: 1px solid #6ee7b7;
                padding: 12px;
                text-align: center;
                color: #047857;
                font-weight: bold;
                font-size: 10pt;
            }}
            .chapter-title {{
                font-size: 12pt;
                color: #0f172a;
                font-weight: bold;
                border-bottom: 2px solid #cbd5e1;
                padding-bottom: 4px;
                margin-top: 15px;
                margin-bottom: 10px;
                page-break-before: always;
            }}
            .questions-container {{
                column-count: {column_count};
                column-gap: 12px;
                column-fill: auto;
            }}
            .question-box {{
                break-inside: avoid;
                page-break-inside: avoid;
                margin-bottom: 10px;
            }}
            .q-text {{
                font-weight: bold;
                color: #0f172a;
                margin-bottom: 3px;
            }}
            .options-grid {{
                margin-left: 8px;
                margin-bottom: 4px;
            }}
            .option-row {{
                margin-bottom: 2px;
                color: #334155;
            }}
            .answer-text {{
                font-weight: bold;
                color: #047857;
                margin-top: 2px;
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
                Format: {format_size} Academic Edition &nbsp;|&nbsp; Columns: {column_count} &nbsp;|&nbsp; Engine: Exampry V2
            </div>
        </div>
    """

    # Chapters & Questions
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
            
            html_content += "</div>"
        html_content += '</div>'

    # Answer Key Table
    if book_data.get("answer_key"):
        html_content += """
        <div class="answer-section">
            <div class="chapter-title">Answer Key & Detailed Explanations</div>
            <table>
                <thead>
                    <tr>
                        <th style="width: 40px;">Q.No</th>
                        <th style="width: 60px;">Ans</th>
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