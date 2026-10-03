from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import os
from generator import generate_exampur_book

app = FastAPI(title="Exampress V2 API")

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
    format_size: str = Form(...),
    file: UploadFile = File(None)
):
    output_pdf = "exampress_final_book.pdf"
    try:
        book_data = None
        if file:
            content = await file.read()
            try:
                book_data = json.loads(content.decode("utf-8"))
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid JSON format.")

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