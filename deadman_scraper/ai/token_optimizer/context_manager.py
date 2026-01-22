# [TRACEABILITY] REQ-301
from datetime import datetime
from typing import List, Dict
import re

class ContextManager:
    """
    Manages conversation context to minimize token usage
    Target: 30-50% context token reduction
    """

    def __init__(self, max_history: int = 5, compression_threshold: int = 3):
        self.max_history = max_history
        self.compression_threshold = compression_threshold
        self.conversation = []

    def add_message(self, role: str, content: str):
        """Add message to conversation history"""
        self.conversation.append({
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        })

    def get_optimized_context(self) -> List[Dict]:
        """Get token-optimized conversation context"""
        if len(self.conversation) <= self.max_history:
            return self.conversation

        optimized = []

        if self.conversation:
            optimized.append(self.conversation[0])

        middle_start = 1
        middle_end = len(self.conversation) - self.max_history

        if middle_end > middle_start:
            middle_summary = {
                'role': 'system',
                'content': f"[Previous {middle_end - middle_start} messages summarized for context]"
            }
            optimized.append(middle_summary)

        recent = self.conversation[-self.max_history:]
        optimized.extend(recent)

        return optimized

    def compress_message(self, content: str) -> str:
        """Compress individual message content"""
        if len(self.conversation) > self.compression_threshold:
            content = re.sub(r'```[\s\S]*?```', '[code block]', content)

        content = re.sub(r'\s+', ' ', content).strip()

        return content
