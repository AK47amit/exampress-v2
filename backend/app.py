import os
import shutil
import tempfile
from fastapi import FastAPI, UploadFile, File, Form, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from parser import parse_uploaded_file
from generator import generate_exampur_book
from archive_parser import extract_and_parse_archive

app = FastAPI(title="Exampress V2 Enterprise API", version="2.5")

# Flexible CORS configuration for Vercel production/preview and local development
origins = [
    "https://exampressv2.vercel.app",
    "https://exampurv2.vercel.app",
    "http://localhost:5173",
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://exampressv2-.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {"status": "Exampress V2 Enterprise Backend is running successfully!"}

@app.post("/generate-book")
async def generate_book(
    book_type: str = Form(...),
    format_size: str = Form(...),
    file: UploadFile = File(None)
):
    tmp_input_path = None
    tmp_output_path = None
    
    try:
        canonical_data = None
        
        if file and file.filename:
            filename = file.filename.lower()
            ext = os.path.splitext(filename)[1]
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_in:
                shutil.copyfileobj(file.file, tmp_in)
                tmp_input_path = tmp_in.name
            
            try:
                if ext in [".zip", ".tar", ".gz"]:
                    canonical_data = extract_and_parse_archive(
                        archive_path=tmp_input_path,
                        book_type=book_type,
                        format_size=format_size
                    )
                else:
                    canonical_data = parse_uploaded_file(
                        file_path=tmp_input_path,
                        file_extension=ext,
                        book_type=book_type,
                        format_size=format_size
                    )
            except Exception as parse_err:
                raise HTTPException(status_code=400, detail=f"Universal Parser Error: {str(parse_err)}")
        else:
            canonical_data = {
                "title": "Exampress Default Practice Book",
                "book_type": book_type,
                "format_size": format_size,
                "author": "Exampur Publication Division",
                "chapters": [
                    {
                        "chapter_title": "Chapter 1: General Awareness & Quantitative Aptitude",
                        "blocks": [
                            {
                                "type": "question",
                                "q_no": 1,
                                "text": "What is the capital city of India?",
                                "options": ["Mumbai", "New Delhi", "Kolkata", "Chennai"],
                                "answer": "New Delhi",
                                "explanation": "New Delhi is the national capital of India."
                            }
                        ]
                    }
                ]
            }

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_out:
            tmp_output_path = tmp_out.name

        output_pdf = generate_exampur_book(
            output_filename=tmp_output_path,
            canonical_data=canonical_data
        )
        
        if not output_pdf or not os.path.exists(output_pdf):
            raise HTTPException(status_code=500, detail="PDF generation engine failed to produce output file.")
        
        with open(output_pdf, "rb") as f:
            pdf_bytes = f.read()
            
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=exampress_{book_type}_{format_size}.pdf"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enterprise Pipeline Error: {str(e)}")
        
    finally:
        if tmp_input_path and os.path.exists(tmp_input_path):
            try:
                os.remove(tmp_input_path)
            except Exception:
                pass
        if tmp_output_path and os.path.exists(tmp_output_path):
            try:
                os.remove(tmp_output_path)
            except Exception:
                pass