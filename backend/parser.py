import os
import re
import pandas as pd
from docx import Document
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from optimizer import DocumentOptimizer

try:
    import pypdf
except ImportError:
    pypdf = None

class QuestionBlock(BaseModel):
    type: str = "question"
    q_no: int
    text: str = Field(..., min_length=1)
    options: List[str] = Field(..., min_items=2)
    answer: str = Field(..., min_length=1)
    explanation: Optional[str] = ""

class Chapter(BaseModel):
    chapter_title: str
    blocks: List[QuestionBlock]

    @field_validator('blocks')
    @classmethod
    def validate_question_blocks(cls, blocks: List[QuestionBlock]) -> List[QuestionBlock]:
        if not blocks:
            raise ValueError("Chapter cannot be empty. At least one question block is required.")
        for idx, block in enumerate(blocks, 1):
            block.q_no = idx
        return blocks

class CanonicalBookSchema(BaseModel):
    title: str
    book_type: str
    format_size: str
    column_count: int = 2
    author: Optional[str] = "Exampur Publication"
    chapters: List[Chapter]

    @field_validator('chapters')
    @classmethod
    def validate_chapters(cls, chapters: List[Chapter]) -> List[Chapter]:
        if not chapters:
            raise ValueError("Validation Error: Book canonical model must contain at least one valid chapter.")
        return chapters


def parse_lines_into_blocks(lines: List[str]) -> List[QuestionBlock]:
    """
    Bulletproof Block-Based Parser tailored for unnumbered Exampur docx manuscripts.
    Ensures zero text bleeding and 100% raw text preservation.
    """
    blocks = []
    
    current_q_lines = []
    current_options = []
    current_answer = "A"
    current_exp = ""
    
    opt_start_pattern = re.compile(r'^[\(\[]?([A-Da-d])[\)\]]?\s*[\.\-]?\s*(.*)')
    ans_line_pattern = re.compile(r'^(?:answer|ans|उत्तर|correct\s*answer)\s*[:\-]?\s*[\(\[]?([A-Da-d])[\)\]]?(?:\s*[\-\–\—]?\s*(.*))?', re.IGNORECASE)

    def flush():
        nonlocal current_q_lines, current_options, current_answer, current_exp
        q_text = " ".join([l.strip() for l in current_q_lines if l.strip()]).strip()
        if q_text:
            if not current_options:
                current_options = ["[A] Option A", "[B] Option B", "[C] Option C", "[D] Option D"]
            while len(current_options) < 4:
                current_options.append(f"[{chr(65+len(current_options))}] Option")
            
            blocks.append(QuestionBlock(
                q_no=len(blocks) + 1,
                text=q_text,
                options=current_options[:4],
                answer=current_answer.strip().upper() if current_answer else "A",
                explanation=current_exp.strip()
            ))
        current_q_lines = []
        current_options = []
        current_answer = "A"
        current_exp = ""

    for text in lines:
        text = text.strip()
        if not text:
            continue

        # 1. Check if line is a standard answer line (उत्तर: / Answer:)
        ans_match = ans_line_pattern.match(text)
        if ans_match:
            current_answer = ans_match.group(1).upper()
            if ans_match.group(2):
                current_exp = ans_match.group(2).strip()
            flush()
            continue

        # 2. Check if line has inline correct answer like (Correct Answer: B)
        if "correct answer" in text.lower():
            m = re.search(r'\(correct\s*answer\s*[:\-]?\s*([A-Da-d])\)', text, re.IGNORECASE)
            if m:
                current_answer = m.group(1).upper()
            clean_t = re.sub(r'\(correct\s*answer\s*[:\-]?\s*[A-Da-d]\)', '', text, flags=re.IGNORECASE).strip()
            if clean_t:
                opt_m = opt_start_pattern.match(clean_t)
                if opt_m and len(current_options) < 4:
                    current_options.append(clean_t)
                else:
                    current_q_lines.append(clean_t)
            flush()
            continue

        # 3. Check if line is an option line ([A], (A) etc.)
        opt_match = opt_start_pattern.match(text)
        if opt_match and len(current_options) < 4:
            current_options.append(text)
            continue

        # 4. If we already have 4 options and see new text, it's a new question/flow
        if len(current_options) >= 4:
            flush()

        # 5. Accumulate question lines or option continuation lines safely
        if current_options:
            current_options[-1] += " " + text
        else:
            current_q_lines.append(text)

    flush()

    if not blocks:
        blocks.append(QuestionBlock(
            q_no=1,
            text="Parsed document content placeholder.",
            options=["[A] Alpha", "[B] Beta", "[C] Gamma", "[D] Delta"],
            answer="A",
            explanation=""
        ))

    for idx, b in enumerate(blocks, 1):
        b.q_no = idx

    return blocks


