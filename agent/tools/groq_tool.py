"""Groq API wrapper for LLM calls."""

import requests
from typing import Optional, Dict, Any
from agent.logger import setup_logger
from agent.config import Config

logger = setup_logger(__name__)


class GroqTool:
    """Wrapper for Groq API with retry logic."""

    def __init__(self, config: Config):
        self.config = config
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"

    def _call_with_retry(self, payload: Dict[str, Any], max_retries: int = 3) -> str:
        """Call Groq API with exponential backoff retry."""
        import time

        for attempt in range(max_retries):
            try:
                resp = requests.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.config.groq_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=self.config.api_timeout,
                )

                if resp.status_code == 429:  # Rate limited
                    if attempt < max_retries - 1:
                        delay = self.config.retry_delay_base * (2**attempt)
                        logger.warning(f"Groq rate limited, retrying in {delay}s...")
                        time.sleep(delay)
                        continue
                elif resp.status_code >= 500:  # Server error
                    if attempt < max_retries - 1:
                        delay = self.config.retry_delay_base * (2**attempt)
                        logger.warning(f"Groq {resp.status_code}, retrying in {delay}s...")
                        time.sleep(delay)
                        continue

                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"].strip()
            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    delay = self.config.retry_delay_base * (2**attempt)
                    logger.warning(f"Groq request failed: {e}, retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"Groq API failed after {max_retries} retries: {e}")
                    raise

    def analyze_repo(self, repo_data: str) -> str:
        """Analyze repository to determine narrative angle."""
        logger.info("Analyzing repository for narrative angle")

        prompt = f"""
You are an expert tech recruiter and content strategist. Analyze this GitHub repository and identify the most compelling narrative angle that would impress a hiring manager.

Repository data:
{repo_data}

Provide:
1. Primary narrative angle (e.g., "engineering excellence", "solving real problems", "innovative approach")
2. Target audience segment (e.g., "ML engineers", "DevOps professionals", "startup founders")
3. Key hooks/angles to emphasize (concrete, measurable, authentic)
4. Recommended tone (technical, inspirational, casual, professional)
5. Why this angle matters to a recruiter

Be concise and specific. Avoid generic descriptions.
"""

        payload = {
            "model": self.config.groq_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config.analysis_temperature,
            "max_tokens": self.config.max_tokens_analysis,
        }
        return self._call_with_retry(payload)

    def generate_variant(
        self, repo_data: str, narrative_analysis: str, variant_type: str, user_preferences: str = ""
    ) -> str:
        """Generate a post variant with specific angle."""
        logger.info(f"Generating {variant_type} variant")

        variant_instructions = {
            "recruiter": "Focus on: engineering rigor, measurable impact, technical decision-making, production readiness, team capability. Make a hiring manager think 'This person can ship.'",
            "developer": "Focus on: solving real problems, ease of use, practical value, developer experience. Make developers think 'I want to use this.'",
            "community": "Focus on: open source contribution, learning opportunity, community impact, accessibility. Make engineers think 'I want to contribute.'",
        }

        prompt = f"""
You are a LinkedIn content expert. Generate a compelling LinkedIn post about this GitHub repository.

{variant_instructions.get(variant_type, "")}

Repository data:
{repo_data}

Narrative analysis (context):
{narrative_analysis}

User preferences (incorporate if provided):
{user_preferences or "None specified"}

Hard rules:
- 100-180 words exactly
- Sound like a real engineer, not a marketer
- NO hashtag spam (0-3 hashtags max, only if genuinely relevant)
- NO generic phrases: "excited to share", "thrilled to announce", "game-changer", "revolutionary"
- Open with something concrete (problem, solution, result) NOT "I built a project"
- Include specifics: what it does, why it matters, what was interesting about it
- End with natural call-to-action (e.g., "Check it out", "Curious what you'd do differently")
- First person, past or present tense as natural

Output ONLY the post text. No explanations, no quotes around it.
"""

        payload = {
            "model": self.config.groq_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config.generation_temperature,
            "max_tokens": self.config.max_tokens_generation,
        }
        return self._call_with_retry(payload)

    def evaluate_variants(self, repo_data: str, variants: str, user_preferences: str = "") -> str:
        """Evaluate and score post variants."""
        logger.info("Evaluating post variants")

        prompt = f"""
You are a recruiter and content quality evaluator. Score these LinkedIn post variants on the criteria below.

Repository context:
{repo_data}

Variants to evaluate:
{variants}

User preferences (if any):
{user_preferences or "None"}

For EACH variant, provide:
- Authenticity (0-10): Does it match the repository reality? Any hallucinated facts?
- Recruiter Appeal (0-10): Would a hiring manager find this impressive? Does it demonstrate capability?
- Originality (0-10): Avoids generic LinkedIn spam phrases?
- Clarity (0-10): Easy to understand on mobile? Well-structured?
- CTA Quality (0-10): Natural, non-pushy call-to-action?
- Composite Score (0-10): Overall quality (weighted: authenticity 25%, recruiter_appeal 30%, originality 20%, clarity 15%, cta_quality 10%)

Format output as JSON:
{
  "variants": [
    {"id": "recruiter", "authenticity": 8, "recruiter_appeal": 9, "originality": 8, "clarity": 9, "cta_quality": 8, "composite_score": 8.4, "reasoning": "brief explanation"},
    ...
  ]
}
"""

        payload = {
            "model": self.config.groq_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config.analysis_temperature,
            "max_tokens": self.config.max_tokens_evaluation,
        }
        return self._call_with_retry(payload)
