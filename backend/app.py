import os
import re
import shutil
import tempfile
import base64
import zipfile
import uuid
import math
from datetime import timedelta
from pathlib import Path
from threading import Lock

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    Response,
    HTTPException,
    Depends,
    status,
    BackgroundTasks,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

from parser import parse_uploaded_file
from generator import PDFGenerator
from archive_parser import extract_and_parse_archive
from idml_generator import IDMLGenerator
from monitoring import init_sentry, logger
from security import limiter, rate_limit_handler
from slowapi.errors import RateLimitExceeded

from database import engine, get_db
from models import Base, User, Project
from auth import (
    get_password_hash,
    verify_password,
    create_access_data_token,
    get_current_user,
)

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

MAX_FILE_SIZE = 100 * 1024 * 1024       # 100 MB per file
MAX_BATCH_FILES = 20
MAX_BATCH_TOTAL_SIZE = 250 * 1024 * 1024  # 250 MB total
ALLOWED_COLUMN_COUNTS = {1, 2, 3, 4}
ALLOWED_BOOK_TYPES = {"quiz", "mock", "practice", "study", "booklet"}

# In-memory job state is suitable only for a single-process,
# temporary workflow. Use a persistent queue/database for production.
job_status_store = {}
job_status_lock = Lock()


# ---------------------------------------------------------
# DATABASE AND APPLICATION
# ---------------------------------------------------------

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Exampress V2 Enterprise SaaS API",
    version="3.3",
)

init_sentry(app)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

origins = [
    "https://exampurv2.vercel.app",
    "https://exampressv2.vercel.app",
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://(exampressv2|exampurv2)(-.*)?\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Type"],
)


# ---------------------------------------------------------
# REQUEST SCHEMAS
# ---------------------------------------------------------

class UserCreate(BaseModel):
    email: str
    password: str


class ProjectSaveRequest(BaseModel):
    title: str
    book_type: str
    format_size: str
    column_count: int = Field(default=2, ge=1, le=4)
    canonical_data: dict


# ---------------------------------------------------------
# VALIDATION AND FILE HELPERS
# ---------------------------------------------------------

def validate_layout_settings(
    book_type: str,
    format_size: str,
    column_count: int,
    **numeric_settings,
):
    """Validate layout settings without modifying Hindi text."""

    if not isinstance(book_type, str) or not book_type.strip():
        raise HTTPException(status_code=400, detail="book_type is required.")

    if not isinstance(format_size, str) or not format_size.strip():
        raise HTTPException(status_code=400, detail="format_size is required.")

    if column_count not in ALLOWED_COLUMN_COUNTS:
        raise HTTPException(
            status_code=400,
            detail="column_count must be 1, 2, 3, or 4.",
        )

    for name, value in numeric_settings.items():
        if not math.isfinite(value):
            raise HTTPException(
                status_code=400,
                detail=f"{name} must be a finite number.",
            )

    # Broad limits prevent obviously invalid layout values.
    limits = {
        "font_size": (1, 100),
        "line_spacing": (1, 200),
        "question_gap": (0, 200),
        "option_top_gap": (0, 200),
        "column_gap_val": (0, 200),
        "footer_bottom_margin": (0, 300),
        "option_vertical_gap": (0, 200),
        "header_font_size": (1, 100),
        "header_alignment": (0, 2),
    }

    for name, bounds in limits.items():
        if name in numeric_settings:
            low, high = bounds
            value = numeric_settings[name]
            if value < low or value > high:
                raise HTTPException(
                    status_code=400,
                    detail=f"{name} must be between {low} and {high}.",
                )


def get_upload_extension(filename: str) -> str:
    """Preserve compound archive extensions such as .tar.gz."""

    name = (filename or "").lower()

    if name.endswith(".tar.gz"):
        return ".tar.gz"

    return os.path.splitext(name)[1]


def is_archive_extension(extension: str) -> bool:
    return extension.lower() in {".zip", ".tar", ".gz", ".tar.gz"}


def safe_output_basename(filename: str) -> str:
    """Prevent uploaded filenames from creating unsafe output paths."""

    base = os.path.basename(filename or "book")
    base = os.path.splitext(base)[0]
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")

    return (base or "book")[:100]


