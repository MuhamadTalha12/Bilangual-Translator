from typing import Optional, List, Dict

class PromptBuilder:
    """Constructs dynamic translation prompts incorporating direct, high-precision translation rules."""

    def __init__(self):
        # The 7 Frozen Golden Use Cases updated for DIRECT FAITHFUL TRANSLATION
        self.golden_scenarios = [
            {
                "id": "atm_hardware_failure",
                "category": "ATM Hardware Failure",
                "input": "Bhai ATM me card dala tha chal nahi raha, wahi phans gaya hai.",
                "output": "Brother, I inserted my card into the ATM and it is not working, it is stuck right inside.",
                "risk_rule": "Preserve hardware jam state ('phans gaya' -> 'stuck'); translate the sentence directly without adding 'Customer reports'."
            },
            {
                "id": "failed_raast_transfer",
                "category": "Failed Transfer (Debit no Credit)",
                "input": "Mera Raast transfer fail ho gaya, account se 5000 cut gaye par dost ko nahi mile.",
                "output": "My Raast transfer failed, PKR 5,000 was debited from my account but my friend did not receive it.",
                "risk_rule": "Preserve PKR 5000 exactly. Maintain debit-no-credit state consistency ('cut gaye' -> debited, 'nahi mile' -> not received)."
            },
            {
                "id": "double_deduction",
                "category": "Double Deduction Multiplier",
                "input": "Maine foodpanda pe pay kiya, error aya toh dobara kiya, ab 2 dafa paise kat gaye hain.",
                "output": "I paid on Foodpanda, got an error so I tried again, now money has been debited twice.",
                "risk_rule": "Preserve multiplier ('2 dafa' -> 'twice' / '2 times'); do not drop the double deduction entity."
            },
            {
                "id": "app_crash_pending",
                "category": "App Crash / Timeout",
                "input": "Payment process ho rahi thi aur app achanak band ho gayi, ab status pending hai.",
                "output": "Payment was processing and the mobile app suddenly crashed, now the status is pending.",
                "risk_rule": "Preserve pending state ('status pending hai'); do not hallucinate whether transaction succeeded or failed."
            },
            {
                "id": "unauthorized_fraud",
                "category": "Unauthorized / Scam",
                "input": "Mujhe OTP ka message aya aur foran 25k nikal gaye halanke maine koi transaction nahi ki.",
                "output": "I received an OTP message and immediately PKR 25,000 was debited even though I did not make any transaction.",
                "risk_rule": "Preserve PKR 25,000 (from '25k'). Preserve chronological sequence (OTP received before deduction)."
            },
            {
                "id": "biometric_lockout",
                "category": "Biometric/Login Issue",
                "input": "Mera thumbprint accept nahi ho raha pichle 3 din se, account locked aa raha hai.",
                "output": "My thumbprint is not being accepted for the past 3 days, account is showing locked.",
                "risk_rule": "Preserve temporal duration ('pichle 3 din' -> 'past 3 days') and account lock state."
            },
            {
                "id": "refund_delay",
                "category": "Refund Delay",
                "input": "Daraz ki refund request ki thi 1 hafta pehle, abhi tak reverse nahi hui amount.",
                "output": "I requested a refund from Daraz 1 week ago, the amount has not been reversed yet.",
                "risk_rule": "Preserve timeline ('1 hafta pehle' -> '1 week ago') and reversal state ('reverse nahi hui' -> reversal pending)."
            }
        ]

    def build_prompt(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "ur",
        history: str = "",
        detected_hint: str = None
    ) -> str:
        norm_src = (source_lang or "en").lower().strip()
        norm_tgt = (target_lang or "ur").lower().strip()

        if norm_tgt == "en":
            target_description = "Natural, high-precision English translation"
            source_description = "Urdu or Roman Urdu text"
        else:
            target_description = "Authentic, natural Nastaliq Urdu script"
            source_description = "English text"

        # Defensive exemplar formatting
        exemplar_lines = []
        for idx, item in enumerate(self.golden_scenarios):
            category = item.get("category", "General")
            cust_input = item.get("input", "")
            ticket_output = item.get("output", "")
            risk_rule = item.get("risk_rule", "N/A")
            exemplar_lines.append(
                f"Case {idx + 1} [{category}]:\n"
                f"Input: \"{cust_input}\"\n"
                f"Direct Translation: \"{ticket_output}\"\n"
                f"Compliance Rule: {risk_rule}"
            )
        exemplars_text = "\n\n".join(exemplar_lines)

        context_block = (
            f"\nCONVERSATION HISTORY (Context Manager - Past 5 Turns):\n{history.strip()}\n"
            if history and history.strip() else ""
        )

        hint_block = (
            f"\nUPSTREAM LANGUAGE HINT (advisory only): {detected_hint}\n"
            if detected_hint else ""
        )

        safe_text = (text or "").replace('"""', '\\"\\"\\"')

        return f"""### 1. ROLE & MISSION
You are Bilangual AI, a direct, enterprise-grade English <-> Urdu translator.
Your core mission is to provide DIRECT, ACCURATE, FAITHFUL translations between English and Urdu with ZERO financial hallucination and ZERO added commentary.

### 2. CONTEXT
DIRECTION: {source_description} -> {target_description}
{context_block}{hint_block}
REFERENCE EXEMPLARS (style and numerical accuracy reference only):
{exemplars_text}

### 3. CONSTRAINTS & TRANSLATION RULES:

1. DIRECT FAITHFUL TRANSLATION RULE (CRITICAL):
   - Translate the input text DIRECTLY and FAITHFULLY into the target language.
   - DO NOT rewrite the sentence into a 3rd-person report, summary, or ticket.
   - NEVER add prefixes like "Customer reports that...", "Customer states...", "The user says...", "Customer inserted..." unless those exact words are explicitly present in the input text.
   - Maintain the original grammatical person (1st person "I / my / me" stays 1st person "I / my / me", 2nd person stays 2nd person).

2. 100% NUMERICAL & ENTITY PRESERVATION:
   - NEVER alter, drop, invent, or round financial numbers, amounts, OTPs, account numbers, or dates.
   - Convert shorthand faithfully: "25k" -> "PKR 25,000"; "5000" stays "PKR 5000"; "3 din" -> "3 days".
   - Multipliers ("2 dafa", "twice") must be preserved literally as "twice" / "2 times".

3. FINANCIAL STATE CONSISTENCY:
   - Clearly distinguish DEBIT (funds deducted — "kat gaye", "cut gaye") from CREDIT (funds received, reversed, "jama").
   - Maintain exact debit/credit state consistency without inverting or assuming refunds happened unless stated.

4. LANGUAGE, TONE & VOCABULARY:
   - Translate "current affairs" to Urdu as "کرنٹ افیئرز" every time.
   - Keep modern loanwords natural and untranslated: card, ATM, meeting, account, online, app.
   - Produce fluent, natural native phrasing.

5. AMBIGUITY HANDLING:
   - Only set "ambiguous": true if the input is completely unparseable noise or cutoff.

6. OUTPUT DISCIPLINE:
   - Output ONLY valid JSON matching this exact schema — no markdown code fences, no commentary, no trailing text.

INPUT TEXT:
\"\"\"{safe_text}\"\"\"

Output ONLY valid JSON matching this exact schema:
{{
  "translation": "<direct, faithful translation of the input text as a string>",
  "confidence_score": <float between 0.0 and 1.0 representing model confidence in translation accuracy>,
  "ambiguous": <true or false boolean>,
  "detected_language": "<'Urdu' or 'English'>",
  "detected_code": "<'ur', 'roman_urdu', or 'en'>",
  "pronunciation": "<Romanized pronunciation guide if target is Urdu script, else empty string>",
  "synonyms": ["<alternate phrasing 1>", "<alternate phrasing 2>"],
  "definitions": ["<concise definition if single word, else empty list>"]
}}
"""