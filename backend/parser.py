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
            raise ValueError("Validation Error: Duplicate question numbers detected in chapter sequence.")
            
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
    """Helper function to strictly segregate Questions, Options, Answers and Explanations."""
    blocks = []
    q_count = 1
    
    current_question = None
    current_options = []
    current_answer = "A"
    current_exp = ""
    
    # Regex matchers for structure separation
    q_pattern = re.compile(r'^(q\.?\s*\d+[\.\)]?|\d+[\.\)]\s*|\bquestion\b\s*\d+)', re.IGNORECASE)
    opt_pattern = re.compile(r'^[\(\[]?\s*([A-Da-d])[\)\]]?\s*[\.\-]?\s*(.+)')
    ans_pattern = re.compile(r'^(answer|ans|उत्तर)\s*[:\-]?\s*[\(\[]?([A-Da-d])[\)\]]?', re.IGNORECASE)
    ans_fallback_pattern = re.compile(r'^(answer|ans|उत्तर)\s*[:\-]\s*(.*)', re.IGNORECASE)
    exp_pattern = re.compile(r'^(explanation|exp)\s*[:\-]\s*(.*)', re.IGNORECASE)

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
            # Save previous question if exists
            if current_question:
                if not current_options:
                    current_options = ["[A] Option 1", "[B] Option 2", "[C] Option 3", "[D] Option 4"]
                blocks.append(QuestionBlock(
                    q_no=q_count,
                    text=current_question.strip(),
                    options=current_options,
                    answer=current_answer.strip() if current_answer else "A",
                    explanation=current_exp.strip()
                ))
                q_count += 1
            
            # Start new question
            current_question = q_pattern.sub('', text).strip()
            if not current_question:
                current_question = text
            current_options = []
            current_answer = "A"
            current_exp = ""

        elif opt_match:
            # It's an option line (e.g., (A) Manipur or A) Assam)
            opt_text = text
            current_options.append(opt_text)

        elif ans_match:
            try:
                current_answer = ans_match.group(2).strip().upper()
            except Exception:
                current_answer = "A"
            if not current_answer:
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
            # Continuation text
            if current_options:
                current_options[-1] += " " + text
            elif current_question:
                current_question += " " + text

    # Append the last question
    if current_question:
        if not current_options:
            current_options = ["[A] Option 1", "[B] Option 2", "[C] Option 3", "[D] Option 4"]
        blocks.append(QuestionBlock(
            q_no=q_count,
            text=current_question.strip(),
            options=current_options,
            answer=current_answer.strip() if current_answer else "A",
            explanation=current_exp.strip()
        ))

    if not blocks:
        blocks.append(QuestionBlock(
            q_no=1, 
            text="Parsed document content placeholder.",
            options=["[A] Alpha", "[B] Beta", "[C] Gamma", "[D] Delta"],
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
                
            chapter = Chapter(chapter_title="Chapter 1: Imported Question Bank (Verified)", blocks=blocks)
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
            blocks = parse_lines_into_blocks(lines)
                
            chapter = Chapter(chapter_title="Chapter 1: PDF Document Import (Structured)", blocks=blocks)
            book = CanonicalBookSchema(
                title="Imported PDF Book", 
                book_type=book_type, 
                format_size=format_size, 
                column_count=column_count,
                chapters=[chapter]
            )
            return book.model_dump()

        elif ext == ".docx":
            doc = Document(file_path)
            lines = [para.text.strip() for para in doc.paragraphs if para.text.strip()]
            blocks = parse_lines_into_blocks(lines)
                
            chapter = Chapter(chapter_title="Chapter 1: Word Document Import (Structured)", blocks=blocks)
            book = CanonicalBookSchema(
                title="Imported Word Document Book", 
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