import os
import json
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from core.schemas import (
    TranslationRequest,
    TranslationResponse,
    ContextHistoryResponse,
    HumanReviewRequest,
    FeedbackRequest,
    HumanReviewResponse,
    UserCreate,
    UserResponse
)
from pipeline.orchestrator import TranslationPipeline, LanguageMismatchError
from core.config import settings
from core.database import get_db, TranslationLog, FeedbackLog, User

router = APIRouter()
pipeline = TranslationPipeline()

SUPPORTED_LANGUAGES = [
    {"code": "en", "name": "English", "native": "English", "dir": "ltr"},
    {"code": "ur", "name": "Urdu", "native": "اردو", "dir": "rtl"}
]

@router.post("/translate", response_model=TranslationResponse)
async def translate(request: TranslationRequest, db: Session = Depends(get_db)):
    try:
        user_id = request.user_id
        username = (request.username or "default").strip().lower()
        if user_id is None and username:
            user = db.query(User).filter(User.username == username).first()
            if user:
                user_id = user.id
            else:
                try:
                    user = User(username=username, display_name=username.title())
                    db.add(user)
                    db.commit()
                    db.refresh(user)
                    user_id = user.id
                except Exception:
                    db.rollback()

        response = pipeline.process(
            raw_text=request.text,
            source_lang=request.source_lang or "en",
            target_lang=request.target_lang or "ur",
            session_id=request.session_id or "default",
            user_id=user_id,
            username=username
        )
        return response
    except LanguageMismatchError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/human-review", response_model=HumanReviewResponse)
