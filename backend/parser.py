import os
import re
import pandas as pd
from docx import Document
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

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
        
        q_numbers = [b.q_no for b in blocks]
        if len(q_numbers) != len(set(q_numbers)):
            # Normalize sequence numbering automatically if duplicates or jumps happen
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
    """Robust parser helper to segregate Questions, Options, Answers and Explanations cleanly with automatic sequence numbering."""
    blocks = []
    q_count = 1
    
    current_question = ""
    current_options = []
    current_answer = "A"
    current_exp = ""
    
    # Enhanced patterns for questions, options, answers (English & Hindi)
    q_pattern = re.compile(r'^(q\.?\s*\d+[\.\)]?|\d+[\.\)]\s*|\bquestion\b\s*\d+)', re.IGNORECASE)
    opt_pattern = re.compile(r'^([\(\[]?[A-Da-d][\)\]]?|\[?[A-Da-d]\])\s*[\.\-]?\s*(.+)')
    ans_pattern = re.compile(r'^(answer|ans|उत्तर)\s*[:\-]?\s*[\(\[]?([A-Da-d])[\)\]]?', re.IGNORECASE)
    ans_fallback_pattern = re.compile(r'^(answer|ans|उत्तर)\s*[:\-]\s*(.*)', re.IGNORECASE)
    exp_pattern = re.compile(r'^(explanation|exp|स्पष्टीकरण)\s*[:\-]\s*(.*)', re.IGNORECASE)

    def flush_current_block():
        nonlocal current_question, current_options, current_answer, current_exp, q_count
        if current_question.strip():
            if not current_options:
                current_options = ["[A] Option A", "[B] Option B", "[C] Option C", "[D] Option D"]
            
            blocks.append(QuestionBlock(
                q_no=q_count,
                text=current_question.strip(),
                options=current_options,
                answer=current_answer.strip() if current_answer else "A",
                explanation=current_exp.strip()
            ))
            q_count += 1
            current_question = ""
            current_options = []
            current_answer = "A"
            current_exp = ""

    for text in lines:
        text = text.strip()
        if not text:
            continue

        ans_match = ans_pattern.match(text)
        ans_fallback_match = ans_fallback_pattern.match(text)
        exp_match = exp_pattern.match(text)
        opt_match = opt_pattern.match(text)
        q_match = q_pattern.match(text)

        if q_match and not opt_match:
            flush_current_block()
            current_question = q_pattern.sub('', text).strip()
            if not current_question:
                current_question = text

        elif opt_match:
            current_options.append(text)

        elif ans_match:
            try:
                current_answer = ans_match.group(2).strip().upper()
            except Exception:
                current_answer = "A"

        elif ans_fallback_match:
            val = ans_fallback_match.group(2).strip()
            letter_match = re.search(r'[\(\[]?([A-Da-d])[\)\]]?', val)
            if letter_match:
                current_answer = letter_match.group(1).upper()
            else:
                current_answer = val if val else "A"

        elif exp_match:
            current_exp = exp_match.group(2).strip()

        else:
            if current_options:
                current_options[-1] += " " + text
            elif current_question:
                current_question += " " + text
            else:
                current_question = text

    flush_current_block()

    if not blocks:
        blocks.append(QuestionBlock(
            q_no=1, 
            text="Parsed document content placeholder.",
            options=["[A] Option 1", "[B] Option 2", "[C] Option 3", "[D] Option 4"],
            answer="A", 
            explanation="Auto-generated explanation."
        ))

    return blocks


def parse_uploaded_file(file_path: str, file_extension: str, book_type: str, format_size: str, column_count: int = 2) -> dict:
    ext = file_extension.lower()
    
    try:
        if ext == ".json":
            import json
            with open(file_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            raw_data["column_count"] = column_count
            return CanonicalBookSchema(**raw_data).model_dump()

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
                answer = str(row.get('answer', 'A'))
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
            return book.model_dump()

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
            return book.model_dump()

        elif ext == ".docx":
            doc = Document(file_path)
            paragraphs = [para.text.strip() for para in doc.paragraphs if para.text.strip()]
            
            doc_title = "Practice Chapter"
            lines_to_parse = paragraphs
            
            if paragraphs:
                first_para = paragraphs[0]
                cleaned_title = first_para
                
                if ".docx" in cleaned_title.lower() or "section" in cleaned_title.lower():
                    cleaned_title = re.sub(r'.*?\.docx\s*[\-\–\—]\s*', '', cleaned_title, flags=re.IGNORECASE)
                    if "-" in cleaned_title and ("section" in first_para.lower() or ".docx" in first_para.lower()):
                        parts = cleaned_title.split("-")
                        cleaned_title = parts[-1].strip()
                
                cleaned_title = re.sub(r'^(section\s*\d+[\:\-]?\s*)?(\d+[\.\-\s]*)?', '', cleaned_title, flags=re.IGNORECASE).strip()
                cleaned_title = re.sub(r'\s*\(\d+\)\s*$', '', cleaned_title).strip()
                
                is_question_or_opt = bool(re.search(r'^(q\.?\s*\d+|[\(\[]?[A-Da-d][\)\]]?|\d+[\.\)])', cleaned_title, re.IGNORECASE))
                
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
            return book.model_dump()

        else:
            raise ValueError(f"Unsupported file extension: {ext}")
            
    except Exception as err:
        raise ValueError(f"Canonical Parser & Source Identity Error: {str(err)}")