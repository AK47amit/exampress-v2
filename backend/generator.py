import os
from weasyprint import HTML, CSS

def generate_exampur_book(output_filename="exampress_final_book.pdf", book_type="quiz", format_size="B5", book_data=None, canonical_data=None):
    """
    Enterprise Layout Engine using WeasyPrint for flawless Unicode (Hindi/English) rendering.
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
                        }
                    ]
                }
            ],
            "answer_key": [
                {"q": 1, "ans": "(A)", "exp": "P is sister of R, R is brother of Q -> P is aunt."}
            ]
        }

    # Dimensions for B5 vs A4
    page_css = "@page { size: b5; margin: 20mm; }" if format_size == "B5" else "@page { size: a4; margin: 20mm; }"

    # Build clean HTML content with robust Unicode font family stack
    html_content = f"""
    <!DOCTYPE html>
    <html lang="hi">
    <head>
        <meta charset="UTF-8">
        <style>
            {page_css}
            body {{
                font-family: 'DejaVu Sans', 'Nirmala UI', Arial, sans-serif;
                color: #334155;
                line-height: 1.5;
                font-size: 11pt;
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
                font-size: 24pt;
                color: #1e293b;
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
                font-size: 14pt;
                color: #0f172a;
                font-weight: bold;
                border-bottom: 2px solid #cbd5e1;
                padding-bottom: 5px;
                margin-top: 20px;
                margin-bottom: 12px;
                page-break-before: always;
            }}
            .question {{
                margin-bottom: 10px;
            }}
            .q-text {{
                font-weight: bold;
                color: #1e293b;
            }}
            .options {{
                margin-left: 20px;
                margin-top: 4px;
                margin-bottom: 8px;
            }}
            .option-item {{
                margin-bottom: 3px;
            }}
            .answer-section {{
                page-break-before: always;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
                font-size: 10pt;
            }}
            th, td {{
                border: 1px solid #cbd5e1;
                padding: 8px;
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
                Format: {format_size} Academic Edition &nbsp;|&nbsp; Engine: Exampry V2.0 WeasyPrint
            </div>
        </div>
    """

    # Chapters & Questions
    for chap in book_data.get("chapters", []):
        html_content += f'<div class="chapter-title">{chap.get("chapter_title")}</div>'
        for q in chap.get("questions", []):
            html_content += f"""
            <div class="question">
                <div class="q-text">Q.{q.get('q_no')} {q.get('question')}</div>
                <div class="options">
            """
            for opt in q.get("options", []):
                html_content += f'<div class="option-item">{opt}</div>'
            html_content += """
                </div>
            </div>
            """

    # Answer Key Table
    if book_data.get("answer_key"):
        html_content += """
        <div class="answer-section">
            <div class="chapter-title">Answer Key & Detailed Explanations</div>
            <table>
                <thead>
                    <tr>
                        <th style="width: 40px;">Q.No</th>
                        <th style="width: 50px;">Ans</th>
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

    # Generate PDF using WeasyPrint
    HTML(string=html_content).write_pdf(output_filename)
    return output_filename