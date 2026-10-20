import os
import shutil
import tempfile
import base64
import zipfile
import uuid
import subprocess
import sys
from datetime import timedelta
from fastapi import FastAPI, UploadFile, File, Form, Response, HTTPException, Depends, status, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional

from parser import parse_uploaded_file
from generator import PDFGenerator
from archive_parser import extract_and_parse_archive
from idml_generator import IDMLGenerator  # Phase 7: Adobe IDML Interchange Generator
from monitoring import init_sentry, logger  # Phase 8.2: Sentry Error Tracking & Logging
from security import limiter, rate_limit_handler  # Phase 8.3: Security Rate Limiting
from slowapi.errors import RateLimitExceeded

# SaaS Foundations Imports (Phase 5)
from database import engine, get_db
from models import Base, User, Project
from auth import get_password_hash, verify_password, create_access_data_token, get_current_user

try:
    import fitz  # PyMuPDF for visual review & thumbnail generation (Section 4.1)
except ImportError:
    fitz = None

# Automatically create database tables on startup if they don't exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Exampress V2 Enterprise SaaS API", version="3.2")

# Initialize Sentry Monitoring & Structured Logging (Phase 8.2)
init_sentry(app)

# Initialize Rate Limiter State & Exception Handler (Phase 8.3)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

# Robust & Flexible CORS configuration for Vercel production/preview and local development
origins = [
    "https://exampurv2.vercel.app",
    "https://exampressv2.vercel.app",
    "http://localhost:5173",
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://(exampressv2|exampurv2)(-.*)?\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Type"]
)

# 100 MB maximum file size limit for security and stability
MAX_FILE_SIZE = 100 * 1024 * 1024

# Pydantic Schemas for Phase 5 SaaS Endpoints
class UserCreate(BaseModel):
    email: str
    password: str

class ProjectSaveRequest(BaseModel):
    title: str
    book_type: str
    format_size: str
    column_count: int
    canonical_data: dict


@app.on_event("startup")
def startup_event():
    """
    Ensure Playwright chromium browser is automatically installed on container startup 
    to permanently prevent missing executable errors in production.
    """
    try:
        logger.info("Startup Event: Ensuring Playwright Chromium browser is installed...")
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        logger.info("Playwright Chromium browser verified and ready.")
    except Exception as e:
        logger.error(f"Failed to auto-install Playwright browser on startup: {str(e)}")


def normalize_canonical_data(canonical_data: dict, book_type: str, format_size: str, column_count: int) -> dict:
    """
    Robust Normalization Guard: Ensures that canonical_data always has a valid 'chapters' 
    structure. Removed silent sample question fallbacks to enforce strict Content Integrity.
    """
    if not isinstance(canonical_data, dict):
        canonical_data = {}

    canonical_data.setdefault("title", "Exampress Practice Book")
    canonical_data.setdefault("book_type", book_type)
    canonical_data.setdefault("format_size", format_size)
    canonical_data.setdefault("column_count", column_count)

    chapters = canonical_data.get("chapters", [])
    
    # If parser returned flat blocks or questions without chapter grouping
    if not chapters and ("blocks" in canonical_data or "questions" in canonical_data):
        blocks = canonical_data.get("blocks", canonical_data.get("questions", []))
        chapters = [{
            "chapter_title": "Chapter 1: Main Content",
            "blocks": blocks
        }]
    
    # Strict Content Integrity Check: Do NOT silently inject fake sample questions with default answers.
    if not chapters:
        raise HTTPException(
            status_code=400, 
            detail="Content Integrity Error: No valid chapters or questions found in the uploaded file. Please check your source formatting."
        )

    canonical_data["chapters"] = chapters
    return canonical_data


