from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=50, description="Unique username")
    display_name: Optional[str] = Field(None, max_length=150, description="Display name or full name")
    email: Optional[str] = Field(None, max_length=255, description="Optional email address")

class UserResponse(BaseModel):
    id: int
    username: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    created_at: Optional[str] = None
    total_translations: int = 0

class TranslationRequest(BaseModel):
    text: str = Field(..., description="The input text to translate")
    source_lang: Optional[str] = Field("en", description="Source language code ('en', 'ur', 'auto')")
    target_lang: Optional[str] = Field("ur", description="Target language code ('ur', 'en')")
    session_id: Optional[str] = Field("default", description="Unique conversation session ID")
    user_id: Optional[int] = Field(None, description="Optional user ID for maintaining user-specific logs")
    username: Optional[str] = Field("default", description="Optional username for user-specific history")

class LatencyBreakdown(BaseModel):
    preprocessing_ms: float = 0.0
    detection_ms: float = 0.0
    llm_ms: float = 0.0
    risk_eval_ms: float = 0.0
    total_ms: float = 0.0

class CostMetrics(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    cache_hit: bool = False

class QualityMetrics(BaseModel):
    is_acceptable: bool = True
    risk_status: str = "LOW_RISK_APPROVED"
    confidence: float = 1.0
    confidence_score: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score from model output (0.0 to 1.0)")
    numbers_match: bool = True
    state_consistent: bool = True

class CrawlStageMetrics(BaseModel):
    stage: str = "CRAWL"
    passed: bool = True
    entity_preservation: bool = True
    state_consistency: bool = True
    multiplier_retention: bool = True
    hardware_jam_integrity: bool = True
    latency_ms: float = 0.0

class WalkStageMetrics(BaseModel):
    stage: str = "WALK"
    human_review_required: bool = False
    action_taken: str = "auto_approved"  # "auto_approved", "human_accepted", "human_corrected", "human_rejected"
    dataset_logged: bool = False

class RunStageMetrics(BaseModel):
    stage: str = "RUN"
    telemetry_recorded: bool = True
    cost_usd: float = 0.0
    latency_total_ms: float = 0.0
    quality_pass_rate_pct: float = 100.0

class CrawlWalkRunReport(BaseModel):
    active_stage: str = "CRAWL"  # Current active risk stage: "CRAWL", "WALK", or "RUN"
    crawl: CrawlStageMetrics = Field(default_factory=CrawlStageMetrics)
    walk: WalkStageMetrics = Field(default_factory=WalkStageMetrics)
    run: RunStageMetrics = Field(default_factory=RunStageMetrics)

class TranslationResponse(BaseModel):
    original_text: str
    translation: str
    source_lang: Optional[str] = "en"
    target_lang: Optional[str] = "ur"
    detected_language: str
    detected_code: Optional[str] = "en"
    detected_label: Optional[str] = "English"
    confidence: Optional[float] = 0.99
    confidence_score: float = Field(0.99, ge=0.0, le=1.0, description="Confidence score from model output (0.0 to 1.0)")
    pronunciation: Optional[str] = ""
    synonyms: Optional[List[str]] = []
    definitions: Optional[List[str]] = []
    risk_level: str = "LOW_RISK_APPROVED"
    risk_details: str = "All checks passed"
    needs_human_review: bool = False
    original_numbers: Optional[List[str]] = []
    translated_numbers: Optional[List[str]] = []
    processing_time_ms: float
    latency_breakdown: Optional[LatencyBreakdown] = None
    cost_metrics: Optional[CostMetrics] = None
    quality_metrics: Optional[QualityMetrics] = None
    crawl_walk_run: Optional[CrawlWalkRunReport] = None
    session_id: Optional[str] = "default"
    user_id: Optional[int] = None
    username: Optional[str] = "default"

class HumanReviewRequest(BaseModel):
    session_id: str
    original_text: str
    ai_translation: str
    action: str = Field(..., description="'accept', 'correct', or 'reject'")
    final_translation: str = Field(..., description="The approved or human-corrected final text")
    risk_level: Optional[str] = ""
    reviewer_notes: Optional[str] = ""
    user_id: Optional[int] = None
    username: Optional[str] = "default"

class FeedbackRequest(HumanReviewRequest):
    """Feedback request schema matching HumanReviewRequest for /api/v1/feedback."""
    pass

class HumanReviewResponse(BaseModel):
    status: str
    message: str
    action_taken: str
    final_translation: str
    session_id: str
    user_id: Optional[int] = None
    username: Optional[str] = "default"
    logged_to_evaluation_dataset: bool = True

class ContextHistoryResponse(BaseModel):
    session_id: str
    messages: List[Dict[str, str]]
    total_turns: int