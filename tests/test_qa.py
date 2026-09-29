import pytest
import json
import os
import sacrebleu
from fastapi.testclient import TestClient
from main import app
from pipeline.orchestrator import TranslationPipeline
from core.database import SessionLocal, TranslationLog, FeedbackLog, init_db

# Initialize database for test suite
init_db()
client = TestClient(app)

# The 7 Frozen Golden Benchmark Scenarios
FROZEN_GOLDEN_SCENARIOS = [
    {
        "id": "atm_hardware_failure",
        "category": "ATM Hardware Failure",
        "input": "Bhai ATM me card dala tha chal nahi raha, wahi phans gaya hai.",
        "source_lang": "ur",
        "target_lang": "en",
        "target_ticket": "Customer inserted credit card into the ATM machine; the card is currently stuck and the machine is unresponsive.",
        "required_entities": ["ATM", "stuck"]
    },
    {
        "id": "failed_raast_transfer",
        "category": "Failed Transfer",
        "input": "Mera Raast transfer fail ho gaya, account se 5000 cut gaye par dost ko nahi mile.",
        "source_lang": "ur",
        "target_lang": "en",
        "target_ticket": "Customer reports failed Raast transfer of PKR 5000. Funds debited from sender account but not credited to beneficiary.",
        "required_entities": ["5000", "Raast", "debited"]
    },
    {
        "id": "double_deduction",
        "category": "Double Deduction",
        "input": "Maine foodpanda pe pay kiya, error aya toh dobara kiya, ab 2 dafa paise kat gaye hain.",
        "source_lang": "ur",
        "target_lang": "en",
        "target_ticket": "Customer experienced a payment gateway error on Foodpanda resulting in a duplicate charge; funds deducted twice.",
        "required_entities": ["Foodpanda", "twice"]
    },
    {
        "id": "app_crash_pending",
        "category": "App Crash / Timeout",
        "input": "Payment process ho rahi thi aur app achanak band ho gayi, ab status pending hai.",
        "source_lang": "ur",
        "target_lang": "en",
        "target_ticket": "Application crashed during payment processing; transaction status is currently pending.",
        "required_entities": ["pending"]
    },
    {
        "id": "unauthorized_fraud",
        "category": "Unauthorized Fraud",
        "input": "Mujhe OTP ka message aya aur foran 25k nikal gaye halanke maine koi transaction nahi ki.",
        "source_lang": "ur",
        "target_lang": "en",
        "target_ticket": "Customer reports unauthorized transaction of PKR 25,000 immediately following an OTP SMS. Fraud suspected.",
        "required_entities": ["25000", "OTP"]
    },
    {
        "id": "biometric_lockout",
        "category": "Biometric Lockout",
        "input": "Mera thumbprint accept nahi ho raha pichle 3 din se, account locked aa raha hai.",
        "source_lang": "ur",
        "target_lang": "en",
        "target_ticket": "Customer unable to authenticate via biometrics for the past 3 days; account is currently locked.",
        "required_entities": ["3 days", "locked"]
    },
    {
        "id": "refund_delay",
        "category": "Refund Delay",
        "input": "Daraz ki refund request ki thi 1 hafta pehle, abhi tak reverse nahi hui amount.",
        "source_lang": "ur",
        "target_lang": "en",
        "target_ticket": "Customer initiated a refund request with Daraz 1 week ago; amount reversal is still pending.",
        "required_entities": ["1 week", "Daraz"]
    }
]


def calculate_bleu(hypothesis: str, reference: str) -> float:
    """Calculates BLEU score (0.0 to 100.0) comparing hypothesis against reference."""
    try:
        score = sacrebleu.sentence_bleu(hypothesis, [reference]).score
        return round(score, 2)
    except Exception:
        return 0.0


def calculate_chrf(hypothesis: str, reference: str) -> float:
    """Calculates chrF character n-gram F-score (0.0 to 100.0)."""
    try:
        score = sacrebleu.sentence_chrf(hypothesis, [reference]).score
        return round(score, 2)
    except Exception:
        return 0.0


def calculate_ter(hypothesis: str, reference: str) -> float:
    """Calculates Translation Edit Rate (TER = word edit distance / reference word count)."""
    hyp_words = hypothesis.strip().split()
    ref_words = reference.strip().split()
    if not ref_words:
        return 0.0
    
    d = [[0] * (len(ref_words) + 1) for _ in range(len(hyp_words) + 1)]
    for i in range(len(hyp_words) + 1):
        d[i][0] = i
    for j in range(len(ref_words) + 1):
        d[0][j] = j
        
    for i in range(1, len(hyp_words) + 1):
        for j in range(1, len(ref_words) + 1):
            cost = 0 if hyp_words[i - 1].lower() == ref_words[j - 1].lower() else 1
            d[i][j] = min(
                d[i - 1][j] + 1,       # deletion
                d[i][j - 1] + 1,       # insertion
                d[i - 1][j - 1] + cost # substitution
            )
            
    edit_distance = d[len(hyp_words)][len(ref_words)]
    return round(edit_distance / len(ref_words), 4)