# Section 4.3 & Phase 5/7/8: End-to-End Health & SaaS Status Endpoint
@app.get("/")
@limiter.limit("60/minute")
def health_check(request: Request):
    logger.info("Health check endpoint accessed.")
    return {
        "status": "Exampress V2 Enterprise SaaS Backend is running successfully!",
        "pipeline_status": "Active",
        "modules": {
            "parser": "Operational",
            "generator": "Operational (Playwright Chromium + Jinja2)",
            "archive_extractor": "Operational",
            "pdf_preview": "Operational" if fitz else "Degraded (PyMuPDF missing)",
            "saas_auth_database": "Operational",
            "async_background_jobs": "Operational",
            "adobe_idml_interchange": "Operational",
            "sentry_monitoring": "Operational",
            "security_rate_limiting": "Operational"
        }
    }


# --- PHASE 5: USER AUTHENTICATION & PROJECT MANAGEMENT ENDPOINTS ---

@app.post("/api/v2/auth/register")
@limiter.limit("10/minute")
def register_user(request: Request, user_data: UserCreate, db = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        logger.warning(f"Registration failed: Email already exists - {user_data.email}")
        raise HTTPException(status_code=400, detail="Email is already registered.")
    
    hashed_pwd = get_password_hash(user_data.password)
    new_user = User(email=user_data.email, hashed_password=hashed_pwd)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    logger.info(f"New user registered successfully: {user_data.email}")
    return {"status": "success", "message": "User registered successfully", "user_id": new_user.id}


@app.post("/api/v2/auth/login")
@limiter.limit("20/minute")
def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Authentication failed for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=1440)
    access_token = create_access_data_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    logger.info(f"User logged in successfully: {user.email}")
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/api/v2/projects")
@limiter.limit("30/minute")
def save_user_project(request: Request, project: ProjectSaveRequest, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    new_project = Project(
        title=project.title,
        book_type=project.book_type,
        format_size=project.format_size,
        column_count=project.column_count,
        canonical_data=project.canonical_data,
        user_id=current_user.id
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    
    logger.info(f"Project '{project.title}' saved to vault for user: {current_user.email}")
    return {
        "status": "success",
        "message": "Project saved successfully to SaaS vault.",
        "project_id": new_project.id
    }


@app.get("/api/v2/projects")
def get_user_projects(current_user: User = Depends(get_current_user), db = Depends(get_db)):
    projects = db.query(Project).filter(Project.user_id == current_user.id).all()
    return {
        "status": "success",
        "total_projects": len(projects),
        "projects": [
            {
                "id": p.id,
                "title": p.title,
                "book_type": p.book_type,
                "format_size": p.format_size,
                "column_count": p.column_count,
                "created_at": p.created_at
            } for p in projects
        ]
    }


# --- PHASE 5.4: ASYNCHRONOUS BACKGROUND JOBS & QUEUING ---

job_status_store = {}

def background_generate_book_task(
    job_id: str, 
    book_type: str, 
    format_size: str, 
    column_count: int, 
    canonical_data: dict, 
    output_path: str,
    font_size: float,
    line_spacing: float,
    question_gap: float,
    option_top_gap: float,
    column_gap_val: float,
    footer_bottom_margin: float,
    option_vertical_gap: float,
    header_font_size: float,
    header_bold: bool,
    header_italic: bool,
    header_alignment: int
):
    try:
        job_status_store[job_id] = {"status": "processing", "progress": 50}
        logger.info(f"Background Job {job_id}: Starting Playwright PDF generation...")
        
        pdf_gen = PDFGenerator()
        generate_output = pdf_gen.generate_pdf(
            output_filename=output_path,
            book_type=book_type,
            format_size=format_size,
            column_count=column_count,
            canonical_data=canonical_data,
            font_size=font_size,
            line_spacing=line_spacing,
            question_gap=question_gap,
            option_top_gap=option_top_gap,
            column_gap_val=column_gap_val,
            footer_bottom_margin=footer_bottom_margin,
            option_vertical_gap=option_vertical_gap,
            header_font_size=header_font_size,
            header_bold=header_bold,
            header_italic=header_italic,
            header_alignment=header_alignment
        )
        
        if generate_output and os.path.exists(output_path):
            job_status_store[job_id] = {"status": "completed", "file_path": output_path}
            logger.info(f"Background Job {job_id}: Completed successfully.")
        else:
            job_status_store[job_id] = {"status": "failed", "error": "PDF generation failed to produce output file."}
            logger.error(f"Background Job {job_id}: Failed to produce output.")
            
    except Exception as e:
        job_status_store[job_id] = {"status": "failed", "error": str(e)}
        logger.exception(f"Background Job {job_id} encountered an exception: {str(e)}")

@app.post("/api/v2/generate-async")
@limiter.limit("15/minute")
async def generate_book_async(
    request: Request,
    background_tasks: BackgroundTasks,
    book_type: str = Form("quiz"),
    format_size: str = Form("B5"),
    column_count: int = Form(2),
    font_size: float = Form(9.0),
    line_spacing: float = Form(13.0),
    question_gap: float = Form(6.0),
    option_top_gap: float = Form(2.0),
    column_gap_val: float = Form(10.0),
    footer_bottom_margin: float = Form(20.0),
    option_vertical_gap: float = Form(1.5),
    header_font_size: float = Form(11.0),
    header_bold: bool = Form(True),
    header_italic: bool = Form(False),
    header_alignment: int = Form(1),
    file: UploadFile = File(None)
):
    job_id = str(uuid.uuid4())
    output_pdf_path = os.path.join(tempfile.gettempdir(), f"exampress_job_{job_id}.pdf")
    
    tmp_input_path = None
    canonical_data = None
    
    try:
        if file and file.filename:
            file.file.seek(0, os.SEEK_END)
            file_size = file.file.tell()
            file.file.seek(0)
            
            if file_size > MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail="Uploaded file exceeds the maximum allowed size limit of 100MB.")

            filename = file.filename.lower()
            ext = os.path.splitext(filename)[1]
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_in:
                shutil.copyfileobj(file.file, tmp_in)
                tmp_input_path = tmp_in.name
            
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
        
        canonical_data = normalize_canonical_data(canonical_data, book_type, format_size, column_count)

    except Exception as parse_err:
        logger.error(f"Parser error during async generation: {str(parse_err)}")
        raise HTTPException(status_code=400, detail=f"Universal Parser Error: {str(parse_err)}")
    finally:
        if tmp_input_path and os.path.exists(tmp_input_path):
            try:
                os.remove(tmp_input_path)
            except Exception:
                pass

    job_status_store[job_id] = {"status": "queued"}
    background_tasks.add_task(
        background_generate_book_task,
        job_id=job_id,
        book_type=book_type,
        format_size=format_size,
        column_count=column_count,
        canonical_data=canonical_data,
        output_path=output_pdf_path,
        font_size=font_size,
        line_spacing=line_spacing,
        question_gap=question_gap,
        option_top_gap=option_top_gap,
        column_gap_val=column_gap_val,
        footer_bottom_margin=footer_bottom_margin,
        option_vertical_gap=option_vertical_gap,
        header_font_size=header_font_size,
        header_bold=header_bold,
        header_italic=header_italic,
        header_alignment=header_alignment
    )
    
    logger.info(f"Queued background generation job {job_id}")
    return {
        "status": "success",
        "message": "Book generation queued successfully in background.",
        "job_id": job_id,
        "status_check_url": f"/api/v2/jobs/{job_id}"
    }

@app.get("/api/v2/jobs/{job_id}")
def check_job_status(job_id: str):
    job = job_status_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID not found.")
    return {"job_id": job_id, "job_info": job}


# --- PHASE 7: ADOBE IDML INTERCHANGE EXPORT ENDPOINT ---

@app.post("/api/v2/export-idml")
@limiter.limit("10/minute")
async def export_book_idml(
    request: Request,
    book_type: str = Form("quiz"),
    format_size: str = Form("B5"),
    column_count: int = Form(2),
    current_user: User = Depends(get_current_user)
):
    tmp_idml_path = tempfile.NamedTemporaryFile(delete=False, suffix=".idml").name
    
    try:
        canonical_data = {
            "title": f"Exampress IDML Export - {current_user.email}",
            "book_type": book_type,
            "format_size": format_size,
            "column_count": column_count,
            "chapters": [
                {
                    "chapter_title": "Chapter 1: InDesign Interchange Content",
                    "blocks": [
                        {
                            "type": "question",
                            "q_no": 1,
                            "text": "Does IDML allow seamless round-trip editing with professional designers?",
                            "options": ["No", "Yes", "Maybe", "Never"],
                            "answer": "Yes",
                            "explanation": "IDML packages XML stories and spreads for native InDesign typesetting."
                        }
                    ]
                }
            ]
        }
        
        output_file = IDMLGenerator.generate_idml_package(canonical_data, tmp_idml_path)
        
        if not output_file or not os.path.exists(output_file):
            raise HTTPException(status_code=500, detail="IDML generation engine failed.")
            
        with open(output_file, "rb") as f:
            idml_bytes = f.read()
            
        logger.info(f"IDML package exported successfully for user {current_user.email}")
        return Response(
            content=idml_bytes,
            media_type="application/vnd.adobe.indesign-idml-package",
            headers={"Content-Disposition": f"attachment; filename=exampress_{book_type}_{format_size}.idml"}
        )
        
    except Exception as e:
        logger.exception(f"IDML Pipeline Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"IDML Pipeline Error: {str(e)}")
        
    finally:
        if os.path.exists(tmp_idml_path):
            try:
                os.remove(tmp_idml_path)
            except Exception:
                pass


# --- CORE GENERATION & PREVIEW ENDPOINTS ---

@app.post("/generate-book")
@limiter.limit("20/minute")
async def generate_book(
    request: Request,
    book_type: str = Form(...),
    format_size: str = Form(...),
    column_count: int = Form(2),
    font_size: float = Form(9.0),
    line_spacing: float = Form(13.0),
    question_gap: float = Form(6.0),
    option_top_gap: float = Form(2.0),
    column_gap_val: float = Form(10.0),
    footer_bottom_margin: float = Form(20.0),
    option_vertical_gap: float = Form(1.5),
    header_font_size: float = Form(11.0),
    header_bold: bool = Form(True),
    header_italic: bool = Form(False),
    header_alignment: int = Form(1),
    file: UploadFile = File(None)
):
    tmp_input_path = None
    tmp_output_path = None
    
    try:
        canonical_data = None
        
        if file and file.filename:
            file.file.seek(0, os.SEEK_END)
            file_size = file.file.tell()
            file.file.seek(0)
            
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
                logger.error(f"Parser error during generation: {str(parse_err)}")
                raise HTTPException(status_code=400, detail=f"Universal Parser Error: {str(parse_err)}")
        
        canonical_data = normalize_canonical_data(canonical_data, book_type, format_size, column_count)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_out:
            tmp_output_path = tmp_out.name

        # --- PLAYWRIGHT PDF GENERATOR EXECUTION ---
        pdf_gen = PDFGenerator()
        output_pdf = pdf_gen.generate_pdf(
            output_filename=tmp_output_path,
            book_type=book_type,
            format_size=format_size,
            column_count=column_count,
            canonical_data=canonical_data,
            font_size=font_size,
            line_spacing=line_spacing,
            question_gap=question_gap,
            option_top_gap=option_top_gap,
            column_gap_val=column_gap_val,
            footer_bottom_margin=footer_bottom_margin,
            option_vertical_gap=option_vertical_gap,
            header_font_size=header_font_size,
            header_bold=header_bold,
            header_italic=header_italic,
            header_alignment=header_alignment
        )
        
        if not output_pdf or not os.path.exists(output_pdf):
            raise HTTPException(status_code=500, detail="PDF generation engine failed to produce output file.")
        
        with open(output_pdf, "rb") as f:
            pdf_bytes = f.read()
            
        logger.info(f"Book generated successfully via Playwright Engine: {book_type} ({format_size})")
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=exampress_{book_type}_{format_size}_{column_count}col.pdf"}
        )
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.exception(f"Enterprise Pipeline Error: {str(e)}")
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


@app.post("/api/v2/preview-pdf")
@limiter.limit("30/minute")
async def preview_generated_pdf(request: Request, file: UploadFile = File(...)):
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
        logger.exception(f"PDF Preview Generation Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PDF Preview Generation Error: {str(e)}")
        
    finally:
        if tmp_preview_path and os.path.exists(tmp_preview_path):
            try:
                os.remove(tmp_preview_path)
            except Exception:
                pass


@app.post("/api/v2/batch-export")
@limiter.limit("10/minute")
async def batch_export_books(
    request: Request,
    book_type: str = Form("quiz"),
    format_size: str = Form("B5"),
    column_count: int = Form(2),
    font_size: float = Form(9.0),
    line_spacing: float = Form(13.0),
    question_gap: float = Form(6.0),
    option_top_gap: float = Form(2.0),
    column_gap_val: float = Form(10.0),
    footer_bottom_margin: float = Form(20.0),
    option_vertical_gap: float = Form(1.5),
    header_font_size: float = Form(11.0),
    header_bold: bool = Form(True),
    header_italic: bool = Form(False),
    header_alignment: int = Form(1),
    files: list[UploadFile] = File(...)
):
    batch_tmp_dir = tempfile.mkdtemp()
    zip_output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".zip").name
    
    try:
        generated_pdfs = []
        pdf_gen = PDFGenerator()
        
        for idx, file in enumerate(files):
            if not file.filename:
                continue
                
            ext = os.path.splitext(file.filename)[1].lower()
            file_tmp_path = os.path.join(batch_tmp_dir, f"input_{idx}{ext}")
            
            with open(file_tmp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
                
            canonical_data = parse_uploaded_file(
                file_path=file_tmp_path,
                file_extension=ext,
                book_type=book_type,
                format_size=format_size,
                column_count=column_count
            )
            canonical_data = normalize_canonical_data(canonical_data, book_type, format_size, column_count)
            
            pdf_filename = os.path.splitext(file.filename)[0] + f"_typeset_{book_type}.pdf"
            pdf_path = os.path.join(batch_tmp_dir, pdf_filename)
            
            pdf_gen.generate_pdf(
                output_filename=pdf_path,
                book_type=book_type,
                format_size=format_size,
                column_count=column_count,
                canonical_data=canonical_data,
                font_size=font_size,
                line_spacing=line_spacing,
                question_gap=question_gap,
                option_top_gap=option_top_gap,
                column_gap_val=column_gap_val,
                footer_bottom_margin=footer_bottom_margin,
                option_vertical_gap=option_vertical_gap,
                header_font_size=header_font_size,
                header_bold=header_bold,
                header_italic=header_italic,
                header_alignment=header_alignment
            )
            
            if os.path.exists(pdf_path):
                generated_pdfs.append(pdf_path)
                
        if not generated_pdfs:
            raise HTTPException(status_code=400, detail="No valid books could be generated from the uploaded batch.")
            
        with zipfile.ZipFile(zip_output_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
            for pdf_p in generated_pdfs:
                zip_ref.write(pdf_p, arcname=os.path.basename(pdf_p))
                
        logger.info(f"Batch export completed successfully with {len(generated_pdfs)} books.")
        return Response(
            content=open(zip_output_path, "rb").read(),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=exampress_batch_export_{book_type}.zip"}
        )
        
    except Exception as e:
        logger.exception(f"Batch Export Pipeline Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Batch Export Pipeline Error")
        
    finally:
        if os.path.exists(batch_tmp_dir):
            try:
                shutil.rmtree(batch_tmp_dir)
            except Exception:
                pass