def save_upload_to_temp(upload: UploadFile, suffix: str) -> tuple[str, int]:
    """Copy an upload to a temporary file and enforce the per-file limit."""

    tmp_path = None

    try:
        upload.file.seek(0, os.SEEK_END)
        file_size = upload.file.tell()
        upload.file.seek(0)

        if file_size <= 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail="Uploaded file exceeds the 100 MB size limit.",
            )

        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            suffix=suffix,
        ) as tmp_file:
            tmp_path = tmp_file.name
            shutil.copyfileobj(upload.file, tmp_file)

        return tmp_path, file_size

    except Exception:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise


def parse_input_file(
    file_path: str,
    filename: str,
    book_type: str,
    format_size: str,
    column_count: int,
) -> dict:
    """Choose archive parsing or normal document parsing."""

    extension = get_upload_extension(filename)

    if is_archive_extension(extension):
        result = extract_and_parse_archive(
            archive_path=file_path,
            book_type=book_type,
            format_size=format_size,
            column_count=column_count,
        )
    else:
        result = parse_uploaded_file(
            file_path=file_path,
            file_extension=extension,
            book_type=book_type,
            format_size=format_size,
            column_count=column_count,
        )

    return normalize_canonical_data(
        result,
        book_type,
        format_size,
        column_count,
    )


def normalize_canonical_data(
    canonical_data: dict,
    book_type: str,
    format_size: str,
    column_count: int,
) -> dict:
    """
    Validate the parser output and keep layout metadata consistent.

    Does not reorder, reverse, or manually rewrite Devanagari characters.
    """

    if not isinstance(canonical_data, dict):
        raise HTTPException(
            status_code=400,
            detail="Parser did not return a valid book object.",
        )

    canonical_data = dict(canonical_data)

    chapters = canonical_data.get("chapters", [])

    # Support parsers that return flat blocks instead of chapters.
    if not chapters and (
        "blocks" in canonical_data or "questions" in canonical_data
    ):
        blocks = canonical_data.get(
            "blocks",
            canonical_data.get("questions", []),
        )

        if isinstance(blocks, list) and blocks:
            chapters = [{
                "chapter_title": "Chapter 1: Main Content",
                "blocks": blocks,
            }]

    if not isinstance(chapters, list) or not chapters:
        raise HTTPException(
            status_code=400,
            detail=(
                "Content Integrity Error: No valid chapters or questions "
                "were found in the uploaded file."
            ),
        )

    valid_chapters = []
    has_content = False

    for index, chapter in enumerate(chapters, start=1):
        if not isinstance(chapter, dict):
            raise HTTPException(
                status_code=400,
                detail=f"Chapter {index} has an invalid structure.",
            )

        blocks = chapter.get("blocks", [])

        if not isinstance(blocks, list):
            raise HTTPException(
                status_code=400,
                detail=f"Chapter {index} blocks must be a list.",
            )

        # Preserve chapter-level text and block fields.
        cleaned_chapter = dict(chapter)
        cleaned_chapter.setdefault("chapter_title", f"Chapter {index}")
        cleaned_chapter["blocks"] = blocks

        if blocks:
            has_content = True

        valid_chapters.append(cleaned_chapter)

    if not has_content:
        raise HTTPException(
            status_code=400,
            detail="No content blocks were found in the uploaded book.",
        )

    canonical_data["chapters"] = valid_chapters

    # The selected request settings are authoritative.
    canonical_data["book_type"] = book_type
    canonical_data["format_size"] = format_size
    canonical_data["column_count"] = column_count
    canonical_data.setdefault("title", "Exampress Practice Book")

    return canonical_data


def generate_pdf_to_path(
    output_path: str,
    book_type: str,
    format_size: str,
    column_count: int,
    canonical_data: dict,
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
    header_alignment: int,
) -> str:
    """Single ReportLab invocation shared by sync and async routes."""

    pdf_gen = PDFGenerator()

    result_path = pdf_gen.generate_pdf(
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
        header_alignment=header_alignment,
    )

    # Some generators return None after writing to the supplied path.
    final_path = result_path or output_path

    if not os.path.isfile(final_path) or os.path.getsize(final_path) == 0:
        raise RuntimeError("PDF generator did not produce a valid output file.")

    return final_path


# ---------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------

