import os
import pandas as pd
from docx import Document
from pydantic import BaseModel
from typing import List, Optional

class QuestionBlock(BaseModel):
    type: str = "question"
    q_no: int
    text: str
    options: List[str]
    answer: str
    explanation: Optional[str] = ""

class Chapter(BaseModel):
    chapter_title: str
    blocks: List[QuestionBlock]

class CanonicalBookSchema(BaseModel):
    title: str
    book_type: str
    format_size: str
    author: Optional[str] = "Exampur Publication"
    chapters: List[Chapter]

def parse_uploaded_file(file_path: str, file_extension: str, book_type: str, format_size: str) -> dict:
    """
    Universal Parser: Ingests raw files (.json, .xlsx, .csv, .docx) 
    and normalizes them into the strict Canonical JSON Schema.
    """
    ext = file_extension.lower()
    
    # 1. JSON Handler
    if ext == ".json":
        import json
        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = json.loadf(f) if hasattr(json, 'loadf') else json.load(f)
        return CanonicalBookSchema(**raw_data).dict()

    # 2. Excel / CSV Handler
    elif ext in [".xlsx", ".xls", ".csv"]:
        df = pd.read_excel(file_path) if ext in [".xlsx", ".xls"] else pd.read_csv(file_path)
        
        blocks = []
        for index, row in df.iterrows():
            # Expecting columns like: q_no, question, opt1, opt2, opt3, opt4, answer, explanation
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
            
            blocks.append(QuestionBlock(
                q_no=q_no, text=text, options=options, answer=answer, explanation=explanation
            ))
            
        chapter = Chapter(chapter_title="Chapter 1: Imported Question Bank", blocks=blocks)
        book = CanonicalBookSchema(
            title="Imported Dataset Book",
            book_type=book_type,
            format_size=format_size,
            chapters=[chapter]
        )
        return book.dict()

    # 3. DOCX Handler
    elif ext == ".docx":
        doc = Document(file_path)
        blocks = []
        q_count = 1
        
        current_question = None
        current_options = []
        
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue
            if text.lower().startswith("q.") or text.lower().startswith("question"):
                if current_question:
                    blocks.append(QuestionBlock(
                        q_no=q_count, text=current_question, 
                        options=current_options if current_options else ["(A) Option 1", "(B) Option 2", "(C) Option 3", "(D) Option 4"],
                        answer="A", explanation=""
                    ))
                    q_count += 1
                current_question = text
                current_options = []
            elif text.startswith("(A)") or text.startswith("(B)") or text.startswith("(C)") or text.startswith("(D)") or text.startswith("A)") or text.startswith("B)"):
                current_options.append(text)
                
        # Append last item
        if current_question:
            blocks.append(QuestionBlock(
                q_no=q_count, text=current_question, 
                options=current_options if current_options else ["(A) Option 1", "(B) Option 2", "(C) Option 3", "(D) Option 4"],
                answer="A", explanation=""
            ))
            
        if not blocks:
            # Fallback if docx structure didn't match q format
            blocks.append(QuestionBlock(
                q_no=1, text="Parsed text document content placeholder.",
                options=["(A) Alpha", "(B) Beta", "(C) Gamma", "(D) Delta"],
                answer="A", explanation="Auto-generated explanation."
            ))
            
        chapter = Chapter(chapter_title="Chapter 1: Word Document Import", blocks=blocks)
        book = CanonicalBookSchema(
            title="Imported Word Document Book",
            book_type=book_type,
            format_size=format_size,
            chapters=[chapter]
        )
        return book.dict()

    else:
        raise ValueError(f"Unsupported file extension: {ext}")