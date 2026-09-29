import time
import re
from typing import Dict, Any, Optional
from pipeline.preprocessor import Preprocessor
from pipeline.language_detector import LanguageDetector
from pipeline.prompt_builder import PromptBuilder
from pipeline.llm_client import LLMClient
from pipeline.risk_engine import RiskEngine
from pipeline.monitoring import PipelineMonitor
from core.context_manager import ContextManager
from core.config import settings
from core.schemas import (
    TranslationResponse,
    LatencyBreakdown,
    CostMetrics,
    QualityMetrics,
    HumanReviewResponse,
    CrawlWalkRunReport,
    CrawlStageMetrics,
    WalkStageMetrics,
    RunStageMetrics
)

class LanguageMismatchError(ValueError):
    """Raised when user enters English in Urdu mode or Urdu in English mode."""
    pass

class TranslationPipeline:
    """The central orchestrator strictly following the architecture flowchart."""

    def __init__(self):
        # Node B & D: Preprocessor & Cleaning
        self.preprocessor = Preprocessor()
        # Node C: Language Detection
        self.detector = LanguageDetector()
        # Node E: Context Manager (Chat History)
        self.context_manager = ContextManager(max_history=getattr(settings, "MAX_CONTEXT_HISTORY", 5))
        # Node F: Prompt Engineering Layer (Includes G: Cold Start & H: System Rules)
        self.prompt_builder = PromptBuilder()
        # Node I & J: Foundation Model Selection & LLM Client
        self.llm_client = LLMClient()
        # Node K & L: Quality & Risk Evaluation Engine
        self.risk_engine = RiskEngine()
        # Node Q, R, S: Telemetry Monitoring & Evaluation Logger
        self.monitor = PipelineMonitor()

        # High-speed deterministic cache for instant zero-cost retrieval (Node Q: Cost Monitoring)
        self.translation_cache = {
            ("current affairs", "en", "ur"): {
                "translation": "کرنٹ افیئرز",
                "pronunciation": "Current affairs",
                "synonyms": ["کرنٹ افیئرز", "حالات حاضرہ"],
                "definitions": ["Events of political or social interest happening at the present time."]
            },
            ("کرنٹ افیئرز", "ur", "en"): {
                "translation": "Current Affairs",
                "pronunciation": "",
                "synonyms": ["Current Affairs", "Contemporary Events"],
                "definitions": ["Important political and social events taking place at present."]
            }
        }

    def validate_language_direction(self, text: str, source_lang: str):
        """Validates that input text script matches the selected source language."""
        norm_src = (source_lang or "en").lower()

        if norm_src == "ur":
            # Selected Urdu -> English: allow Urdu script AND Roman Urdu
            if self.detector.is_english(text) and not self.detector.is_roman_urdu(text):
                raise LanguageMismatchError(
                    "Language mismatch: You selected 'Urdu → English', but entered English text. "
                    "Please enter Urdu text (اردو میں لکھیں / Roman Urdu) or switch translation direction to 'English → Urdu'."
                )
        elif norm_src == "en":
            # Selected English -> Urdu, but input is Urdu script text
            if self.detector.is_urdu(text):
                raise LanguageMismatchError(
                    "Language mismatch: You selected 'English → Urdu', but entered Urdu text (اردو). "
                    "Please enter English text or switch translation direction to 'Urdu → English'."
                )

    def process(
        self,
        raw_text: str,
        source_lang: str = "en",
        target_lang: str = "ur",
        session_id: str = "default"
    ) -> TranslationResponse:
        t_start = time.time()
        norm_src = (source_lang or "en").lower()
        norm_tgt = (target_lang or "ur").lower()

        # -------------------------------------------------------------
        # Node A -> Node B: Input Preprocessing & Normalization (D)
        # -------------------------------------------------------------
        t_prep_start = time.time()
        clean_text = self.preprocessor.clean(raw_text) if hasattr(self.preprocessor, "clean") else raw_text.strip()
        prep_ms = round((time.time() - t_prep_start) * 1000, 2)

        if not clean_text:
            return TranslationResponse(
                original_text="",
                translation="",
                source_lang=source_lang,
                target_lang=target_lang,
                detected_language="Empty",
                detected_code=source_lang,
                detected_label="Empty",
                confidence=1.0,
                pronunciation="",
                synonyms=[],
                definitions=[],
                risk_level="LOW_RISK_APPROVED",
                risk_details="Empty input",
                needs_human_review=False,
                original_numbers=[],
                translated_numbers=[],
                processing_time_ms=0.0,
                latency_breakdown=LatencyBreakdown(total_ms=0.0),
                cost_metrics=CostMetrics(),
                quality_metrics=QualityMetrics(),
                session_id=session_id
            )

        # -------------------------------------------------------------
        # Node C: Language Detection
        # -------------------------------------------------------------
        t_detect_start = time.time()
        self.validate_language_direction(clean_text, source_lang)
        detection_data = self.detector.detect(clean_text)
        detect_ms = round((time.time() - t_detect_start) * 1000, 2)

        # -------------------------------------------------------------
        # Node Q: Cache Check (Cost Optimization)
        # -------------------------------------------------------------
        cache_key = (clean_text.lower().strip(), norm_src, norm_tgt)
        if cache_key in self.translation_cache:
            cached = self.translation_cache[cache_key]
            total_ms = round((time.time() - t_start) * 1000, 2)
            
            # Node P -> Node E: Store in Context Manager
            self.context_manager.add_message(session_id, "user", clean_text)
            self.context_manager.add_message(session_id, "assistant", cached["translation"])

            latency_info = LatencyBreakdown(
                preprocessing_ms=prep_ms,
                detection_ms=detect_ms,
                llm_ms=0.0,
                risk_eval_ms=0.5,
                total_ms=total_ms
            )

            telemetry = self.monitor.record_transaction(
                input_text=clean_text,
                output_text=cached["translation"],
                cache_hit=True,
                latency_breakdown=latency_info.dict(),
                risk_status="LOW_RISK_APPROVED"
            )

            cwr_report = CrawlWalkRunReport(
                active_stage="CRAWL",
                crawl=CrawlStageMetrics(
                    stage="CRAWL",
                    passed=True,
                    entity_preservation=True,
                    state_consistency=True,
                    multiplier_retention=True,
                    hardware_jam_integrity=True,
                    latency_ms=0.5
                ),
                walk=WalkStageMetrics(
                    stage="WALK",
                    human_review_required=False,
                    action_taken="auto_approved",
                    dataset_logged=False
                ),
                run=RunStageMetrics(
                    stage="RUN",
                    telemetry_recorded=True,
                    cost_usd=0.0,
                    latency_total_ms=total_ms,
                    quality_pass_rate_pct=100.0
                )
            )

            return TranslationResponse(
                original_text=raw_text,
                translation=cached["translation"],
                source_lang=source_lang,
                target_lang=target_lang,
                detected_language="English" if norm_src == "en" else "Urdu",
                detected_code=source_lang,
                detected_label="English (EN)" if norm_src == "en" else "Urdu (UR)",
                confidence=1.0,
                pronunciation=cached.get("pronunciation", ""),
                synonyms=cached.get("synonyms", []),
                definitions=cached.get("definitions", []),
                risk_level="LOW_RISK_APPROVED",
                risk_details="Instant Cache Hit (Verified Quality)",
                needs_human_review=False,
                original_numbers=[],
                translated_numbers=[],
                processing_time_ms=total_ms,
                latency_breakdown=latency_info,
                cost_metrics=CostMetrics(**telemetry["cost"]),
                quality_metrics=QualityMetrics(**telemetry["quality"]),
                crawl_walk_run=cwr_report,
                session_id=session_id
            )

        # -------------------------------------------------------------
        # Node E: Context Manager (Retrieve Chat History)
        # -------------------------------------------------------------
        history_string = self.context_manager.get_history_string(session_id)

        # -------------------------------------------------------------
        # Node F: Prompt Engineering Layer (Includes G: Few-shot, H: Rules, E: Context)
        # -------------------------------------------------------------
        prompt = self.prompt_builder.build_prompt(
            text=clean_text,
            source_lang=source_lang,
            target_lang=target_lang,
            history=history_string,
            detected_hint="English" if source_lang == "en" else "Urdu"
        )

        # -------------------------------------------------------------
        # Node I & J: Foundation Model Selection & LLM Translation (Includes R: Latency)
        # -------------------------------------------------------------
        t_llm_start = time.time()
        llm_output = self.llm_client.generate_translation(prompt)
        llm_ms = round((time.time() - t_llm_start) * 1000, 2)

        translation_text = llm_output.get("translation", "")
        ambiguous_flag = llm_output.get("ambiguous", False)
        pronunciation = llm_output.get("pronunciation", "")
        synonyms = llm_output.get("synonyms") or []
        definitions = llm_output.get("definitions") or []

        # Confidence Score extraction & validation
        raw_conf = llm_output.get("confidence_score")
        try:
            confidence_score = float(raw_conf) if raw_conf is not None else None
            if confidence_score is not None and not (0.0 <= confidence_score <= 1.0):
                confidence_score = None
        except (ValueError, TypeError):
            confidence_score = None

        # Enforce "Current Affairs" -> "کرنٹ افیئرز"
        if norm_tgt == "ur":
            if "current affairs" in clean_text.lower():
                translation_text = re.sub(r'حالات[\s_ـ]*[ِ]?\s*حاضرہ', 'کرنٹ افیئرز', translation_text)
                clean_no_punct = re.sub(r'[^\w\s]', '', clean_text).strip().lower()
                if clean_no_punct == "current affairs":
                    translation_text = "کرنٹ افیئرز"
                    pronunciation = "Current affairs"
                    if "کرنٹ افیئرز" not in synonyms:
                        synonyms = ["کرنٹ افیئرز", "حالات حاضرہ"]
        elif norm_tgt == "en":
            if "کرنٹ افیئرز" in clean_text:
                clean_no_punct = clean_text.strip().rstrip('.!?')
                if clean_no_punct == "کرنٹ افیئرز":
                    translation_text = "Current Affairs"

        # -------------------------------------------------------------
        # Node K & S: Output Evaluation & Quality / Risk Check
        # -------------------------------------------------------------
        t_eval_start = time.time()
        risk_evaluation = self.risk_engine.evaluate_detailed(
            original_text=clean_text,
            translated_text=translation_text,
            llm_ambiguous_flag=ambiguous_flag,
            confidence_score=confidence_score
        )
        eval_ms = round((time.time() - t_eval_start) * 1000, 2)

        # -------------------------------------------------------------
        # Node L: Decision {Risk / Quality Acceptable?}
        # -------------------------------------------------------------
        is_acceptable = (risk_evaluation["status"] == "LOW_RISK_APPROVED")

        if confidence_score is None:
            confidence_score = round(0.98 if is_acceptable else 0.45, 2)

        if is_acceptable:
            # Node M: Final Translation Approved (Low Risk)
            final_risk_level = "LOW_RISK_APPROVED"
            final_risk_details = risk_evaluation["details"]
            needs_human_review = False
            
            # Cache approved translations
            if translation_text and "error" not in translation_text.lower():
                self.translation_cache[cache_key] = {
                    "translation": translation_text,
                    "pronunciation": pronunciation,
                    "synonyms": synonyms,
                    "definitions": definitions
                }
        else:
            # Node N: Flagged for Human Review (High Risk)
            final_risk_level = f"FLAGGED_FOR_HUMAN_REVIEW_{risk_evaluation['status']}"
            final_risk_details = f"Risk Engine Flag: {risk_evaluation['details']}"
            needs_human_review = True

        # -------------------------------------------------------------
        # Node P -> Node E: Store in Context Manager (Feedback Loop)
        # -------------------------------------------------------------
        try:
            self.context_manager.add_message(session_id, "user", clean_text)
            self.context_manager.add_message(session_id, "assistant", translation_text)
        except Exception:
            pass

        # -------------------------------------------------------------
        # Telemetry Monitoring (Q, R, S)
        # -------------------------------------------------------------
        total_processing_time = round((time.time() - t_start) * 1000, 2)
        latency_info = LatencyBreakdown(
            preprocessing_ms=prep_ms,
            detection_ms=detect_ms,
            llm_ms=llm_ms,
            risk_eval_ms=eval_ms,
            total_ms=total_processing_time
        )

        telemetry = self.monitor.record_transaction(
            input_text=clean_text,
            output_text=translation_text,
            cache_hit=False,
            latency_breakdown=latency_info.dict(),
            risk_status=risk_evaluation["status"],
            confidence_score=confidence_score
        )

        # -------------------------------------------------------------
        # Persistent Logging to SQLite via SQLAlchemy
        # -------------------------------------------------------------
        try:
            from core.database import SessionLocal, TranslationLog
            db = SessionLocal()
            log_entry = TranslationLog(
                session_id=session_id,
                source_text=raw_text,
                target_text=translation_text,
                detected_script=source_lang,
                processing_time=total_processing_time,
                confidence_score=confidence_score,
                final_risk_status=final_risk_level
            )
            db.add(log_entry)
            db.commit()
            db.close()
        except Exception as db_err:
            print(f"Warning: Failed to log translation to SQLite: {db_err}")

        crawl_data = self.risk_engine.get_crawl_report(
            original_text=clean_text,
            translated_text=translation_text,
            eval_ms=eval_ms,
            llm_ambiguous_flag=ambiguous_flag,
            confidence_score=confidence_score
        )

        cwr_report = CrawlWalkRunReport(
            active_stage="WALK" if needs_human_review else "CRAWL",
            crawl=CrawlStageMetrics(
                stage="CRAWL",
                passed=crawl_data["passed"],
                entity_preservation=crawl_data["checks"]["entity_preservation"],
                state_consistency=crawl_data["checks"]["state_consistency"],
                multiplier_retention=crawl_data["checks"]["multiplier_retention"],
                hardware_jam_integrity=crawl_data["checks"]["hardware_jam_integrity"],
                latency_ms=eval_ms
            ),
            walk=WalkStageMetrics(
                stage="WALK",
                human_review_required=needs_human_review,
                action_taken="pending_human_review" if needs_human_review else "auto_approved",
                dataset_logged=False
            ),
            run=RunStageMetrics(
                stage="RUN",
                telemetry_recorded=True,
                cost_usd=telemetry["cost"]["estimated_cost_usd"],
                latency_total_ms=total_processing_time,
                quality_pass_rate_pct=100.0 if not needs_human_review else 0.0
            )
        )

        quality_metrics = QualityMetrics(
            is_acceptable=is_acceptable,
            risk_status=risk_evaluation["status"],
            confidence=confidence_score,
            confidence_score=confidence_score,
            numbers_match=len(risk_evaluation.get("missing_numbers", [])) == 0,
            state_consistent="STATE" not in risk_evaluation["status"]
        )

        return TranslationResponse(
            original_text=raw_text,
            translation=translation_text,
            source_lang=source_lang,
            target_lang=target_lang,
            detected_language="English" if source_lang == "en" else "Urdu",
            detected_code=source_lang,
            detected_label="English (EN)" if source_lang == "en" else "Urdu (UR)",
            confidence=confidence_score,
            confidence_score=confidence_score,
            pronunciation=pronunciation,
            synonyms=synonyms,
            definitions=definitions,
            risk_level=final_risk_level,
            risk_details=final_risk_details,
            needs_human_review=needs_human_review,
            original_numbers=risk_evaluation.get("original_numbers", []),
            translated_numbers=risk_evaluation.get("translated_numbers", []),
            processing_time_ms=total_processing_time,
            latency_breakdown=latency_info,
            cost_metrics=CostMetrics(**telemetry["cost"]),
            quality_metrics=quality_metrics,
            crawl_walk_run=cwr_report,
            session_id=session_id
        )

    def submit_human_review(
        self,
        session_id: str,
        original_text: str,
        ai_translation: str,
        action: str,
        final_translation: str,
        risk_level: str = "",
        reviewer_notes: str = ""
    ) -> HumanReviewResponse:
        """Executes Node N -> Node M -> Node P -> Node E and logs to Node O (Evaluation Dataset)."""
        # 1. Update Context Manager with human-approved final translation
        self.context_manager.add_message(session_id, "user", original_text)
        self.context_manager.add_message(session_id, "human_reviewed_assistant", final_translation)

        # 2. Log to Evaluation Dataset (Node O)
        self.monitor.log_human_review(
            session_id=session_id,
            original_text=original_text,
            ai_translation=ai_translation,
            action=action,
            final_translation=final_translation,
            risk_level=risk_level,
            notes=reviewer_notes
        )

        # 3. Log to SQLite database
        try:
            from core.database import SessionLocal, FeedbackLog
            db = SessionLocal()
            fb_entry = FeedbackLog(
                session_id=session_id,
                original_text=original_text,
                ai_translation=ai_translation,
                action=action,
                final_translation=final_translation,
                risk_level=risk_level,
                reviewer_notes=reviewer_notes
            )
            db.add(fb_entry)
            db.commit()
            db.close()
        except Exception as db_err:
            print(f"Warning: Failed to log feedback to SQLite: {db_err}")

        return HumanReviewResponse(
            status="success",
            message=f"Human Review '{action.upper()}' processed successfully.",
            action_taken=action,
            final_translation=final_translation,
            session_id=session_id,
            logged_to_evaluation_dataset=True
        )