async def submit_human_review(request: HumanReviewRequest, db: Session = Depends(get_db)):
    """Node N -> Node M -> Node P -> Node E & Node O: Handles human reviewer action."""
    try:
        user_id = request.user_id
        username = (request.username or "default").strip().lower()
        if user_id is None and username:
            user = db.query(User).filter(User.username == username).first()
            if user:
                user_id = user.id

        result = pipeline.submit_human_review(
            session_id=request.session_id,
            original_text=request.original_text,
            ai_translation=request.ai_translation,
            action=request.action,
            final_translation=request.final_translation,
            risk_level=request.risk_level or "",
            reviewer_notes=request.reviewer_notes or "",
            user_id=user_id,
            username=username
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/feedback", response_model=HumanReviewResponse)
async def submit_feedback(request: FeedbackRequest, db: Session = Depends(get_db)):
    """
    Requirement 1 Deliverable: POST /api/v1/feedback
    Accepts and stores human-corrected text from Human-in-the-Loop review with user metadata.
    """
    try:
        user_id = request.user_id
        username = (request.username or "default").strip().lower()
        if user_id is None and username:
            user = db.query(User).filter(User.username == username).first()
            if user:
                user_id = user.id

        result = pipeline.submit_human_review(
            session_id=request.session_id,
            original_text=request.original_text,
            ai_translation=request.ai_translation,
            action=request.action,
            final_translation=request.final_translation,
            risk_level=request.risk_level or "",
            reviewer_notes=request.reviewer_notes or "",
            user_id=user_id,
            username=username
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
async def get_history_logs(
    session_id: Optional[str] = None,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Requirement 2 Deliverable: GET /api/v1/history
    Fetches persistent translation logs from SQLite database using SQLAlchemy,
    supporting filtering by session_id, user_id, or username.
    """
    query = db.query(TranslationLog)
    if session_id:
        query = query.filter(TranslationLog.session_id == session_id)
    if user_id is not None:
        query = query.filter(TranslationLog.user_id == user_id)
    if username:
        query = query.filter(TranslationLog.username == username.strip().lower())
    logs = query.order_by(TranslationLog.id.desc()).limit(limit).all()
    return [
        {
            "id": log.id,
            "session_id": log.session_id,
            "user_id": log.user_id,
            "username": log.username or "default",
            "source_text": log.source_text,
            "target_text": log.target_text,
            "detected_script": log.detected_script,
            "processing_time_ms": log.processing_time,
            "confidence_score": log.confidence_score,
            "final_risk_status": log.final_risk_status,
            "created_at": log.created_at.isoformat() if log.created_at else None
        }
        for log in logs
    ]

# ---------------------------------------------------------------------------
# User Management Endpoints
# ---------------------------------------------------------------------------

@router.get("/users")
async def list_users(db: Session = Depends(get_db)):
    """Fetches all registered users with their individual translation activity count."""
    users = db.query(User).order_by(User.id.asc()).all()
    results = []
    for u in users:
        count = db.query(TranslationLog).filter(TranslationLog.user_id == u.id).count()
        results.append({
            "id": u.id,
            "username": u.username,
            "display_name": u.display_name or u.username,
            "email": u.email,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "total_translations": count
        })
    return results

@router.post("/users")
async def create_user(user_in: UserCreate, db: Session = Depends(get_db)):
    """Creates a new user profile for maintaining distinct translation history."""
    clean_username = user_in.username.strip().lower()
    existing = db.query(User).filter(User.username == clean_username).first()
    if existing:
        count = db.query(TranslationLog).filter(TranslationLog.user_id == existing.id).count()
        return {
            "id": existing.id,
            "username": existing.username,
            "display_name": existing.display_name,
            "email": existing.email,
            "created_at": existing.created_at.isoformat() if existing.created_at else None,
            "total_translations": count,
            "message": "User already exists"
        }
    
    new_user = User(
        username=clean_username,
        display_name=user_in.display_name.strip() if user_in.display_name else clean_username.title(),
        email=user_in.email.strip() if user_in.email else None
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {
        "id": new_user.id,
        "username": new_user.username,
        "display_name": new_user.display_name,
        "email": new_user.email,
        "created_at": new_user.created_at.isoformat() if new_user.created_at else None,
        "total_translations": 0,
        "message": "User created successfully"
    }

@router.get("/users/{user_id_or_name}")
async def get_user_detail(user_id_or_name: str, db: Session = Depends(get_db)):
    """Fetch profile and stats for a specific user by ID or username."""
    if user_id_or_name.isdigit():
        user = db.query(User).filter(User.id == int(user_id_or_name)).first()
    else:
        user = db.query(User).filter(User.username == user_id_or_name.strip().lower()).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    count = db.query(TranslationLog).filter(TranslationLog.user_id == user.id).count()
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name or user.username,
        "email": user.email,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "total_translations": count
    }

@router.delete("/users/{user_id_or_name}")
async def delete_user(user_id_or_name: str, db: Session = Depends(get_db)):
    """Deletes a user profile (preventing deletion of the default user)."""
    if user_id_or_name.isdigit():
        user = db.query(User).filter(User.id == int(user_id_or_name)).first()
    else:
        user = db.query(User).filter(User.username == user_id_or_name.strip().lower()).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.username == "default":
        raise HTTPException(status_code=400, detail="Cannot delete default system user")
    
    username = user.username
    db.delete(user)
    db.commit()
    return {"status": "success", "message": f"User '{username}' deleted successfully."}

@router.delete("/users/{user_id_or_name}/history")
async def clear_user_history(user_id_or_name: str, db: Session = Depends(get_db)):
    """Clears all translation history logs for a specific user."""
    if user_id_or_name.isdigit():
        user = db.query(User).filter(User.id == int(user_id_or_name)).first()
    else:
        user = db.query(User).filter(User.username == user_id_or_name.strip().lower()).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    deleted_count = db.query(TranslationLog).filter(TranslationLog.user_id == user.id).delete()
    db.commit()
    return {
        "status": "success",
        "deleted_logs": deleted_count,
        "username": user.username,
        "message": f"Cleared {deleted_count} logs for user '{user.username}'"
    }

@router.get("/evaluation-dataset")
async def get_evaluation_dataset():
    """Node O: Fetches the benchmark evaluation dataset and human review log."""
    path = "data/evaluation_dataset.json"
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"benchmark_cases": [], "human_reviewed_samples": []}

@router.get("/metrics")
async def get_system_metrics():
    """Nodes Q (Cost), R (Latency), S (Quality): Telemetry snapshots."""
    return pipeline.monitor.get_system_metrics()

@router.get("/scenarios")
async def get_scenarios():
    """Quick 1-Click Golden Test Scenarios for English <-> Urdu."""
    return [
        # Urdu Script Scenarios (ur -> en)
        {
            "id": "atm_hardware_failure_ur",
            "category": "ATM Hardware Failure",
            "title": "اے ٹی ایم کارڈ پھنس گیا (ATM Jammed)",
            "text": "اے ٹی ایم میں کارڈ ڈالا تھا مگر واپس نہیں ملا، مشین میں پھنس گیا ہے۔",
            "source_lang": "ur",
            "target_lang": "en",
            "risk_type": "Hardware Failure"
        },
        {
            "id": "failed_raast_transfer_ur",
            "category": "Failed Transfer",
            "title": "راستہ ٹرانسفر کٹوتی (Raast PKR 5,000)",
            "text": "میرا راستہ ٹرانسفر فیل ہو گیا، اکاؤنٹ سے 5000 روپے کٹ گئے پر وصول کنندہ کو نہیں ملے۔",
            "source_lang": "ur",
            "target_lang": "en",
            "risk_type": "Debit State & Amount"
        },
        {
            "id": "double_deduction_ur",
            "category": "Double Deduction",
            "title": "دوہری کٹوتی (Double Deduction)",
            "text": "فوڈ پانڈا پر ادائیگی کی، دو دفعہ پیسے کٹ گئے ہیں برائے مہربانی رقم واپس کی جائے۔",
            "source_lang": "ur",
            "target_lang": "en",
            "risk_type": "Duplicate Charge"
        },
        {
            "id": "app_crash_pending_ur",
            "category": "App Crash / Timeout",
            "title": "ایپ کریش زیر التواء (In-Flight Timeout)",
            "text": "ادائیگی کے دوران موبائل ایپ بند ہو گئی اور اب اسٹیٹس زیر التواء آ رہا ہے۔",
            "source_lang": "ur",
            "target_lang": "en",
            "risk_type": "In-Flight State"
        },
        {
            "id": "unauthorized_fraud_ur",
            "category": "Fraud / Scam",
            "title": "مشکوک او ٹی پی کٹوتی (OTP Fraud 25k)",
            "text": "او ٹی پی کا میسج آیا اور فوری طور پر پچیس ہزار روپے نکل گئے، میں نے کوئی ٹرانزیکشن نہیں کی۔",
            "source_lang": "ur",
            "target_lang": "en",
            "risk_type": "Fraud Security"
        },
        {
            "id": "biometric_lockout_ur",
            "category": "Biometric Auth",
            "title": "فنگر پرنٹ لاک (Biometric Lockout)",
            "text": "فنگر پرنٹ تصدیق نہیں ہو رہی اور پچھلے تین دن سے اکاؤنٹ لاک ہے۔",
            "source_lang": "ur",
            "target_lang": "en",
            "risk_type": "Account Lockout"
        },
        {
            "id": "refund_delay_ur",
            "category": "Refund Reversal",
            "title": "ریفنڈ میں تاخیر (Refund Delay)",
            "text": "دراز کا ریفنڈ ایک ہفتہ پہلے مانگا تھا، رقم ابھی تک اکاؤنٹ میں واپس نہیں آئی۔",
            "source_lang": "ur",
            "target_lang": "en",
            "risk_type": "Reversal Delay"
        },

        # English Scenarios (en -> ur)
        {
            "id": "atm_swallowed_card_en",
            "category": "ATM Hardware Failure",
            "title": "ATM Jammed / Swallowed Card",
            "text": "ATM machine swallowed my debit card during cash withdrawal, please block and reissue.",
            "source_lang": "en",
            "target_lang": "ur",
            "risk_type": "Hardware Failure"
        },
        {
            "id": "raast_transfer_dispute_en",
            "category": "Failed Transfer",
            "title": "Raast Transfer (PKR 5,000 Debited)",
            "text": "My Raast transfer of PKR 5,000 failed; amount was debited from account but not credited to recipient.",
            "source_lang": "en",
            "target_lang": "ur",
            "risk_type": "Debit State & Amount"
        },
        {
            "id": "double_charge_refund_en",
            "category": "Double Deduction",
            "title": "Foodpanda Double Charge",
            "text": "I was charged twice for my online food delivery order, please initiate immediate reversal of PKR 2,450.",
            "source_lang": "en",
            "target_lang": "ur",
            "risk_type": "Duplicate Charge"
        },
        {
            "id": "app_crash_timeout_en",
            "category": "App Crash / Timeout",
            "title": "Payment In-Flight Crash",
            "text": "The mobile banking application crashed during payment processing, transaction is currently showing pending.",
            "source_lang": "en",
            "target_lang": "ur",
            "risk_type": "In-Flight State"
        },
        {
            "id": "fraud_alert_en",
            "category": "Fraud / Scam",
            "title": "Suspicious OTP Drain (PKR 25,000)",
            "text": "Unauthorized transaction alert: 25,000 PKR was debited immediately following a suspicious OTP notification.",
            "source_lang": "en",
            "target_lang": "ur",
            "risk_type": "Fraud Security"
        },
        {
            "id": "current_affairs_rule_en",
            "category": "Loanword Rule",
            "title": "Current Affairs Loanword Rule",
            "text": "We will study current affairs today in our banking compliance committee meeting.",
            "source_lang": "en",
            "target_lang": "ur",
            "risk_type": "Exact Loanword"
        },
        {
            "id": "agent_reversal_resolution_en",
            "category": "Resolution Notice",
            "title": "Agent Reversal Notice (PKR 5,000)",
            "text": "Duplicate charge of PKR 5,000 has been verified and reversed to your account balance successfully.",
            "source_lang": "en",
            "target_lang": "ur",
            "risk_type": "Customer Resolution"
        }
    ]

@router.get("/languages")
async def get_languages():
    return {
        "total": len(SUPPORTED_LANGUAGES),
        "languages": SUPPORTED_LANGUAGES
    }

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Bilangual Neural AI Engine",
        "model": getattr(settings, "GEMINI_MODEL", "gemini-3.5-flash-lite"),
        "version": "3.0.0"
    }

@router.get("/context/{session_id}", response_model=ContextHistoryResponse)
async def get_session_context(session_id: str):
    messages = pipeline.context_manager.get_messages(session_id)
    return ContextHistoryResponse(
        session_id=session_id,
        messages=messages,
        total_turns=len(messages)
    )

@router.delete("/context/{session_id}")
async def clear_session_context(session_id: str):
    pipeline.context_manager.clear_session(session_id)
    return {"message": f"Session '{session_id}' context cleared.", "session_id": session_id}