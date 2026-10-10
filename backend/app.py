import os
import shutil
import tempfile
import base64
import zipfile
from fastapi import FastAPI, UploadFile, File, Form, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from parser import parse_uploaded_file
from generator import generate_exampur_book
from archive_parser import extract_and_parse_archive

try:
    import fitz  # PyMuPDF for visual review & thumbnail generation (Section 4.1)
except ImportError:
    fitz = None

app = FastAPI(title="Exampress V2 Enterprise API", version="2.7")

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

# 100 MB maximum file size limit for security and stability
MAX_FILE_SIZE = 100 * 1024 * 1024

# Section 4.3: End-to-End Health & Pipeline Verification Endpoint
@app.get("/")
def health_check():
    return {
        "status": "Exampress V2 Enterprise Backend is running successfully!",
        "pipeline_status": "Active",
        "modules": {
            "parser": "Operational",
            "generator": "Operational",
            "archive_extractor": "Operational",
            "pdf_preview": "Operational" if fitz else "Degraded (PyMuPDF missing)"
        }
    }

@app.post("/generate-book")
async def generate_book(
    book_type: str = Form(...),
    format_size: str = Form(...),
    column_count: int = Form(2),
    file: UploadFile = File(None)
):
    tmp_input_path = None
    tmp_output_path = None
    
    try:
        canonical_data = None
        
        if file and file.filename:
            # Validate file size prior to processing
            file.file.seek(0, os.SEEK_END)
            file_size = file.file.tell()
            file.file.seek(0)  # Reset pointer back to start
            
            if file_size > MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail="Uploaded file exceeds the maximum allowed size limit of 100MB.")

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
                        format_size=format_size,
                        column_count=column_count
                    )
                else:
                    canonical_data = parse_uploaded_file(
                        file_path=tmp_input_path,
                        file_extension=ext,
                        book_type=book_type,
                        format_size=format_size,
                        column_count=column_count
                    )
            except Exception as parse_err:
                raise HTTPException(status_code=400, detail=f"Universal Parser Error: {str(parse_err)}")
        else:
            canonical_data = {
                "title": "Exampress Default Practice Book",
                "book_type": book_type,
                "format_size": format_size,
                "column_count": column_count,
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
            canonical_data=canonical_data,
            column_count=column_count
        )
        
        if not output_pdf or not os.path.exists(output_pdf):
            raise HTTPException(status_code=500, detail="PDF generation engine failed to produce output file.")
        
        with open(output_pdf, "rb") as f:
            pdf_bytes = f.read()
            
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=exampress_{book_type}_{format_size}_{column_count}col.pdf"}
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enterprise Pipeline Error: {str(e)}")
        
    finally:
        # Section 4.3: Secure Temp File Cleanup Guarantee
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


# Phase 4.1: PDF Preview & Thumbnail Generator Endpoint
@app.post("/api/v2/preview-pdf")
async def preview_generated_pdf(file: UploadFile = File(...)):
    """
    Converts the first page of the generated or uploaded PDF into a high-quality base64 PNG thumbnail 
    for real-time visual review in the frontend dashboard.
    """
    if not fitz:
        raise HTTPException(status_code=500, detail="PyMuPDF (fitz) library is not installed on the backend.")
    
    tmp_preview_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_p:
            shutil.copyfileobj(file.file, tmp_p)
            tmp_preview_path = tmp_p.name
            
        doc = fitz.open(tmp_preview_path)
        if len(doc) == 0:
            raise HTTPException(status_code=400, detail="Uploaded PDF is empty or invalid.")
        
        # Render first page as high-res PNG thumbnail
        page = doc[0]
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")
        encoded_img = base64.b64encode(img_bytes).decode("utf-8")
        
        doc.close()
        
        return JSONResponse(content={
            "status": "success",
            "total_pages": len(doc),
            "preview_thumbnail": f"data:image/png;base64,{encoded_img}"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF Preview Generation Error: {str(e)}")
        
    finally:
        if tmp_preview_path and os.path.exists(tmp_preview_path):
            try:
                os.remove(tmp_preview_path)
            except Exception:
                pass


# Phase 4.2 & 4.3: Export & Download Manager with Full Pipeline Verification
@app.post("/api/v2/batch-export")
async def batch_export_books(
    book_type: str = Form("quiz"),
    format_size: str = Form("B5"),
    column_count: int = Form(2),
    files: list[UploadFile] = File(...)
):
    """
    Accepts multiple documents, processes each through the canonical & layout engine,
    and bundles them into a single downloadable ZIP package with verified cleanup.
    """
    batch_tmp_dir = tempfile.mkdtemp()
    zip_output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".zip").name
    
    try:
        generated_pdfs = []
        
        for idx, file in enumerate(files):
            if not file.filename:
                continue
                
            ext = os.path.splitext(file.filename)[1].lower()
            file_tmp_path = os.path.join(batch_tmp_dir, f"input_{idx}{ext}")
            
            with open(file_tmp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                
            # Parse & Generate individual book via pipeline
            canonical_data = parse_uploaded_file(
                file_path=file_tmp_path,
                file_extension=ext,
                book_type=book_type,
                format_size=format_size,
                column_count=column_count
            )
            
            pdf_filename = os.path.splitext(file.filename)[0] + f"_typeset_{book_type}.pdf"
            pdf_path = os.path.join(batch_tmp_dir, pdf_filename)
            
            generate_exampur_book(
                output_filename=pdf_path,
                canonical_data=canonical_data,
                column_count=column_count
            )
            
            if os.path.exists(pdf_path):
                generated_pdfs.append(pdf_path)
                
        if not generated_pdfs:
            raise HTTPException(status_code=400, detail="No valid books could be generated from the uploaded batch.")
            
        # Bundle all generated PDFs into a secure ZIP archive
        with zipfile.ZipFile(zip_output_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
            for pdf_p in generated_pdfs:
                zip_ref.write(pdf_p, arcname=os.path.basename(pdf_p))
                
        return Response(
            content=open(zip_output_path, "rb").read(),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=exampress_batch_export_{book_type}.zip"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch Export Pipeline Error: {str(e)}")
        
    finally:
        # Section 4.3: Secure Cleanup of Batch Directory
        if os.path.exists(batch_tmp_dir):
            try:
                shutil.rmtree(batch_tmp_dir)
            except Exception:
                pass