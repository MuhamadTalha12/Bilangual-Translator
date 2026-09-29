import re
from typing import Dict, Any, Set, List, Optional

# Eastern Arabic / Urdu digits to ASCII digits mapping table
URDU_DIGITS_MAP = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')

# Number words mapping for English & Urdu (cardinals, ordinals, financial numbers)
NUMBER_WORD_MAP = {
    "1": ["one", "ek", "ایک", "first", "1st", "یکم"],
    "2": ["two", "twice", "double", "do", "duo", "دوبارہ", "دو", "دفعہ", "دوہری", "second", "2nd", "دو بار"],
    "3": ["three", "teen", "تین", "third", "3rd"],
    "4": ["four", "char", "چار", "fourth", "4th"],
    "5": ["five", "panch", "پانچ", "fifth", "5th"],
    "6": ["six", "chhay", "چھ"],
    "7": ["seven", "saat", "سات"],
    "8": ["eight", "aath", "آٹھ"],
    "9": ["nine", "nau", "نو"],
    "10": ["ten", "das", "دس"],
    "100": ["100", "sau", "سو", "hundred"],
    "500": ["500", "panch sau", "پانچ سو"],
    "1000": ["1k", "1000", "ek hazar", "ایک ہزار", "ہزار", "thousand"],
    "5000": ["5k", "5000", "panj hazar", "panch hazar", "پنج ہزار", "پانچ ہزار"],
    "10000": ["10k", "10000", "das hazar", "دس ہزار"],
    "25000": ["25k", "25000", "pachees hazar", "پچیس ہزار", "twenty five thousand"],
    "50000": ["50k", "50000", "pachaas hazar", "پچاس ہزار", "fifty thousand"],
    "100000": ["100k", "100000", "1 lakh", "ek lakh", "ایک لاکھ", "لاکھ"]
}

