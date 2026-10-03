from fastapi import FastAPI, Form, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from generator import generate_exampur_book

app = FastAPI(title="Exampress V2 API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return {"status": "Exampress V2 Backend is running smoothly!"}

@app.post("/generate-book")
async def generate_book(
    book_type: str = Form(...),
    format_size: str = Form(...)
):
    output_pdf = None
    try:
        # Call generator engine
        output_pdf = generate_exampur_book(book_type=book_type, format_size=format_size)
        
        if not output_pdf or not os.path.exists(output_pdf):
            raise HTTPException(status_code=500, detail="PDF generation failed to produce output file.")
        
        with open(output_pdf, "rb") as f:
            pdf_bytes = f.read()
            
        # Optional: Clean up the generated file from disk after reading into bytes
        try:
            os.remove(output_pdf)
        except Exception:
            pass
            
        return Response(
            content=pdf_bytes, 
            media_type="application/pdf", 
            headers={"Content-Disposition": "attachment; filename=exampress_v2_book.pdf"}
        )
        
    except Exception as e:
        if output_pdf and os.path.exists(output_pdf):
            try:
                os.remove(output_pdf)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=str(e))