@app.get("/")
@limiter.limit("60/minute")
def health_check(request: Request):
    return {
        "status": "Exampress V2 Enterprise SaaS Backend is running successfully!",
        "pipeline_status": "Active",
        "modules": {
            "parser": "Configured",
            "generator": "ReportLab configured; generation requires runtime testing",
            "archive_extractor": "Configured",
            "pdf_preview": "Operational" if fitz else "Degraded (PyMuPDF missing)",
            "saas_auth_database": "Configured",
            "async_background_jobs": "In-memory; single-process limitation",
            "adobe_idml_interchange": "Configured",
            "sentry_monitoring": "Configured",
            "security_rate_limiting": "Configured",
        },
    }


# ---------------------------------------------------------
# AUTHENTICATION
# ---------------------------------------------------------

@app.post("/api/v2/auth/register")
@limiter.limit("10/minute")
def register_user(
    request: Request,
    user_data: UserCreate,
    db=Depends(get_db),
):
    existing_user = db.query(User).filter(
        User.email == user_data.email
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email is already registered.",
        )

    new_user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info("New user registered successfully.")
    return {
        "status": "success",
        "message": "User registered successfully",
        "user_id": new_user.id,
    }


@app.post("/api/v2/auth/login")
@limiter.limit("20/minute")
def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db=Depends(get_db),
):
    user = db.query(User).filter(
        User.email == form_data.username
    ).first()

    if not user or not verify_password(
        form_data.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_data_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=1440),
    )

    return {"access_token": token, "token_type": "bearer"}


# ---------------------------------------------------------
# PROJECT MANAGEMENT
# ---------------------------------------------------------

