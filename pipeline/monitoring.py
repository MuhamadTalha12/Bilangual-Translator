import os
import json
import time
from typing import Dict, Any, List

class PipelineMonitor:
    """Manages Telemetry for Cost (Q), Latency (R), and Quality (S) according to the architecture flowchart."""

    def __init__(self, dataset_path: str = "data/evaluation_dataset.json"):
        self.dataset_path = dataset_path
        self.total_requests = 0
        self.cache_hits = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.cumulative_cost_usd = 0.0
        
        self.low_risk_count = 0
        self.high_risk_count = 0
        self.human_review_count = 0
        
        self.recent_latencies: List[float] = []
        self.recent_confidences: List[float] = []

    def estimate_tokens(self, text: str) -> int:
        """Approximates token count (avg 3.8 characters per token for mixed English/Urdu)."""
        if not text:
            return 0
        return max(1, int(len(text) / 3.8))

    def record_transaction(
        self,
        input_text: str,
        output_text: str,
        cache_hit: bool,
        latency_breakdown: Dict[str, float],
        risk_status: str,
        confidence_score: float = 1.0
    ) -> Dict[str, Any]:
        self.total_requests += 1

        in_tokens = self.estimate_tokens(input_text)
        out_tokens = self.estimate_tokens(output_text)

        if cache_hit:
            self.cache_hits += 1
            cost = 0.0
        else:
            self.total_input_tokens += in_tokens
            self.total_output_tokens += out_tokens
            # Gemini 1.5/3.5 Flash pricing: ~$0.075 per 1M input, ~$0.30 per 1M output tokens
            cost = (in_tokens * 0.000000075) + (out_tokens * 0.00000030)
            self.cumulative_cost_usd += cost

        # Latency & Confidence
        total_lat = latency_breakdown.get("total_ms", 0.0)
        self.recent_latencies.append(total_lat)
        if len(self.recent_latencies) > 100:
            self.recent_latencies.pop(0)

        self.recent_confidences.append(confidence_score)
        if len(self.recent_confidences) > 100:
            self.recent_confidences.pop(0)

        # Quality & Risk
        is_low_risk = (risk_status == "LOW_RISK_APPROVED")
        if is_low_risk:
            self.low_risk_count += 1
        else:
            self.high_risk_count += 1

        avg_latency = round(sum(self.recent_latencies) / len(self.recent_latencies), 2) if self.recent_latencies else 0.0
        avg_confidence = round(sum(self.recent_confidences) / len(self.recent_confidences), 4) if self.recent_confidences else 1.0
        cache_hit_rate = round((self.cache_hits / self.total_requests) * 100, 1) if self.total_requests else 0.0
        quality_pass_rate = round((self.low_risk_count / self.total_requests) * 100, 1) if self.total_requests else 100.0

        return {
            "cost": {
                "input_tokens": in_tokens,
                "output_tokens": out_tokens,
                "total_tokens": in_tokens + out_tokens,
                "estimated_cost_usd": round(cost, 6),
                "cache_hit": cache_hit,
                "cache_hit_rate_pct": cache_hit_rate,
                "cumulative_cost_usd": round(self.cumulative_cost_usd, 6)
            },
            "latency": {
                "breakdown": latency_breakdown,
                "rolling_avg_ms": avg_latency
            },
            "quality": {
                "risk_status": risk_status,
                "is_acceptable": is_low_risk,
                "confidence": confidence_score,
                "confidence_score": confidence_score,
                "avg_confidence": avg_confidence,
                "total_processed": self.total_requests,
                "quality_pass_rate_pct": quality_pass_rate
            }
        }

    def log_human_review(
        self,
        session_id: str,
        original_text: str,
        ai_translation: str,
        action: str,
        final_translation: str,
        risk_level: str,
        notes: str = ""
    ) -> Dict[str, Any]:
        """Appends human-reviewed correction to the Evaluation Dataset (Node N -> Node O)."""
        self.human_review_count += 1
        record = {
            "timestamp": time.time(),
            "session_id": session_id,
            "original_text": original_text,
            "ai_translation": ai_translation,
            "human_action": action,
            "final_translation": final_translation,
            "original_risk_level": risk_level,
            "reviewer_notes": notes
        }

        try:
            if os.path.exists(self.dataset_path):
                with open(self.dataset_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {"benchmark_cases": [], "human_reviewed_samples": []}

            if "human_reviewed_samples" not in data:
                data["human_reviewed_samples"] = []

            data["human_reviewed_samples"].append(record)

            with open(self.dataset_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"Warning: Could not write to evaluation dataset: {e}")

        return record

    def get_system_metrics(self) -> Dict[str, Any]:
        """Returns snapshot of current Cost, Latency, and Quality metrics."""
        avg_lat = round(sum(self.recent_latencies) / len(self.recent_latencies), 2) if self.recent_latencies else 0.0
        hit_rate = round((self.cache_hits / self.total_requests) * 100, 1) if self.total_requests else 0.0
        pass_rate = round((self.low_risk_count / self.total_requests) * 100, 1) if self.total_requests else 100.0

        return {
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "cache_hit_rate_pct": hit_rate,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "cumulative_cost_usd": round(self.cumulative_cost_usd, 6),
            "rolling_avg_latency_ms": avg_lat,
            "low_risk_count": self.low_risk_count,
            "high_risk_count": self.high_risk_count,
            "human_review_count": self.human_review_count,
            "quality_pass_rate_pct": pass_rate
        }