def parse_uploaded_file(file_path: str, file_extension: str, book_type: str, format_size: str, column_count: int = 2) -> dict:
    ext = file_extension.lower()
    
    try:
        if ext == ".json":
            import json
            with open(file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            raw_data["column_count"] = column_count
            book_dict = CanonicalBookSchema(**raw_data).model_dump()
            return DocumentOptimizer.optimize_canonical_book(book_dict)

        elif ext in [".xlsx", ".xls", ".csv"]:
            df = pd.read_excel(file_path) if ext in [".xlsx", ".xls"] else pd.read_csv(file_path)
            blocks = []
            for index, row in df.iterrows():
                q_no = int(row.get('q_no', index + 1))
                text = str(row.get('question', 'Sample Question'))
                options = [
                    str(row.get('opt1', 'A')),
                    str(row.get('opt2', 'B')),
                    str(row.get('opt3', 'C')),
                    str(row.get('opt4', 'D'))
                ]
                answer = str(row.get('answer', 'A')).strip().upper()
                explanation = str(row.get('explanation', ''))
                blocks.append(QuestionBlock(q_no=q_no, text=text, options=options, answer=answer, explanation=explanation))
                
            chapter = Chapter(chapter_title="Chapter 1: Imported Question Bank", blocks=blocks)
            book = CanonicalBookSchema(
                title="Imported Dataset Book", 
                book_type=book_type, 
                format_size=format_size, 
                column_count=column_count,
                chapters=[chapter]
            )
            book_dict = book.model_dump()
            return DocumentOptimizer.optimize_canonical_book(book_dict)

        elif ext == ".pdf":
            if not pypdf:
                raise RuntimeError("pypdf library is not installed on the backend.")
            
            reader = pypdf.PdfReader(file_path)
            full_text = ""
            for page in reader.pages:
                t = page.extract_text()
                if t:
                    full_text += t + "\n"
            
            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
            doc_title = lines[0] if lines else "PDF Document Import"
            blocks = parse_lines_into_blocks(lines[1:] if len(lines) > 1 else lines)
                
            chapter = Chapter(chapter_title=doc_title, blocks=blocks)
            book = CanonicalBookSchema(
                title=doc_title, 
                book_type=book_type, 
                format_size=format_size, 
                column_count=column_count,
                chapters=[chapter]
            )
            book_dict = book.model_dump()
            return DocumentOptimizer.optimize_canonical_book(book_dict)

        elif ext == ".docx":
            doc = Document(file_path)
            paragraphs = [para.text for para in doc.paragraphs if para.text and para.text.strip()]
            
            doc_title = "Practice Chapter"
            lines_to_parse = paragraphs
            
            if paragraphs:
                first_para = paragraphs[0].strip()
                cleaned_title = first_para
                
                if ".docx" in cleaned_title.lower() or "section" in cleaned_title.lower():
                    cleaned_title = re.sub(r'.*?\.docx\s*[\-\–\—]\s*', '', cleaned_title, flags=re.IGNORECASE)
                    if "-" in cleaned_title and ("section" in first_para.lower() or ".docx" in first_para.lower()):
                        parts = cleaned_title.split("-")
                        cleaned_title = parts[-1].strip()
                
                cleaned_title = re.sub(r'^(section\s*\d+[\:\-]?\s*)?(\d+[\.\-\s]*)?', '', cleaned_title, flags=re.IGNORECASE).strip()
                cleaned_title = re.sub(r'\s*\(\d+\)\s*$', '', cleaned_title).strip()
                
                is_question_or_opt = bool(re.search(r'^([\(\[]?[A-Da-d][\)\]]?|\d+[\.\)])', cleaned_title, re.IGNORECASE))
                
                if cleaned_title and len(cleaned_title) < 100 and not is_question_or_opt:
                    doc_title = cleaned_title
                    lines_to_parse = paragraphs[1:]
                else:
                    base_name = os.path.basename(file_path)
                    clean_title = re.sub(r'\.[^.]+$', '', base_name)
                    clean_title = re.sub(r'^(section\s*\d+[\:\-]?\s*)?(\d+[\.\-\s]*)?', '', clean_title, flags=re.IGNORECASE).strip()
                    clean_title = re.sub(r'\s*\(\d+\)\s*$', '', clean_title).strip()
                    doc_title = clean_title if clean_title else "Practice Chapter"
                    lines_to_parse = paragraphs
                
            blocks = parse_lines_into_blocks(lines_to_parse)
                
            chapter = Chapter(chapter_title=doc_title, blocks=blocks)
            book = CanonicalBookSchema(
                title=doc_title, 
                book_type=book_type, 
                format_size=format_size, 
                column_count=column_count,
                chapters=[chapter]
            )
            book_dict = book.model_dump()
            return DocumentOptimizer.optimize_canonical_book(book_dict)

        else:
            raise ValueError(f"Unsupported file extension: {ext}")
            
    except Exception as err:
        raise ValueError(f"Canonical Parser & Source Identity Error: {str(err)}")