class TestQualityAssuranceSuite:
    """
    Automated Evaluation Suite testing the Bilangual AI translation system
    against the 7 Frozen Golden Benchmark Scenarios.
    """

    @pytest.fixture(autouse=True)
    def setup_pipeline(self):
        self.pipeline = TranslationPipeline()

    def test_7_frozen_golden_benchmark_scenarios(self):
        """Programmatically runs system against all 7 golden scenarios & evaluates BLEU, chrF, TER."""
        results = []
        
        for scenario in FROZEN_GOLDEN_SCENARIOS:
            sc_id = scenario["id"]
            user_input = scenario["input"]
            target_ticket = scenario["target_ticket"]
            
            # Execute pipeline translation
            response = self.pipeline.process(
                raw_text=user_input,
                source_lang=scenario["source_lang"],
                target_lang=scenario["target_lang"],
                session_id=f"qa_test_{sc_id}"
            )
            
            translation = response.translation
            conf_score = response.confidence_score
            
            # Compute evaluation metrics
            bleu_score = calculate_bleu(translation, target_ticket)
            chrf_score = calculate_chrf(translation, target_ticket)
            ter_score = calculate_ter(translation, target_ticket)
            
            results.append({
                "id": sc_id,
                "category": scenario["category"],
                "bleu": bleu_score,
                "chrf": chrf_score,
                "ter": ter_score,
                "confidence_score": conf_score,
                "risk_level": response.risk_level
            })
            
            # Assert response structure & confidence score range
            assert response.translation is not None and len(response.translation) > 0
            assert 0.0 <= conf_score <= 1.0
            assert response.processing_time_ms > 0.0

        # Print detailed QA benchmark evaluation report
        print("\n" + "=" * 80)
        print("  BILANGUAL QA EVALUATION REPORT - 7 FROZEN GOLDEN BENCHMARK SCENARIOS")
        print("=" * 80)
        print(f"{'Scenario ID':<25} | {'BLEU':<7} | {'chrF':<7} | {'TER':<7} | {'Confidence':<10} | {'Risk Level'}")
        print("-" * 80)
        for r in results:
            print(f"{r['id']:<25} | {r['bleu']:<7.2f} | {r['chrf']:<7.2f} | {r['ter']:<7.4f} | {r['confidence_score']:<10.2f} | {r['risk_level']}")
        print("=" * 80 + "\n")

    def test_feedback_api_endpoint(self):
        """Tests Requirement 1 Deliverable: POST /api/v1/feedback."""
        payload = {
            "session_id": "qa_feedback_sess_1",
            "original_text": "Mera Raast transfer fail ho gaya 5000 rupees",
            "ai_translation": "Raast transfer failed 5000 rupees.",
            "action": "correct",
            "final_translation": "Customer reports failed Raast transfer of PKR 5000. Funds debited from account.",
            "risk_level": "FLAGGED_FOR_HUMAN_REVIEW_HIGH_RISK_NUMBER_MISMATCH",
            "reviewer_notes": "Corrected by QA automated test suite."
        }
        
        res = client.post("/api/v1/feedback", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["action_taken"] == "correct"
        assert data["final_translation"] == payload["final_translation"]

    def test_sqlite_history_logging(self):
        """Tests Requirement 2 Deliverable: SQLite history logging via SQLAlchemy."""
        session_id = "qa_sqlite_test_sess"
        
        # Trigger translation to write SQLite log
        res = client.post("/api/v1/translate", json={
            "text": "Bhai ATM me card dala tha chal nahi raha",
            "source_lang": "ur",
            "target_lang": "en",
            "session_id": session_id
        })
        assert res.status_code == 200
        
        # Query /api/v1/history endpoint to verify SQLite record
        hist_res = client.get(f"/api/v1/history?session_id={session_id}")
        assert hist_res.status_code == 200
        history = hist_res.json()
        assert len(history) > 0
        latest = history[0]
        assert latest["session_id"] == session_id
        assert "ATM" in latest["source_text"]
        assert 0.0 <= latest["confidence_score"] <= 1.0

    def test_prometheus_metrics_endpoint(self):
        """Tests Requirement 4 Deliverable: FastAPI /metrics endpoint."""
        res = client.get("/metrics")
        assert res.status_code == 200
        assert "http_requests_total" in res.text or "process_cpu_seconds_total" in res.text
