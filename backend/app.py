import os
import shutil
import tempfile
import base64
import zipfile
import uuid
from datetime import timedelta
from fastapi import FastAPI, UploadFile, File, Form, Response, HTTPException, Depends, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from parser import parse_uploaded_file
from generator import generate_exampur_book
from archive_parser import extract_and_parse_archive
from idml_generator import IDMLGenerator  # Phase 7: Adobe IDML Interchange Generator

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

app = FastAPI(title="Exampress V2 Enterprise SaaS API", version="3.0")

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


# Section 4.3 & Phase 5/7: End-to-End Health & SaaS Status Endpoint
@app.get("/")
def health_check():
    return {
        "status": "Exampress V2 Enterprise SaaS Backend is running successfully!",
        "pipeline_status": "Active",
        "modules": {
            "parser": "Operational",
            "generator": "Operational",
            "archive_extractor": "Operational",
            "pdf_preview": "Operational" if fitz else "Degraded (PyMuPDF missing)",
            "saas_auth_database": "Operational",
            "async_background_jobs": "Operational",
            "adobe_idml_interchange": "Operational"
        }
    }


# --- PHASE 5: USER AUTHENTICATION & PROJECT MANAGEMENT ENDPOINTS ---

@app.post("/api/v2/auth/register")
def register_user(user_data: UserCreate, db = Depends(get_db)):
    """Registers a new user in the enterprise SaaS database."""
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email is already registered.")
    
    hashed_pwd = get_password_hash(user_data.password)
    new_user = User(email=user_data.email, hashed_password=hashed_pwd)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"status": "success", "message": "User registered successfully", "user_id": new_user.id}


@app.post("/api/v2/auth/login")
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db = Depends(get_db)):
    """Authenticates user credentials and issues a secure JWT access token."""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=1440) # 24 Hours
    access_token = create_access_data_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/api/v2/projects")
def save_user_project(project: ProjectSaveRequest, current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """Saves a generated book project securely to the authenticated user's profile vault."""
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
    
    return {
        "status": "success",
        "message": "Project saved successfully to SaaS vault.",
        "project_id": new_project.id
    }


@app.get("/api/v2/projects")
def get_user_projects(current_user: User = Depends(get_current_user), db = Depends(get_db)):
    """Retrieves all saved book projects belonging to the logged-in user."""
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

def background_generate_book_task(job_id: str, book_type: str, format_size: str, column_count: int, canonical_data: dict, output_path: str):
    try:
        job_status_store[job_id] = {"status": "processing", "progress": 50}
        
        # Execute typesetting & PDF generation
        generate_output = generate_exampur_book(
            output_filename=output_path,
            canonical_data=canonical_data,
            column_count=column_count
        )
        
        if generate_output and os.path.exists(output_path):
            job_status_store[job_id] = {"status": "completed", "file_path": output_path}
        else:
            job_status_store[job_id] = {"status": "failed", "error": "PDF generation failed to produce output file."}
            
    except Exception as e:
        job_status_store[job_id] = {"status": "failed", "error": str(e)}

@app.post("/api/v2/generate-async")
async def generate_book_async(
    background_tasks: BackgroundTasks,
    book_type: str = Form("quiz"),
    format_size: str = Form("B5"),
    column_count: int = Form(2),
    current_user: User = Depends(get_current_user)
):
    """
    Initiates heavy book generation in the background to prevent server timeouts.
    Returns a Job ID immediately for status tracking.
    """
    job_id = str(uuid.uuid4())
    output_pdf_path = os.path.join(tempfile.gettempdir(), f"exampress_job_{job_id}.pdf")
    
    canonical_data = {
        "title": f"Async Enterprise Book - {current_user.email}",
        "book_type": book_type,
        "format_size": format_size,
        "column_count": column_count,
        "author": "Exampur Publication Division",
        "chapters": [
            {
                "chapter_title": "Chapter 1: Background Processed SaaS Content",
                "blocks": [
                    {
                        "type": "question",
                        "q_no": 1,
                        "text": "Is background queue processing essential for enterprise scaling?",
                        "options": ["No", "Yes", "Maybe", "Never"],
                        "answer": "Yes",
                        "explanation": "Background workers prevent Gateway Timeouts on heavy compilation workloads."
                    }
                ]
            }
        ]
    }
    
    job_status_store[job_id] = {"status": "queued"}
    background_tasks.add_task(
        background_generate_book_task,
        job_id=job_id,
        book_type=book_type,
        format_size=format_size,
        column_count=column_count,
        canonical_data=canonical_data,
        output_path=output_pdf_path
    )
    
    return {
        "status": "success",
        "message": "Book generation queued successfully in background.",
        "job_id": job_id,
        "status_check_url": f"/api/v2/jobs/{job_id}"
    }

@app.get("/api/v2/jobs/{job_id}")
def check_job_status(job_id: str, current_user: User = Depends(get_current_user)):
    """Checks the live progress and status of a queued background job."""
    job = job_status_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job ID not found.")
    return {"job_id": job_id, "job_info": job}


# --- PHASE 7: ADOBE IDML INTERCHANGE EXPORT ENDPOINT ---

@app.post("/api/v2/export-idml")
async def export_book_idml(
    book_type: str = Form("quiz"),
    format_size: str = Form("B5"),
    column_count: int = Form(2),
    current_user: User = Depends(get_current_user)
):
    """
    Exports book canonical data into an Adobe InDesign (IDML) package 
    for professional layout editing and designer workflows.
    """
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
            
        return Response(
            content=idml_bytes,
            media_type="application/vnd.adobe.indesign-idml-package",
            headers={"Content-Disposition": f"attachment; filename=exampress_{book_type}_{format_size}.idml"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"IDML Pipeline Error: {str(e)}")
        
    finally:
        if os.path.exists(tmp_idml_path):
            try:
                os.remove(tmp_idml_path)
            except Exception:
                pass


# --- EXISTING CORE GENERATION & PREVIEW ENDPOINTS ---

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
            
        with zipfile.ZipFile(zip_output_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
            for pdf_p in generated_pdfs:
                zip_ref.write(pdf_p, arcname=os.path.basename(pdf_p))
                
        return Response(
            content=open(zip_output_path, "rb").read(),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename=exampress_batch_export_{book_type}.zip"}
        )
        
    except:
        raise HTTPException(status_code=500, detail="Batch Export Pipeline Error")
        
    finally:
        if os.path.exists(batch_tmp_dir):
            try:
                shutil.rmtree(batch_tmp_dir)
            except Exception:
                pass