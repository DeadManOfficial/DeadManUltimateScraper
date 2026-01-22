# [TRACEABILITY] REQ-301
class OutputController:
    """
    Controls output length to minimize unnecessary tokens
    Target: 20-30% token reduction
    """

    @staticmethod
    def add_length_constraint(prompt: str, max_words: int = None, max_sentences: int = None) -> str:
        """Add length constraints to prompt"""
        constraints = []

        if max_words:
            constraints.append(f"Max {max_words} words")

        if max_sentences:
            constraints.append(f"Max {max_sentences} sentences")

        if constraints:
            constraint_text = ". ".join(constraints) + "."
            return f"{prompt}\n\n{constraint_text}"

        return prompt

    @staticmethod
    def request_concise_format(prompt: str) -> str:
        """Request concise response format"""
        concise_instructions = [
            "\nBe concise.",
            "\nBrief response only.",
            "\nSummarize key points.",
            "\nConcise answer:"
        ]

        if '?' in prompt:
            return prompt + concise_instructions[0]
        elif 'list' in prompt.lower():
            return prompt + concise_instructions[2]
        else:
            return prompt + concise_instructions[1]

    @staticmethod
    def prefer_bullet_points(prompt: str) -> str:
        """Request bullet point format (more token-efficient)"""
        if 'explain' in prompt.lower() or 'describe' in prompt.lower():
            return prompt + "\n\nUse bullet points."
        return prompt
