import os
from pathlib import Path
import concurrent.futures
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright
from fastapi import HTTPException

class PDFGenerator:
    def __init__(self, template_dir=None):
        # Fix 1: Robust absolute template path resolution to prevent directory mismatch
        if template_dir is None:
            self.template_dir = Path(__file__).resolve().parent
        else:
            self.template_dir = Path(template_dir).resolve()
        
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=True  # Fix for security: enable autoescape as per report guidelines
        )

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
                        
                        # Content Integrity: Strictly use actual parsed values, no fake fallbacks
                        ans_val = block.get("answer", "") 
                        exp_val = block.get("explanation", "").strip()
                        
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

            # Strict Content Integrity Check: Do NOT silently inject fake sample books.
            if not processed_chapters:
                raise HTTPException(
                    status_code=400,
                    detail="Content Integrity Error: Generator received empty or invalid chapters payload. PDF rendering aborted."
                )

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

            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--hide-scrollbars",
                        "--disable-breakpad"
                    ]
                )
                page = browser.new_page()
                
                page.set_content(rendered_html, wait_until="domcontentloaded")
                page.wait_for_timeout(1500)
                
                pdf_args = {
                    "print_background": True,
                    "margin": {
                        "top": f"{top_header_margin}mm", 
                        "bottom": f"{footer_bottom_margin}mm", 
                        "left": "20mm", 
                        "right": "20mm"
                    }
                }

                # Fix 2: Explicit dimensions for B5 to prevent 'Unknown paper format: B5' error
                if format_size.upper() == "B5":
                    pdf_args["width"] = "176mm"
                    pdf_args["height"] = "250mm"
                else:
                    pdf_args["format"] = "A4"

                pdf_bytes = page.pdf(**pdf_args)
                browser.close()

            abs_output_path = os.path.abspath(output_filename)
            with open(abs_output_path, "wb") as f:
                f.write(pdf_bytes)

            return output_filename

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(_run_playwright_render)
            return future.result()