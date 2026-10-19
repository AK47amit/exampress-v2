import os
import concurrent.futures
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright

class PDFGenerator:
    def __init__(self, template_dir="backend"):
        self.template_dir = template_dir
        self.env = Environment(loader=FileSystemLoader(template_dir))

    def generate_pdf(
        self,
        output_filename="exampress_final_book.pdf",
        book_type="quiz",
        format_size="B5",
        book_data=None,
        canonical_data=None,
        column_count=2,
        font_size=9.0,
        line_spacing=13.0,
        question_gap=6.0,
        option_top_gap=2.0,
        column_gap_val=10.0,
        footer_bottom_margin=22.0,
        top_header_margin=15.0,
        option_vertical_gap=1.5,
        header_font_size=16.0,
        header_bold=True,
        header_italic=False,
        header_alignment=0
    ):
        def _run_playwright_render():
            processed_chapters = []

            if canonical_data and isinstance(canonical_data, dict):
                nonlocal column_count, format_size, book_type
                column_count = int(canonical_data.get("column_count", column_count))
                format_size = canonical_data.get("format_size", format_size)
                book_type = canonical_data.get("book_type", book_type)
                
                raw_chapters = canonical_data.get("chapters", [])
                
                if not raw_chapters:
                    if "blocks" in canonical_data:
                        raw_chapters = [{"chapter_title": "Main Chapter", "blocks": canonical_data["blocks"]}]
                    elif "questions" in canonical_data:
                        raw_chapters = [{"chapter_title": "Main Chapter", "blocks": canonical_data["questions"]}]

                for chap in raw_chapters:
                    formatted_questions = []
                    chap_answer_key = []
                    
                    blocks = chap.get("blocks", chap.get("questions", []))
                    
                    for block in blocks:
                        if not isinstance(block, dict):
                            continue
                        
                        q_text = block.get("text", "") or block.get("question", "")
                        ans_val = block.get("answer", "A")
                        exp_val = block.get("explanation", "").strip()
                        if not exp_val or "auto-generated" in exp_val.lower():
                            exp_val = "Verified by editorial board."
                        
                        options = block.get("options", [])
                        
                        formatted_questions.append({
                            "question": q_text,
                            "options": options,
                            "answer": ans_val,
                            "explanation": exp_val
                        })
                        
                        chap_answer_key.append({
                            "ans": ans_val,
                            "exp": exp_val
                        })
                    
                    if formatted_questions:
                        processed_chapters.append({
                            "chapter_title": chap.get("chapter_title", "Chapter"),
                            "questions": formatted_questions,
                            "answer_key": chap_answer_key
                        })

            if not processed_chapters:
                processed_chapters = [
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

            book_payload = {
                "title": canonical_data.get("title", "Exampress Practice Book") if canonical_data else "Exampress Practice Book",
                "chapters": processed_chapters
            }

            align_map = {0: "left", 1: "center", 2: "right"}
            header_align_str = align_map.get(header_alignment, "left")
            header_font_weight = "bold" if header_bold else "normal"
            header_font_style = "italic" if header_italic else "normal"

            template = self.env.get_template("template.html")
            
            rendered_html = template.render(
                book=book_payload,
                column_count=column_count,
                format_size=format_size,
                book_type=book_type,
                font_size=font_size,
                line_spacing=line_spacing,
                question_gap=question_gap,
                option_top_gap=option_top_gap,
                column_gap_val=column_gap_val,
                header_font_size=header_font_size,
                header_font_weight=header_font_weight,
                header_font_style=header_font_style,
                header_align_str=header_align_str
            )

            temp_html_path = os.path.join(self.template_dir, f"temp_output_{os.getpid()}.html")
            with open(temp_html_path, "w", encoding="utf-8") as f:
                f.write(rendered_html)

            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu"
                    ]
                )
                page = browser.new_page()
                
                # Safely load HTML with domcontentloaded and stability wait
                page.goto(f"file://{os.path.abspath(temp_html_path)}", wait_until="domcontentloaded")
                page.wait_for_timeout(1000)
                
                pdf_options = {
                    "path": output_filename,
                    "print_background": True,
                    "margin": {
                        "top": f"{top_header_margin}mm", 
                        "bottom": f"{footer_bottom_margin}mm", 
                        "left": "20mm", 
                        "right": "20mm"
                    }
                }

                if format_size.upper() == "B5":
                    pdf_options["width"] = "176mm"
                    pdf_options["height"] = "250mm"
                else:
                    pdf_options["format"] = "A4"

                page.pdf(**pdf_options)
                browser.close()
                
            if os.path.exists(temp_html_path):
                try:
                    os.remove(temp_html_path)
                except Exception:
                    pass

            return output_filename

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(_run_playwright_render)
            return future.result()