@app.post("/api/v2/projects")
@limiter.limit("30/minute")
def save_user_project(
    request: Request,
    project: ProjectSaveRequest,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    new_project = Project(
        title=project.title,
        book_type=project.book_type,
        format_size=project.format_size,
        column_count=project.column_count,
        canonical_data=project.canonical_data,
        user_id=current_user.id,
    )

    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    return {
        "status": "success",
        "message": "Project saved successfully to SaaS vault.",
        "project_id": new_project.id,
    }


@app.get("/api/v2/projects")
def get_user_projects(
    current_user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    projects = (
        db.query(Project)
        .filter(Project.user_id == current_user.id)
        .all()
    )

    return {
        "status": "success",
        "total_projects": len(projects),
        "projects": [
            {
                "id": project.id,
                "title": project.title,
                "book_type": project.book_type,
                "format_size": project.format_size,
                "column_count": project.column_count,
                "created_at": project.created_at,
            }
            for project in projects
        ],
    }


# ---------------------------------------------------------
# ASYNC PDF GENERATION
# ---------------------------------------------------------

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
    header_alignment: int,
):
    try:
        with job_status_lock:
            job_status_store[job_id] = {
                "status": "processing",
                "progress": 50,
            }

        final_path = generate_pdf_to_path(
            output_path=output_path,
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
            header_alignment=header_alignment,
        )

        with job_status_lock:
            job_status_store[job_id] = {
                "status": "completed",
                "file_path": final_path,
                "filename": f"exampress_{book_type}_{format_size}.pdf",
            }

        logger.info("Background PDF job completed: %s", job_id)

    except Exception as exc:
        for candidate in {output_path}:
            if os.path.isfile(candidate):
                try:
                    os.remove(candidate)
                except OSError:
                    pass

        with job_status_lock:
            job_status_store[job_id] = {
                "status": "failed",
                "error": str(exc),
            }

        logger.exception("Background PDF job failed: %s", job_id)


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
    file: UploadFile = File(None),
):
    validate_layout_settings(
        book_type,
        format_size,
        column_count,
        font_size=font_size,
        line_spacing=line_spacing,
        question_gap=question_gap,
        option_top_gap=option_top_gap,
        column_gap_val=column_gap_val,
        footer_bottom_margin=footer_bottom_margin,
        option_vertical_gap=option_vertical_gap,
        header_font_size=header_font_size,
        header_alignment=header_alignment,
    )

    if not file or not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Upload a source file before generating the book.",
        )

    tmp_input_path = None
    output_path = os.path.join(
        tempfile.gettempdir(),
        f"exampress_job_{uuid.uuid4()}.pdf",
    )

    try:
        extension = get_upload_extension(file.filename)
        tmp_input_path, _ = save_upload_to_temp(file, extension)

        canonical_data = parse_input_file(
            tmp_input_path,
            file.filename,
            book_type,
            format_size,
            column_count,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Async generation input parsing failed.")
        raise HTTPException(
            status_code=400,
            detail=f"Universal Parser Error: {str(exc)}",
        ) from exc
    finally:
        if tmp_input_path and os.path.exists(tmp_input_path):
            try:
                os.remove(tmp_input_path)
            except OSError:
                logger.warning("Could not remove temporary input file.")

    job_id = str(uuid.uuid4())

    with job_status_lock:
        job_status_store[job_id] = {"status": "queued"}

    background_tasks.add_task(
        background_generate_book_task,
        job_id=job_id,
        book_type=book_type,
        format_size=format_size,
        column_count=column_count,
        canonical_data=canonical_data,
        output_path=output_path,
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
        header_alignment=header_alignment,
    )

    return {
        "status": "success",
        "message": "Book generation queued successfully.",
        "job_id": job_id,
        "status_check_url": f"/api/v2/jobs/{job_id}",
        "download_url": f"/api/v2/jobs/{job_id}/download",
    }


@app.get("/api/v2/jobs/{job_id}")
def check_job_status(job_id: str):
    with job_status_lock:
        job = job_status_store.get(job_id)

        if not job:
            raise HTTPException(status_code=404, detail="Job ID not found.")

        # Do not expose internal server filesystem paths.
        public_job = {
            key: value
            for key, value in job.items()
            if key != "file_path"
        }

    return {"job_id": job_id, "job_info": public_job}


@app.get("/api/v2/jobs/{job_id}/download")
def download_generated_job(job_id: str):
    with job_status_lock:
        job = job_status_store.get(job_id)

        if not job:
            raise HTTPException(status_code=404, detail="Job ID not found.")

        if job.get("status") != "completed":
            raise HTTPException(
                status_code=409,
                detail=f"PDF is not ready. Current status: {job.get('status')}",
            )

        file_path = job.get("file_path")
        filename = job.get("filename", "exampress_book.pdf")

        if not file_path or not os.path.isfile(file_path):
            raise HTTPException(
                status_code=410,
                detail="Generated PDF is no longer available.",
            )

        try:
            with open(file_path, "rb") as pdf_file:
                pdf_bytes = pdf_file.read()
        except OSError as exc:
            raise HTTPException(
                status_code=500,
                detail="Could not read the generated PDF.",
            ) from exc

        job_status_store[job_id] = {
            "status": "downloaded",
            "filename": filename,
        }

    try:
        os.remove(file_path)
    except OSError:
        logger.warning("Could not remove downloaded PDF for job %s", job_id)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )


# ---------------------------------------------------------
# IDML EXPORT
# ---------------------------------------------------------

@app.post("/api/v2/export-idml")
@limiter.limit("10/minute")
async def export_book_idml(
    request: Request,
    book_type: str = Form("quiz"),
    format_size: str = Form("B5"),
    column_count: int = Form(2),
    current_user: User = Depends(get_current_user),
):
    validate_layout_settings(book_type, format_size, column_count)

    tmp_idml_path = None

    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".idml",
        ) as tmp_file:
            tmp_idml_path = tmp_file.name

        canonical_data = {
            "title": "Exampress IDML Export",
            "book_type": book_type,
            "format_size": format_size,
            "column_count": column_count,
            "chapters": [
                {
                    "chapter_title": "Chapter 1",
                    "blocks": [
                        {
                            "type": "question",
                            "q_no": 1,
                            "text": (
                                "Does IDML allow round-trip editing "
                                "with professional designers?"
                            ),
                            "options": ["No", "Yes", "Maybe", "Never"],
                            "answer": "Yes",
                            "explanation": (
                                "IDML packages XML stories and spreads "
                                "for InDesign typesetting."
                            ),
                        }
                    ],
                }
            ],
        }

        output_file = IDMLGenerator.generate_idml_package(
            canonical_data,
            tmp_idml_path,
        )

        if not output_file or not os.path.isfile(output_file):
            raise HTTPException(
                status_code=500,
                detail="IDML generation engine failed.",
            )

        with open(output_file, "rb") as idml_file:
            idml_bytes = idml_file.read()

        return Response(
            content=idml_bytes,
            media_type="application/vnd.adobe.indesign-idml-package",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="exampress_{book_type}_{format_size}.idml"'
                )
            },
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("IDML pipeline failed.")
        raise HTTPException(
            status_code=500,
            detail=f"IDML Pipeline Error: {str(exc)}",
        ) from exc
    finally:
        if tmp_idml_path and os.path.exists(tmp_idml_path):
            try:
                os.remove(tmp_idml_path)
            except OSError:
                logger.warning("Could not remove temporary IDML file.")


