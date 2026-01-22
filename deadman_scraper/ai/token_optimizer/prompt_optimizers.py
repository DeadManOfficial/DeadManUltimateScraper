# [TRACEABILITY] REQ-301
import re

class PromptOptimizer:
    """
    Optimizes prompts to reduce token usage
    Techniques: compression, template optimization, redundancy removal
    """

    @staticmethod
    def compress_prompt(prompt: str) -> str:
        """
        Compress prompt by removing redundancy
        Target: 20-30% token reduction
        """
        compressed = re.sub(r'\s+', ' ', prompt)

        redundant_phrases = [
            r'please\s+',
            r'could you\s+',
            r'would you\s+',
            r'can you\s+',
            r'i would like you to\s+',
            r'i want you to\s+',
            r'make sure to\s+',
            r'be sure to\s+',
        ]

        for phrase in redundant_phrases:
            compressed = re.sub(phrase, '', compressed, flags=re.IGNORECASE)

        compressed = re.sub(r'\b(the|a|an)\s+(?=(data|file|code|text|content))', '', compressed, flags=re.IGNORECASE)

        abbreviations = {
            r'\bdocumentation\b': 'docs',
            r'\bconfiguration\b': 'config',
            r'\brepository\b': 'repo',
            r'\bapplication\b': 'app',
            r'\bdatabase\b': 'db',
            r'\binformation\b': 'info',
        }

        for full, abbr in abbreviations.items():
            compressed = re.sub(full, abbr, compressed, flags=re.IGNORECASE)

        compressed = re.sub(r'([.!?])\1+', r'\1', compressed)

        compressed = compressed.strip()

        return compressed

    @staticmethod
    def optimize_system_prompt(system_prompt: str) -> str:
        """
        Optimize system prompt for minimal tokens
        Target: 30-40% reduction
        """
        optimized = system_prompt

        replacements = {
            'You are a helpful assistant that': 'You',
            'Your task is to': '',
            'You should': '',
            'Make sure to': '',
            'Please ensure that you': '',
            'Always remember to': '',
        }

        for verbose, concise in replacements.items():
            optimized = optimized.replace(verbose, concise)

        if 'For example' in optimized:
            if len(optimized) > 200:
                optimized = re.sub(r'For example[^.]*\.', '', optimized)

        optimized = re.sub(r'\s+', ' ', optimized).strip()

        return optimized

    @staticmethod
    def create_efficient_template(task_type: str) -> str:
        """
        Get token-efficient template for common tasks
        """
        templates = {
            'summarize': 'Summarize in {length} words:\n{content}',
            'analyze': 'Analyze {content}. Focus on {aspects}.',
            'extract': 'Extract {target} from:\n{content}',
            'translate': 'Translate to {language}:\n{content}',
            'code_review': 'Review code:\n{code}\nIssues:',
            'debug': 'Debug:\n{code}\nError: {error}',
            'explain': 'Explain {concept} concisely.',
        }

        return templates.get(task_type, '{content}')