class RiskEngine:
    """
    Deterministic validation layer to catch LLM financial hallucinations,
    state inversions, and dropped entities in banking/compliance translations.
    """

    def __init__(self):
        # Base contiguous digits regex and 'k' shorthand
        self.number_pattern = re.compile(r'\b\d+\b')
        self.k_pattern = re.compile(r'(\d+)\s*[kK]\b')

        # State Consistency Patterns (Input)
        self.debit_input_patterns = [
            r'\b(?:kat\s*gaye|cut\s*gaye|nikal\s*gaye|kat\s*gye|kata|kate|deduct|deducted|debited|debit|minus|charged|loss|lost)\b',
            r'(?:کٹ\s*گئے|کٹے|نکل\s*گئے|ڈیبٹ|کٹوتی|منہا)'
        ]
        # Bi-directional output keywords (English & Urdu)
        self.debit_output_keywords = {
            'debit', 'debited', 'deduct', 'deducted', 'deduction', 'withdrawn', 'outflow', 'charged', 'charge', 'cut', 'lost', 'loss',
            'کٹ', 'کٹے', 'ڈیبٹ', 'نکل', 'کٹوتی', 'منہا', 'کم', 'ضائع', 'نقصان'
        }

        self.credit_input_patterns = [
            r'\b(?:credit|credited|jama|reverse|reversed|refund|refunded|deposit|deposited)\b',
            r'(?:ریفنڈ|کریڈٹ|جمع|واپس)'
        ]
        self.credit_output_keywords = {
            'credit', 'credited', 'reverse', 'reversed', 'reversal', 'refund', 'refunded', 'deposit', 'deposited', 'received',
            'ریفنڈ', 'کریڈٹ', 'جمع', 'واپس', 'مصول'
        }

        # Multiplier / Duplicate Charge Patterns (e.g. Foodpanda double deduction)
        # Specifically targeting duplicate deductions or multi-charges
        self.multiplier_input_pattern = re.compile(
            r'\b(?:2\s*dafa|do\s*dafa|twice|double|2\s*times|two\s*times|duplicate)\s*(?:paise|amount|kat|cut|charged|deducted)?\b|(?:دو\s*دفعہ|دو\s*بار|دوہری|دوبارہ\s*(?:پیسے|کٹوتی|کٹ))', 
            re.IGNORECASE
        )
        self.multiplier_output_keywords = {
            'twice', 'duplicate', 'double', 'two times', 'second time', '2 times', 'again', 're-attempt', 're-attempted',
            'دو', 'دوبارہ', 'دفعہ', 'دوہری', 'دو بار', 'دوسری بار'
        }

        # Hardware Jam Patterns (e.g. ATM stuck card / cash entrapment)
        # Strictly require entrapment/jamming verbs — NOT general non-jam machine mentions
        self.hardware_jam_input_pattern = re.compile(
            r'\b(?:phans\s*gaya|phans\s*gayi|phansa|phansi|stuck|trapped|swallowed|jammed|jam|retained|bahir\s*nahi\s*a(?:ya|raha))\b|(?:پھنس\s*گیا|پھنس\s*گئی|پھنسا|پھنس|باہر\s*نہیں\s*آ(?:یا|رہا)|مشین\s*نے\s*رکھ\s*لیا)', 
            re.IGNORECASE
        )
        self.hardware_jam_output_keywords = {
            'stuck', 'trapped', 'jam', 'jammed', 'unresponsive', 'retained', 'swallowed', 'not returned',
            'پھنس', 'پھنسا', 'پھنس گئی', 'مشین', 'باہر نہیں', 'واپس نہیں', 'نہ نکلا'
        }

        # Timeline Patterns
        self.timeline_input_pattern = re.compile(
            r'\b(\d+)\s*(?:din|days|hafta|haftay|week|weeks|ghante|hours)\b',
            re.IGNORECASE
        )

    def normalize_numbers(self, text: str) -> str:
        """Translates Urdu digits to ASCII, strips decimal cents e.g. 5000.00 -> 5000, and formatting commas."""
        if not text:
            return ""
        # 1. Translate Urdu/Eastern-Arabic digits (۰۱۲۳۴۵۶۷۸۹) -> (0123456789)
        text_converted = text.translate(URDU_DIGITS_MAP)
        # 2. Remove formatting commas between digits e.g. 5,000 -> 5000
        text_converted = re.sub(r'(?<=\d),(?=\d)', '', text_converted)
        # 3. Strip trailing currency decimal zeros e.g. 5000.00 or 5000.0 -> 5000
        text_converted = re.sub(r'(?<=\d)\.00?\b', '', text_converted)
        return text_converted

    def extract_numbers(self, text: str) -> Set[str]:
        clean = self.normalize_numbers(text)
        found = set(self.number_pattern.findall(clean))
        # Filter out isolated '00' or '000' fragments from decimal cents
        found = {n for n in found if not (n in ('00', '000') and len(n) > 1)}
        
        # Check for '15k' or '25k' patterns and include both representations
        k_matches = self.k_pattern.findall(clean)
        for k_val in k_matches:
            try:
                expanded = str(int(k_val) * 1000)
                found.add(expanded)
                found.add(k_val)
            except ValueError:
                pass
                
        return found

    def check_state_consistency(self, original_text: str, translated_text: str) -> Dict[str, Any]:
        """Validates that transaction states (debit vs credit) are not inverted or misclassified."""
        orig_lower = original_text.lower()
        trans_lower = translated_text.lower()
        trans_words = set(re.findall(r'\b\w+\b', trans_lower))

        has_debit_input = any(re.search(p, orig_lower) for p in self.debit_input_patterns)
        has_credit_input = any(re.search(p, orig_lower) for p in self.credit_input_patterns)

        has_debit_output = bool(trans_words.intersection(self.debit_output_keywords)) or any(kw in trans_lower for kw in self.debit_output_keywords)
        has_credit_output = bool(trans_words.intersection(self.credit_output_keywords)) or any(kw in trans_lower for kw in self.credit_output_keywords)

        # Check 1A: Severe Inversion (Customer reported ONLY deduction, but output claims funds credited/received)
        if has_debit_input and not has_credit_input and not has_debit_output and has_credit_output:
            if "not credited" not in trans_lower and "نہیں" not in trans_lower and "uncredited" not in trans_lower and "haven't received" not in trans_lower:
                return {
                    "passed": False,
                    "reason": "STATE_INVERSION: Customer reported a deduction/debit, but output states funds were credited/received."
                }

        # Check 1B: Severe Inversion (Customer reported ONLY credit/deposit, but output claims funds debited/deducted)
        if has_credit_input and not has_debit_input and not has_credit_output and has_debit_output:
            if "not debited" not in trans_lower and "نہیں" not in trans_lower and "undebited" not in trans_lower:
                return {
                    "passed": False,
                    "reason": "STATE_INVERSION: Customer reported funds credited/deposited, but output states funds were debited."
                }

        # Check 2: Missing Debit state in financial transaction failure
        if has_debit_input and not has_debit_output:
            if any(term in orig_lower for term in ['transfer', 'pay', 'paid', 'raast', 'foodpanda', 'daraz', 'ٹرانسفر']):
                if not any(k in trans_lower for k in ['debit', 'deduct', 'cut', 'charge', 'lost', 'outflow', 'کٹ', 'منہا', 'نکل']):
                    return {
                        "passed": False,
                        "reason": "STATE_INCOMPLETE: Customer explicitly mentioned funds debited ('cut gaye'), but debit state is missing in compliance output."
                    }

        # Check 3: Multiplier Dropped (e.g. '2 dafa paise kat gaye' -> 'money deducted' without 'duplicate/twice')
        if self.multiplier_input_pattern.search(orig_lower):
            if not any(kw in trans_lower for kw in self.multiplier_output_keywords):
                return {
                    "passed": False,
                    "reason": "MULTIPLIER_DROPPED: Customer reported double deduction ('2 dafa'), but duplicate multiplier was dropped in ticket."
                }

        # Check 4: Hardware Jam misclassified
        if self.hardware_jam_input_pattern.search(orig_lower):
            if not any(kw in trans_lower for kw in self.hardware_jam_output_keywords):
                return {
                    "passed": False,
                    "reason": "HARDWARE_STATE_DROPPED: Customer reported card stuck in ATM machine ('phans gaya'), but stuck/trapped status was omitted."
                }

        return {"passed": True, "reason": "State consistency verified"}

    def evaluate_detailed(
        self,
        original_text: str,
        translated_text: str,
        llm_ambiguous_flag: bool = False,
        confidence_score: Optional[float] = None
    ) -> Dict[str, Any]:
        # Handle API Error strings gracefully
        if "quota limit reached" in translated_text.lower() or "service encountered an error" in translated_text.lower():
            return {
                "status": "HIGH_RISK_SERVICE_ERROR",
                "details": "LLM Service unavailable due to rate limits or API key exhaustion.",
                "original_numbers": [],
                "translated_numbers": [],
                "missing_numbers": []
            }

        original_numbers = self.extract_numbers(original_text)
        translated_numbers = self.extract_numbers(translated_text)
        
        # Rule 1: Ambiguity Gate - Only flag if text is unparseable noise or cutoff
        clean_orig = original_text.strip()
        is_too_short_noise = len(clean_orig) < 3 and not clean_orig.isalnum()
        if llm_ambiguous_flag and is_too_short_noise:
            return {
                "status": "HIGH_RISK_AMBIGUOUS",
                "details": "Input is ambiguous, garbled noise, or impossible to verify.",
                "original_numbers": sorted(list(original_numbers)),
                "translated_numbers": sorted(list(translated_numbers)),
                "missing_numbers": []
            }

        # Rule 2: Model Self-Assessed Confidence Gate (Escalate low-confidence outputs)
        if confidence_score is not None and confidence_score < 0.50:
            return {
                "status": "HIGH_RISK_LOW_CONFIDENCE",
                "details": f"Model confidence score ({confidence_score:.2f}) is below the safety threshold (0.50). Operator review required.",
                "original_numbers": sorted(list(original_numbers)),
                "translated_numbers": sorted(list(translated_numbers)),
                "missing_numbers": []
            }
            
        # Rule 3: Numerical Preservation Gate (Zero tolerance for dropped financial amounts)
        missing_numbers = set()
        trans_lower = translated_text.lower()
        
        # Convert to integer sets for robust numerical comparison (e.g. 05000 vs 5000)
        trans_ints = {int(n) for n in translated_numbers if n.isdigit()}

        for num in original_numbers:
            if not num.isdigit():
                continue
            num_int = int(num)
            
            # Check 1: Direct integer match in translated numbers
            if num_int in trans_ints:
                continue
                
            # Check 2: Shorthand 'k' expansion (e.g. 25k -> 25000)
            if num_int < 1000 and (num_int * 1000) in trans_ints:
                continue
            if num_int >= 1000 and (num_int // 1000) in trans_ints and num_int % 1000 == 0:
                continue

            # Check 3: Word equivalents (e.g. 5000 -> 'panch hazar' / 'پانچ ہزار')
            if num in NUMBER_WORD_MAP:
                words = NUMBER_WORD_MAP[num]
                if any(w.lower() in trans_lower for w in words):
                    continue

            missing_numbers.add(num)

        if missing_numbers:
            return {
                "status": "HIGH_RISK_NUMBER_MISMATCH",
                "details": f"Missing critical financial identifiers/amounts: {', '.join(sorted(list(missing_numbers)))}",
                "original_numbers": sorted(list(original_numbers)),
                "translated_numbers": sorted(list(translated_numbers)),
                "missing_numbers": sorted(list(missing_numbers))
            }

        # Rule 4: Deterministic Financial State Consistency Gate
        state_check = self.check_state_consistency(original_text, translated_text)
        if not state_check["passed"]:
            return {
                "status": "HIGH_RISK_STATE_INCONSISTENCY",
                "details": state_check["reason"],
                "original_numbers": sorted(list(original_numbers)),
                "translated_numbers": sorted(list(translated_numbers)),
                "missing_numbers": []
            }
            
        # Passed All Deterministic Verification Layers
        return {
            "status": "LOW_RISK_APPROVED",
            "details": "All numerical entities, multipliers, and financial transaction states verified.",
            "original_numbers": sorted(list(original_numbers)),
            "translated_numbers": sorted(list(translated_numbers)),
            "missing_numbers": []
        }

    def evaluate(
        self,
        original_text: str,
        translated_text: str,
        llm_ambiguous_flag: bool = False,
        confidence_score: Optional[float] = None
    ) -> str:
        result = self.evaluate_detailed(original_text, translated_text, llm_ambiguous_flag, confidence_score)
        return result["status"]

    def get_crawl_report(
        self,
        original_text: str,
        translated_text: str,
        eval_ms: float = 0.0,
        llm_ambiguous_flag: bool = False,
        confidence_score: Optional[float] = None
    ) -> Dict[str, Any]:
        detailed = self.evaluate_detailed(original_text, translated_text, llm_ambiguous_flag, confidence_score)
        passed = (detailed["status"] == "LOW_RISK_APPROVED")
        missing_numbers = detailed.get("missing_numbers", [])
        
        return {
            "stage": "CRAWL",
            "passed": passed,
            "status": detailed["status"],
            "details": detailed["details"],
            "checks": {
                "entity_preservation": len(missing_numbers) == 0,
                "state_consistency": "STATE" not in detailed["status"],
                "multiplier_retention": "MULTIPLIER" not in detailed.get("details", ""),
                "hardware_jam_integrity": "HARDWARE" not in detailed.get("details", "")
            },
            "latency_ms": eval_ms,
            "original_numbers": detailed.get("original_numbers", []),
            "translated_numbers": detailed.get("translated_numbers", []),
            "missing_numbers": missing_numbers
        }