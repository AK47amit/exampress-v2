import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationship to user's projects
    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    book_type = Column(String, default="quiz")          # quiz, theory, solutions
    format_size = Column(String, default="B5")        # B5, A4
    column_count = Column(Integer, default=2)         # 2 or 3 columns
    canonical_data = Column(JSON, nullable=True)      # Stored structured canonical JSON
    pdf_output_path = Column(String, nullable=True)   # Generated PDF path or reference
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationship back to User
    owner = relationship("User", back_populates="projects")