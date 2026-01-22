"""
DEADMAN SCRAPER - Sentiment Analysis
=====================================
Weighted keyword sentiment analysis for dark web content.

Features:
- Custom weighted keywords for dark web monitoring
- AFINN-based base sentiment
- Comparative scoring (normalized by word count)
- Batch analysis for charts
- Keyword extraction

Based on zilbers/dark-web-scraper sentiment patterns, enhanced for DeadMan.
"""

import re
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("DeadMan.Sentiment")


# Dark web focused keywords with negative weights
# Higher negative = more concerning/dangerous
DARK_WEB_KEYWORDS: dict[str, int] = {
    # Cyber attacks
    "ddos": -3,
    "exploits": -4,
    "exploit": -4,
    "attack": -3,
    "malware": -4,
    "ransomware": -4,
    "trojan": -4,
    "botnet": -4,
    "backdoor": -4,
    "rootkit": -5,
    "zero-day": -5,
    "0day": -5,
    "vulnerability": -3,
    "cve": -2,

    # Credentials & Data
    "passwords": -5,
    "password": -5,
    "credentials": -5,
    "username": -5,
    "account": -3,
    "leaked": -5,
    "breach": -5,
    "dump": -4,
    "fullz": -5,
    "ssn": -5,
    "dob": -3,
    "stolen": -5,
    "hacked": -4,
    "cracked": -4,
    "combo": -3,
    "combolist": -4,

    # Financial
    "credit cards": -5,
    "credit card": -5,
    "cc": -3,
    "cvv": -5,
    "bin": -3,
    "carding": -5,
    "cashout": -4,
    "bitcoin": -2,
    "btc": -2,
    "monero": -2,
    "xmr": -2,
    "crypto": -1,
    "wallet": -2,
    "money": -2,
    "dollar": -1,

    # Illegal goods
    "weapons": -5,
    "guns": -5,
    "explosives": -5,
    "drugs": -4,
    "narcotics": -4,

    # General dark web
    "forbidden": -3,
    "underground": -2,
    "black market": -4,
    "darknet": -2,
    "onion": -1,
    "tor": -1,
    "anonymous": -1,
    "untraceable": -3,

    # Fraud
    "fraud": -4,
    "scam": -3,
    "phishing": -4,
    "spoof": -3,
    "fake": -2,
    "counterfeit": -4,
    "forged": -4,

    # Access
    "admin": -2,
    "root": -2,
    "shell": -3,
    "rdp": -3,
    "vpn": -1,
    "proxy": -1,
    "access": -2,

    # PII
    "identity": -3,
    "biometric": -3,
    "passport": -4,
    "license": -3,
    "social security": -5,

    # Russian dark web terms (transliterated)
    "vzlomschik": -4,  # hacker
    "zaliv": -3,       # money transfer
    "beznal": -3,      # non-cash
    "vzlom": -4,       # hack
}


# AFINN-111 base lexicon subset (most common words)
AFINN_BASE: dict[str, int] = {
    "good": 3, "great": 3, "excellent": 3, "amazing": 4, "awesome": 4,
    "bad": -3, "terrible": -3, "awful": -3, "horrible": -4,
    "love": 3, "hate": -3, "like": 2, "dislike": -2,
    "happy": 3, "sad": -2, "angry": -3, "fear": -2,
    "success": 3, "fail": -2, "failure": -2, "error": -1,
    "secure": 2, "insecure": -2, "safe": 2, "danger": -3,
    "free": 1, "cheap": 1, "expensive": -1,
    "fast": 1, "slow": -1, "easy": 1, "hard": -1,
    "new": 1, "old": -1, "fresh": 1, "stale": -1,
    "trust": 2, "distrust": -2, "reliable": 2, "unreliable": -2,
    "legal": 1, "illegal": -3, "legit": 1, "scam": -4,
}


@dataclass
class SentimentResult:
    """Result of sentiment analysis."""
    score: int               # Raw sentiment score
    comparative: float       # Score normalized by word count
    words: list[str]         # Sentiment-bearing words found
    keyword_matches: list[str]  # Dark web keywords found
    word_count: int          # Total words analyzed


