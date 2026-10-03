from fastapi import FastAPI, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from generator import generate_exampur_book

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/generate-book")
async def generate_book(
    book_type: str = Form(...),
    format_size: str = Form(...)
):
    output_pdf = generate_exampur_book(book_type=book_type, format_size=format_size)
    
    with open(output_pdf, "rb") as f:
        pdf_bytes = f.read()
        
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=exampress_v2_book.pdf"})