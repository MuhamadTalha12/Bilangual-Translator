import os
from datetime import datetime
from typing import Generator
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, ForeignKey, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship

# SQLite Database File Path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bilangual_history.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    """
    SQLAlchemy model storing user profiles for tracking individual translation histories and feedback logs.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    display_name = Column(String(150), nullable=True)
    email = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    translations = relationship("TranslationLog", back_populates="user", cascade="all, delete-orphan")
    feedback = relationship("FeedbackLog", back_populates="user", cascade="all, delete-orphan")


class TranslationLog(Base):
    """
    SQLAlchemy model storing every API translation request, detected script,
    processing latency, output confidence score, final risk status, and user association.
    """
    __tablename__ = "translation_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(100), index=True, default="default")
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    username = Column(String(100), index=True, default="default")
    source_text = Column(Text, nullable=False)
    target_text = Column(Text, nullable=False)
    detected_script = Column(String(50), default="en")
    processing_time = Column(Float, default=0.0)  # Latency in ms
    confidence_score = Column(Float, default=1.0)  # Model confidence 0.0 to 1.0
    final_risk_status = Column(String(100), default="LOW_RISK_APPROVED")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="translations")


class FeedbackLog(Base):
    """
    SQLAlchemy model storing Human-in-the-Loop review actions (Accept, Correct Inplace, Reject).
    """
    __tablename__ = "feedback_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(100), index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    username = Column(String(100), index=True, default="default")
    original_text = Column(Text, nullable=False)
    ai_translation = Column(Text, nullable=False)
    action = Column(String(50), nullable=False)  # 'accept', 'correct', or 'reject'
    final_translation = Column(Text, nullable=False)
    risk_level = Column(String(100), default="")
    reviewer_notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="feedback")


def init_db():
    """Initializes SQLite database tables and handles column migrations seamlessly."""
    Base.metadata.create_all(bind=engine)

    # Perform lightweight migration for existing SQLite databases
    with engine.connect() as conn:
        try:
            # Check translation_logs columns
            res = conn.execute(text("PRAGMA table_info(translation_logs);")).fetchall()
            col_names = [r[1] for r in res]
            if "user_id" not in col_names:
                conn.execute(text("ALTER TABLE translation_logs ADD COLUMN user_id INTEGER;"))
            if "username" not in col_names:
                conn.execute(text("ALTER TABLE translation_logs ADD COLUMN username VARCHAR(100) DEFAULT 'default';"))

            # Check feedback_logs columns
            res_fb = conn.execute(text("PRAGMA table_info(feedback_logs);")).fetchall()
            fb_cols = [r[1] for r in res_fb]
            if "user_id" not in fb_cols:
                conn.execute(text("ALTER TABLE feedback_logs ADD COLUMN user_id INTEGER;"))
            if "username" not in fb_cols:
                conn.execute(text("ALTER TABLE feedback_logs ADD COLUMN username VARCHAR(100) DEFAULT 'default';"))
            
            conn.commit()
        except Exception as mig_err:
            print(f"Database migration note: {mig_err}")

    # Seed default user if not exists
    db = SessionLocal()
    try:
        default_user = db.query(User).filter(User.username == "default").first()
        if not default_user:
            default_user = User(
                username="default",
                display_name="Default User",
                email="user@bilangual.ai"
            )
            db.add(default_user)
            db.commit()
            db.refresh(default_user)

        # Backfill existing logs that have null user_id/username
        db.query(TranslationLog).filter(
            (TranslationLog.user_id == None) | (TranslationLog.username == None)
        ).update({
            TranslationLog.user_id: default_user.id,
            TranslationLog.username: default_user.username
        }, synchronize_session=False)

        db.query(FeedbackLog).filter(
            (FeedbackLog.user_id == None) | (FeedbackLog.username == None)
        ).update({
            FeedbackLog.user_id: default_user.id,
            FeedbackLog.username: default_user.username
        }, synchronize_session=False)

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Warning initializing default user: {e}")
    finally:
        db.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI Dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

