import re
from typing import Dict, List, Tuple

# All intent rules centralized in this single file as required
INTENT_RULES: Dict[str, List[str]] = {
    "Refund": [
        "refund",
        "reimburse",
        "reimbursement",
        "money back",
        "duplicate charge",
        "overcharge",
        "tax refund",
        "fare difference",
        "penalty refund",
        "double billed",
    ],
    "Date Change": [
        "date change",
        "reschedule",
        "postpone",
        "prepone",
        "change date",
        "extend stay",
        "flight change",
        "departure date",
        "modify booking",
        "new travel date",
    ],
    "Cancellation": [
        "cancel",
        "cancellation",
        "canceling",
        "cancelled",
        "void",
        "abort",
        "no-show",
        "no show",
        "unable to travel",
    ],
    "Visa/Documents": [
        "visa",
        "passport",
        "transit visa",
        "document",
        "documentation",
        "name correction",
        "typo in name",
        "passport number",
        "travel permit",
    ],
    "Payment Issue": [
        "payment",
        "transaction",
        "3d secure",
        "credit line",
        "wallet balance",
        "gateway timeout",
        "billing",
        "card declined",
        "invoice",
        "gst invoice",
        "vat",
    ],
    "Supplier Issue": [
        "supplier",
        "hotel refused",
        "room not found",
        "driver not found",
        "transfer missing",
        "bed type",
        "overbooked",
        "voucher rejected",
        "property claims",
        "gds issue",
    ],
}


def detect_intent(text: str) -> Tuple[str, List[str]]:
    """
    Rule-based intent auto-suggest engine.
    Analyzes input text against dictionary patterns and identifies matching trigger words.

    Returns:
        (suggested_intent, matched_words_list)
        If no rules match, returns ("Other", []).
    """
    if not text or not text.strip():
        return "Other", []

    normalized_text = text.lower()
    best_intent = "Other"
    best_matches: List[str] = []
    max_match_count = 0

    for intent, keywords in INTENT_RULES.items():
        matched_for_intent = []
        for kw in keywords:
            # Use regex word boundaries for single words, direct substring for multi-word phrases
            if " " in kw:
                pattern = r"(?:\b|^)" + re.escape(kw) + r"(?:\b|$)"
            else:
                pattern = r"\b" + re.escape(kw) + r"\b"

            if re.search(pattern, normalized_text):
                matched_for_intent.append(kw)

        match_count = len(matched_for_intent)
        if match_count > max_match_count:
            max_match_count = match_count
            best_intent = intent
            best_matches = matched_for_intent

    return best_intent, best_matches