# ---------------------------------------------------------
# SINGLE PDF GENERATION
# ---------------------------------------------------------

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
    file: UploadFile = File(None),
):
    validate_layout_settings(
        book_type,
        format_size,
        column_count,
        font_size=font_size,
        line_spacing=line_spacing,
        question_gap=question_gap,
        option_top_gap=option_top_gap,
        column_gap_val=column_gap_val,
        footer_bottom_margin=footer_bottom_margin,
        option_vertical_gap=option_vertical_gap,
        header_font_size=header_font_size,
        header_alignment=header_alignment,
    )

    if not file or not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Upload a source file before generating the book.",
        )

    tmp_input_path = None
    tmp_output_path = None
    alternate_output_path = None

    try:
        extension = get_upload_extension(file.filename)
        tmp_input_path, _ = save_upload_to_temp(file, extension)

        try:
            canonical_data = parse_input_file(
                tmp_input_path,
                file.filename,
                book_type,
                format_size,
                column_count,
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Input parsing failed.")
            raise HTTPException(
                status_code=400,
                detail=f"Universal Parser Error: {str(exc)}",
            ) from exc

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".pdf",
        ) as tmp_output:
            tmp_output_path = tmp_output.name

        output_pdf = generate_pdf_to_path(
            output_path=tmp_output_path,
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
            header_alignment=header_alignment,
        )

        if os.path.abspath(output_pdf) != os.path.abspath(tmp_output_path):
            alternate_output_path = output_pdf

        with open(output_pdf, "rb") as pdf_file:
            pdf_bytes = pdf_file.read()

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="exampress_{book_type}_{format_size}_{column_count}col.pdf"'
                )
            },
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("PDF generation pipeline failed.")
        raise HTTPException(
            status_code=500,
            detail=f"PDF generation failed: {str(exc)}",
        ) from exc
    finally:
        for path in (tmp_input_path, tmp_output_path, alternate_output_path):
            if path and os.path.isfile(path):
                try:
                    os.remove(path)
                except OSError:
                    logger.warning("Could not remove a temporary PDF/input file.")


# ---------------------------------------------------------
# PDF PREVIEW
# ---------------------------------------------------------

