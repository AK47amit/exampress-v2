from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import os
import io
import pandas as pd
from docx import Document
from generator import generate_exampur_book

app = FastAPI(title="Exampress V2 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def parse_uploaded_file(file_extension: str, file_bytes: bytes):
    book_data = None
    if file_extension == '.json':
        book_data = json.loads(file_bytes.decode('utf-8'))
    elif file_extension in ['.xlsx', '.xls']:
        df = pd.read_excel(io.BytesIO(file_bytes))
        questions = []
        for idx, row in df.iterrows():
            questions.append({
                "q_no": int(row.get("q_no", idx + 1)),
                "question": str(row.get("question", "")),
                "options": [str(row.get("opt_a", "")), str(row.get("opt_b", "")), str(row.get("opt_c", "")), str(row.get("opt_d", ""))]
            })
        book_data = {
            "title": "Exampur Spreadsheet Edition",
            "publisher": "EXAMPUR PUBLICATION DIVISION",
            "author": "Editorial Board",
            "chapters": [{"chapter_title": "Chapter 1: Uploaded Questions", "questions": questions}],
            "answer_key": []
        }
    elif file_extension == '.csv':
        df = pd.read_csv(io.BytesIO(file_bytes))
        questions = []
        for idx, row in df.iterrows():
            questions.append({
                "q_no": int(row.get("q_no", idx + 1)),
                "question": str(row.get("question", "")),
                "options": [str(row.get("opt_a", "")), str(row.get("opt_b", "")), str(row.get("opt_c", "")), str(row.get("opt_d", ""))]
            })
        book_data = {
            "title": "Exampur CSV Edition",
            "publisher": "EXAMPUR PUBLICATION DIVISION",
            "author": "Editorial Board",
            "chapters": [{"chapter_title": "Chapter 1: Uploaded Questions", "questions": questions}],
            "answer_key": []
        }
    elif file_extension == '.docx':
        doc = Document(io.BytesIO(file_bytes))
        text_content = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        book_data = {
            "title": "Exampur Manuscript Edition",
            "publisher": "EXAMPUR PUBLICATION DIVISION",
            "author": "Editorial Board",
            "chapters": [{"chapter_title": "Manuscript Content", "questions": [{"q_no": 1, "question": text_content, "options": []}]}],
            "answer_key": []
        }
    elif file_extension == '.txt':
        text_content = file_bytes.decode('utf-8')
        book_data = {
            "title": "Exampur Text Edition",
            "publisher": "EXAMPUR PUBLICATION DIVISION",
            "author": "Editorial Board",
            "chapters": [{"chapter_title": "Text Content", "questions": [{"q_no": 1, "question": text_content, "options": []}]}],
            "answer_key": []
        }
    return book_data

@app.post("/generate-book")
async def generate_book(
    book_type: str = Form(...),
    format_size: str = Form(...),
    file: UploadFile = File(None)
):
    output_pdf = "exampress_final_book.pdf"
    try:
        book_data = None
        if file:
            filename = file.filename.lower()
            ext = os.path.splitext(filename)[1]
            content = await file.read()
            try:
                book_data = parse_uploaded_file(ext, content)
            except Exception as parse_err:
                raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(parse_err)}")

        generate_exampur_book(
            output_filename=output_pdf,
            book_type=book_type,
            format_size=format_size,
            book_data=book_data
        )
        
        if os.path.exists(output_pdf):
            return FileResponse(
                output_pdf,
                media_type="application/pdf",
                filename=f"exampress_{book_type}_{format_size}.pdf"
            )
        raise HTTPException(status_code=500, detail="PDF generation failed.")
        
    except Exception as e:
        if os.path.exists(output_pdf):
            try:
                os.remove(output_pdf)
            except:
                pass
        raise HTTPException(status_code=500, detail=str(e))