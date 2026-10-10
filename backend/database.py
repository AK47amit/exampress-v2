import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Database URL: defaults to local SQLite file for development, can be overridden by env variable for production (PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./exampress_saas.db")

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# Session local factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Dependency injection for database sessions in FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()