@app.post("/api/v2/preview-pdf")
@limiter.limit("30/minute")
async def preview_generated_pdf(
    request: Request,
    file: UploadFile = File(...),
):
    if not fitz:
        raise HTTPException(
            status_code=503,
            detail="PyMuPDF is not installed on the backend.",
        )

    tmp_preview_path = None
    doc = None

    try:
        tmp_preview_path, _ = save_upload_to_temp(file, ".pdf")

        try:
            doc = fitz.open(tmp_preview_path)

            if doc.page_count == 0:
                raise HTTPException(
                    status_code=400,
                    detail="Uploaded PDF contains no pages.",
                )

            total_pages = doc.page_count
            page = doc.load_page(0)
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
            encoded_img = base64.b64encode(img_bytes).decode("ascii")

        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is not a readable PDF.",
            ) from exc

        return JSONResponse(
            content={
                "status": "success",
                "total_pages": total_pages,
                "preview_thumbnail": f"data:image/png;base64,{encoded_img}",
            }
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("PDF preview failed.")
        raise HTTPException(
            status_code=500,
            detail="PDF preview generation failed.",
        ) from exc
    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass

        if tmp_preview_path and os.path.exists(tmp_preview_path):
            try:
                os.remove(tmp_preview_path)
            except OSError:
                logger.warning("Could not remove preview temporary file.")


# ---------------------------------------------------------
# BATCH PDF EXPORT
# ---------------------------------------------------------

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
    files: list[UploadFile] = File(...),
):
    validate_layout_settings(
        book_type,
        format_size,
        column_count,
        font_size=font_size,
        line_spacing=line_spacing,
        question_gap=question_gap,
        option_top_gap=option_top_gap,
        column_gap_val=column_gap_val,
        footer_bottom_margin=footer_bottom_margin,
        option_vertical_gap=option_vertical_gap,
        header_font_size=header_font_size,
        header_alignment=header_alignment,
    )

    if not files:
        raise HTTPException(status_code=400, detail="No files were uploaded.")

    if len(files) > MAX_BATCH_FILES:
        raise HTTPException(
            status_code=413,
            detail=f"A batch can contain at most {MAX_BATCH_FILES} files.",
        )

    batch_tmp_dir = tempfile.mkdtemp(prefix="exampress_batch_")
    zip_output_path = None
    total_upload_size = 0

    try:
        generated_pdfs = []
        pdf_gen = PDFGenerator()

        for index, upload in enumerate(files):
            if not upload.filename:
                continue

            extension = get_upload_extension(upload.filename)
            input_path = os.path.join(
                batch_tmp_dir,
                f"input_{index}{extension}",
            )

            upload.file.seek(0, os.SEEK_END)
            file_size = upload.file.tell()
            upload.file.seek(0)

            if file_size <= 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {index + 1} is empty.",
                )

            if file_size > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail=f"File {index + 1} exceeds the 100 MB limit.",
                )

            total_upload_size += file_size
            if total_upload_size > MAX_BATCH_TOTAL_SIZE:
                raise HTTPException(
                    status_code=413,
                    detail="Combined batch upload exceeds the 250 MB limit.",
                )

            with open(input_path, "wb") as destination:
                shutil.copyfileobj(upload.file, destination)

            try:
                canonical_data = parse_input_file(
                    input_path,
                    upload.filename,
                    book_type,
                    format_size,
                    column_count,
                )
            except HTTPException:
                raise
            except Exception as exc:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Could not parse file {index + 1} "
                        f"({safe_output_basename(upload.filename)}): {exc}"
                    ),
                ) from exc

            safe_name = safe_output_basename(upload.filename)
            pdf_filename = (
                f"{safe_name}_typeset_{book_type}_{index + 1}.pdf"
            )
            pdf_path = os.path.join(batch_tmp_dir, pdf_filename)

            try:
                result_path = pdf_gen.generate_pdf(
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
                    header_alignment=header_alignment,
                )

                actual_path = result_path or pdf_path

                if not os.path.isfile(actual_path) or os.path.getsize(actual_path) == 0:
                    raise RuntimeError("PDF output was not created.")

                # Ensure the output is included in the temporary batch folder.
                if os.path.abspath(actual_path) != os.path.abspath(pdf_path):
                    shutil.copy2(actual_path, pdf_path)

                generated_pdfs.append(pdf_path)

            except Exception as exc:
                logger.exception("Batch PDF generation failed for file %s", index + 1)
                raise HTTPException(
                    status_code=500,
                    detail=f"PDF generation failed for file {index + 1}: {exc}",
                ) from exc

        if not generated_pdfs:
            raise HTTPException(
                status_code=400,
                detail="No valid books could be generated from the uploaded batch.",
            )

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".zip",
        ) as zip_tmp:
            zip_output_path = zip_tmp.name

        with zipfile.ZipFile(
            zip_output_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as zip_ref:
            for pdf_path in generated_pdfs:
                zip_ref.write(pdf_path, arcname=os.path.basename(pdf_path))

        with open(zip_output_path, "rb") as zip_file:
            zip_bytes = zip_file.read()

        return Response(
            content=zip_bytes,
            media_type="application/zip",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="exampress_batch_export_{book_type}.zip"'
                )
            },
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Batch export failed.")
        raise HTTPException(
            status_code=500,
            detail=f"Batch export failed: {str(exc)}",
        ) from exc
    finally:
        if os.path.exists(batch_tmp_dir):
            try:
                shutil.rmtree(batch_tmp_dir)
            except OSError:
                logger.warning("Could not remove batch temporary directory.")

        if zip_output_path and os.path.exists(zip_output_path):
            try:
                os.remove(zip_output_path)
            except OSError:
                logger.warning("Could not remove temporary batch ZIP.")
