import re
from typing import Dict, Any

class LanguageDetector:
    """
    Lightweight, high-precision script detector for bidirectional English <-> Urdu translation.
    Detects whether input text is written in Urdu (Arabic/Nastaliq script) or English (Latin script).
    """

    def __init__(self):
        # Urdu / Arabic Unicode script range:
        # Standard Arabic: \u0600-\u06FF
        # Arabic Supplement: \u0750-\u077F
        # Arabic Presentation Forms-A: \uFB50-\uFDFF
        # Arabic Presentation Forms-B: \uFE70-\uFEFF
        self.urdu_script_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]')
        self.en_script_pattern = re.compile(r'[a-zA-Z]')

    ROMAN_URDU_KEYWORDS = {
        'hai', 'hain', 'tha', 'thi', 'the', 'kya', 'kiya', 'gaya', 'gayi', 'gaye',
        'nahi', 'nahin', 'aur', 'par', 'pe', 'mein', 'me', 'se', 'mera', 'meri',
        'mere', 'mujhe', 'hum', 'humein', 'bhai', 'bhaiya', 'kal', 'aj', 'aaj',
        'kat', 'cut', 'pese', 'paise', 'karo', 'karein', 'apke', 'aapke', 'hua', 'hui',
        'phans', 'raast', 'daraz', 'pay', 'dobara', 'nikal', 'hafta', 'dafa'
    }

    def is_urdu(self, text: str) -> bool:
        """Returns True if the text contains predominantly Urdu / Arabic script characters."""
        if not text:
            return False
        urdu_chars = len(self.urdu_script_pattern.findall(text))
        en_chars = len(self.en_script_pattern.findall(text))
        return urdu_chars > 0 and urdu_chars >= en_chars

    def is_roman_urdu(self, text: str) -> bool:
        """Returns True if Latin-script text contains Roman Urdu keywords."""
        if not text:
            return False
        words = set(re.findall(r'\b\w+\b', text.lower()))
        return bool(words.intersection(self.ROMAN_URDU_KEYWORDS))

    def is_english(self, text: str) -> bool:
        """Returns True if the text contains predominantly English / Latin alphabet characters."""
        if not text:
            return False
        urdu_chars = len(self.urdu_script_pattern.findall(text))
        en_chars = len(self.en_script_pattern.findall(text))
        return en_chars > 0 and en_chars > urdu_chars

    def detect(self, text: str) -> Dict[str, Any]:
        """
        Analyzes the text and returns language detection metadata.
        Returns:
            dict: {
                "language": "Urdu" | "English",
                "code": "ur" | "en",
                "confidence": float,
                "label": "Urdu" | "English"
            }
        """
        if not text or not text.strip():
            return {
                "language": "English",
                "code": "en",
                "confidence": 1.0,
                "label": "English"
            }

        stripped = text.strip()
        urdu_chars = len(self.urdu_script_pattern.findall(stripped))
        en_chars = len(self.en_script_pattern.findall(stripped))

        if urdu_chars > 0 and urdu_chars >= en_chars:
            total_alpha = max(1, urdu_chars + en_chars)
            conf = round(min(0.99, max(0.85, urdu_chars / total_alpha)), 2)
            return {
                "language": "Urdu",
                "code": "ur",
                "confidence": conf,
                "label": "Urdu"
            }

        total_alpha = max(1, urdu_chars + en_chars)
        conf = round(min(0.99, max(0.85, en_chars / total_alpha if en_chars else 0.90)), 2)
        return {
            "language": "English",
            "code": "en",
            "confidence": conf,
            "label": "English"
        }