class SentimentAnalyzer:
    """
    Sentiment analyzer with dark web keyword weighting.

    Combines AFINN-based base sentiment with custom dark web
    keyword weights for comprehensive threat scoring.
    """

    def __init__(
        self,
        custom_keywords: dict[str, int] | None = None,
        include_base_afinn: bool = True
    ):
        """
        Initialize the sentiment analyzer.

        Args:
            custom_keywords: Additional custom keywords with weights
            include_base_afinn: Include AFINN base lexicon
        """
        self.lexicon: dict[str, int] = {}

        # Add AFINN base if requested
        if include_base_afinn:
            self.lexicon.update(AFINN_BASE)

        # Add dark web keywords
        self.lexicon.update(DARK_WEB_KEYWORDS)

        # Add any custom keywords
        if custom_keywords:
            self.lexicon.update(custom_keywords)

        # Compile regex for multi-word phrases
        self._phrase_patterns = {
            phrase: weight
            for phrase, weight in self.lexicon.items()
            if " " in phrase
        }

        logger.info(f"Sentiment analyzer initialized with {len(self.lexicon)} keywords")

    def analyze(self, text: str) -> SentimentResult:
        """
        Analyze sentiment of text.

        Args:
            text: Text to analyze

        Returns:
            SentimentResult with score and details
        """
        if not text:
            return SentimentResult(
                score=0,
                comparative=0.0,
                words=[],
                keyword_matches=[],
                word_count=0
            )

        text_lower = text.lower()
        score = 0
        words_found = []
        keyword_matches = []

        # Check multi-word phrases first
        for phrase, weight in self._phrase_patterns.items():
            if phrase in text_lower:
                score += weight
                words_found.append(phrase)
                if phrase in DARK_WEB_KEYWORDS:
                    keyword_matches.append(phrase)

        # Tokenize and check single words
        tokens = re.findall(r'\b[a-z]+\b', text_lower)
        word_count = len(tokens)

        for token in tokens:
            if token in self.lexicon and token not in self._phrase_patterns:
                weight = self.lexicon[token]
                score += weight
                words_found.append(token)
                if token in DARK_WEB_KEYWORDS:
                    keyword_matches.append(token)

        # Calculate comparative (normalized) score
        comparative = score / word_count if word_count > 0 else 0.0

        return SentimentResult(
            score=score,
            comparative=round(comparative, 4),
            words=words_found,
            keyword_matches=list(set(keyword_matches)),
            word_count=word_count
        )

    def analyze_document(self, doc: dict, fields: list[str] | None = None) -> SentimentResult:
        """
        Analyze sentiment across multiple fields of a document.

        Args:
            doc: Document dict with text fields
            fields: List of field names to analyze (default: all string fields)

        Returns:
            Combined SentimentResult
        """
        if fields is None:
            fields = [k for k, v in doc.items() if isinstance(v, str)]

        combined_text = " ".join(str(doc.get(f, "")) for f in fields)
        return self.analyze(combined_text)

    def analyze_batch(
        self,
        documents: list[dict],
        fields: list[str] | None = None
    ) -> list[dict]:
        """
        Analyze sentiment for multiple documents.

        Args:
            documents: List of document dicts
            fields: Fields to analyze per document

        Returns:
            List of {score, comparative, words} dicts for charts
        """
        results = []
        for doc in documents:
            result = self.analyze_document(doc, fields)
            results.append({
                "score": result.score,
                "comparative": result.comparative,
                "words": result.words
            })
        return results

    def get_threat_level(self, score: int) -> str:
        """
        Convert score to threat level.

        Args:
            score: Raw sentiment score

        Returns:
            Threat level string
        """
        if score >= 0:
            return "neutral"
        elif score > -10:
            return "low"
        elif score > -25:
            return "medium"
        elif score > -50:
            return "high"
        else:
            return "critical"

    def extract_keywords(self, text: str) -> list[tuple[str, int]]:
        """
        Extract dark web keywords found in text with their weights.

        Args:
            text: Text to scan

        Returns:
            List of (keyword, weight) tuples
        """
        text_lower = text.lower()
        found = []

        for keyword, weight in DARK_WEB_KEYWORDS.items():
            if keyword in text_lower:
                found.append((keyword, weight))

        return sorted(found, key=lambda x: x[1])  # Most negative first

    def add_keyword(self, keyword: str, weight: int) -> None:
        """Add or update a keyword in the lexicon."""
        keyword_lower = keyword.lower()
        self.lexicon[keyword_lower] = weight

        if " " in keyword_lower:
            self._phrase_patterns[keyword_lower] = weight

        logger.debug(f"Added keyword: {keyword} = {weight}")

    def remove_keyword(self, keyword: str) -> bool:
        """Remove a keyword from the lexicon."""
        keyword_lower = keyword.lower()

        if keyword_lower in self.lexicon:
            del self.lexicon[keyword_lower]
            self._phrase_patterns.pop(keyword_lower, None)
            return True

        return False

    def get_keyword_stats(self) -> dict:
        """Get statistics about the keyword lexicon."""
        positive = sum(1 for v in self.lexicon.values() if v > 0)
        negative = sum(1 for v in self.lexicon.values() if v < 0)
        neutral = sum(1 for v in self.lexicon.values() if v == 0)

        return {
            "total_keywords": len(self.lexicon),
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
            "dark_web_keywords": len(DARK_WEB_KEYWORDS),
            "most_negative": min(self.lexicon.values()) if self.lexicon else 0,
            "most_positive": max(self.lexicon.values()) if self.lexicon else 0
        }


# Convenience function for quick analysis
def analyze_sentiment(text: str) -> SentimentResult:
    """Quick sentiment analysis with default settings."""
    analyzer = SentimentAnalyzer()
    return analyzer.analyze(text)


def get_threat_score(text: str) -> tuple[int, str]:
    """Get threat score and level for text."""
    analyzer = SentimentAnalyzer()
    result = analyzer.analyze(text)
    level = analyzer.get_threat_level(result.score)
    return result.score, level
