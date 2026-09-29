import os
from datetime import datetime
from typing import Generator
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# SQLite Database File Path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bilangual_history.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class TranslationLog(Base):
    """
    SQLAlchemy model storing every API translation request, detected script,
    processing latency, output confidence score, and final risk status.
    """
    __tablename__ = "translation_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(100), index=True, default="default")
    source_text = Column(Text, nullable=False)
    target_text = Column(Text, nullable=False)
    detected_script = Column(String(50), default="en")
    processing_time = Column(Float, default=0.0)  # Latency in ms
    confidence_score = Column(Float, default=1.0)  # Model confidence 0.0 to 1.0
    final_risk_status = Column(String(100), default="LOW_RISK_APPROVED")
    created_at = Column(DateTime, default=datetime.utcnow)


class FeedbackLog(Base):
    """
    SQLAlchemy model storing Human-in-the-Loop review actions (Accept, Correct Inplace, Reject).
    """
    __tablename__ = "feedback_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(100), index=True)
    original_text = Column(Text, nullable=False)
    ai_translation = Column(Text, nullable=False)
    action = Column(String(50), nullable=False)  # 'accept', 'correct', or 'reject'
    final_translation = Column(Text, nullable=False)
    risk_level = Column(String(100), default="")
    reviewer_notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Initializes SQLite database tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI Dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
