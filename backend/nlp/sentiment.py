"""
Sentiment analysis pipeline tuned for Zambian English.

Handles:
- Standard English sentiment
- Common Zambian slang / code-switching (Bemba, Nyanja phrases)
- Political context: negative about govt ≠ negative about PF
- Issue extraction from keyword list
"""
from textblob import TextBlob
from langdetect import detect, LangDetectException
import re
from typing import Optional
from database.models import SentimentLabel


# Zambian slang and context-specific overrides
# Format: {phrase: sentiment_adjustment}  — positive = more positive, negative = more negative
ZAMBIAN_CONTEXT = {
    # Cost of living complaints (strongly negative)
    "life is hard": -0.6,
    "too expensive": -0.5,
    "can't afford": -0.6,
    "ba hichilema": -0.3,        # often used dismissively
    "new dawn": -0.2,            # ironic use common
    "maningi": -0.1,             # "too much" in Nyanja
    "expensive mwe": -0.5,
    "ibinabu": -0.3,             # "problems" in Bemba
    "ukwabula": -0.3,            # "lack of" in Bemba
    "no money": -0.5,
    "poverty": -0.5,
    "suffering": -0.6,
    "starving": -0.7,
    "hunger": -0.6,
    # Positive signals
    "well done pf": 0.6,
    "pf was better": 0.4,
    "bring back pf": 0.5,
    "vote pf": 0.5,
    "pf 2026": 0.4,
}

# Issue keywords mapped to issue categories
ISSUE_KEYWORDS = {
    "mealie_meal":  ["mealie meal", "nshima", "25kg", "breakfast meal", "roller meal", "posho"],
    "fuel":         ["fuel", "petrol", "diesel", "pump price", "fuel price", "transport fare"],
    "electricity":  ["zesco", "load shedding", "power cut", "electricity", "loadshedding", "blackout"],
    "employment":   ["unemployment", "job loss", "retrenchment", "no jobs", "unemployed", "fired"],
    "kwacha":       ["kwacha", "exchange rate", "dollar", "inflation", "depreciation", "forex"],
    "fertiliser":   ["fertiliser", "fisp", "subsidy", "farming input", "crop", "maize"],
    "education":    ["school fees", "hospital fees", "drug shortage", "medicine", "clinic"],
}

# Provinces mentioned in text
PROVINCE_KEYWORDS = {
    "Lusaka":       ["lusaka", "chawama", "kanyama", "matero", "chongwe", "kafue"],
    "Copperbelt":   ["copperbelt", "ndola", "kitwe", "chingola", "mufulira", "wusakile", "luanshya"],
    "Eastern":      ["eastern", "chipata", "petauke", "lundazi", "katete"],
    "Southern":     ["southern", "livingstone", "mazabuka", "choma", "monze", "gwembe"],
    "Central":      ["central", "kabwe", "mkushi", "serenje", "mumbwa"],
    "Western":      ["western", "mongu", "kaoma", "senanga", "kalabo"],
    "Northern":     ["northern", "kasama", "mbala", "mporokoso", "chinsali"],
    "Luapula":      ["luapula", "mansa", "kawambwa", "nchelenge", "samfya"],
    "North-Western":["north-western", "solwezi", "kasempa", "mwinilunga", "zambezi"],
    "Muchinga":     ["muchinga", "chinsali", "nakonde", "isoka", "mpika"],
}


def analyse_sentiment(text: str) -> dict:
    """
    Returns:
        {
          "label": "negative"|"positive"|"neutral",
          "score": 0.0–1.0,        # confidence
          "raw_polarity": float,   # TextBlob polarity -1 to +1
          "issues": ["mealie_meal","fuel",...],
          "province": str|None
        }
    """
    if not text or len(text.strip()) < 10:
        return {"label": "neutral", "score": 0.5, "raw_polarity": 0.0,
                "issues": [], "province": None}

    text_lower = text.lower()

    # Base sentiment from TextBlob
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity   # -1 to +1

    # Apply Zambian context adjustments
    for phrase, adjustment in ZAMBIAN_CONTEXT.items():
        if phrase in text_lower:
            polarity += adjustment

    # Clamp to [-1, 1]
    polarity = max(-1.0, min(1.0, polarity))

    # Government criticism → negative (even if phrased neutrally)
    govt_criticism_patterns = [
        r"government (has|have) failed",
        r"upnd (has|have) failed",
        r"hichilema (has|have) failed",
        r"broken promis",
        r"where is the (change|improvement|new dawn)",
        r"cost of living (is|has) (high|increased|risen|gone up)",
        r"prices? (have|has) (gone|shot|jumped) up",
        r"can\'t afford (to eat|food|mealie|fuel)",
    ]
    for pattern in govt_criticism_patterns:
        if re.search(pattern, text_lower):
            polarity -= 0.3
            break

    polarity = max(-1.0, min(1.0, polarity))

    # Map polarity to label + confidence score
    if polarity < -0.1:
        label = SentimentLabel.negative
        score = min(1.0, abs(polarity) + 0.3)
    elif polarity > 0.1:
        label = SentimentLabel.positive
        score = min(1.0, polarity + 0.3)
    else:
        label = SentimentLabel.neutral
        score = 0.6

    # Extract issues
    issues = []
    for issue, keywords in ISSUE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            issues.append(issue)

    # Detect province
    province = None
    for prov, keywords in PROVINCE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            province = prov
            break

    return {
        "label": label,
        "score": round(score, 3),
        "raw_polarity": round(polarity, 3),
        "issues": issues,
        "province": province,
    }


def batch_analyse(texts: list[str]) -> list[dict]:
    """Analyse a list of texts, returning results in order."""
    return [analyse_sentiment(t) for t in texts]


def compute_province_score(negative_pct: float, post_count: int,
                            avg_polarity: float) -> float:
    """
    Compute a 0–100 grievance score for a province.
    Higher = more public grievance = more opportunity for PF.
    """
    base = negative_pct * 70                      # 70% weight on neg sentiment
    volume_bonus = min(20, post_count / 50)       # up to 20 pts for high volume
    polarity_bonus = abs(min(0, avg_polarity)) * 10  # up to 10 pts for strong negativity
    return round(min(100, base + volume_bonus + polarity_bonus), 1)
