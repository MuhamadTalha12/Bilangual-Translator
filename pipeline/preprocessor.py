import re

class Preprocessor:
    """Normalizes input while strictly preserving financial entities (numbers, currency)."""
    def __init__(self):
        self.repeated_punct = re.compile(r'([.!?])\1+')
        self.extra_spaces = re.compile(r'\s+')

    def clean(self, text: str) -> str:
        if not text:
            return ""
        text = self.repeated_punct.sub(r'\1', text)
        text = self.extra_spaces.sub(' ', text).strip()
        return text