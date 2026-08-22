"""Telegram Bot API wrapper."""

import requests
import json
from typing import List, Dict, Any, Optional
from agent.logger import setup_logger
from agent.config import Config

logger = setup_logger(__name__)


class TelegramTool:
    """Wrapper for Telegram Bot API."""

    def __init__(self, config: Config):
        self.config = config
        self.base_url = f"https://api.telegram.org/bot{config.telegram_bot_token}"
        self.chat_id = str(config.telegram_chat_id)

    def _call_with_retry(self, method: str, endpoint: str, max_retries: int = 3, **kwargs) -> requests.Response:
        """Call Telegram API with exponential backoff retry."""
        import time

        url = f"{self.base_url}/{endpoint}"
        for attempt in range(max_retries):
            try:
                resp = requests.request(
                    method,
                    url,
                    timeout=self.config.api_timeout,
                    **kwargs,
                )
                if resp.status_code < 500:
                    return resp
                if attempt < max_retries - 1:
                    delay = self.config.retry_delay_base * (2**attempt)
                    logger.warning(f"Telegram {resp.status_code}, retrying in {delay}s...")
                    time.sleep(delay)
            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    delay = self.config.retry_delay_base * (2**attempt)
                    logger.warning(f"Telegram request failed: {e}, retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"Telegram API failed after {max_retries} retries: {e}")
                    raise
        return resp

    def send_message(self, text: str, parse_mode: str = "Markdown") -> Dict[str, Any]:
        """Send message to chat."""
        logger.info(f"Sending Telegram message: {text[:50]}...")
        resp = self._call_with_retry(
            "POST",
            "sendMessage",
            json={"chat_id": self.chat_id, "text": text, "parse_mode": parse_mode},
        )
        resp.raise_for_status()
        return resp.json()

    def get_updates(self, offset: int = 0, timeout: int = 0) -> List[Dict[str, Any]]:
        """Poll for new messages."""
        logger.info(f"Polling Telegram messages (offset={offset})")
        resp = self._call_with_retry(
            "GET", "getUpdates", params={"offset": offset, "timeout": timeout}
        )
        if not resp.ok:
            logger.error(f"Telegram getUpdates failed: {resp.status_code} {resp.text}")
            return []
        return resp.json().get("result", [])

    def send_approval_request(self, repo: str, variants: List[tuple]) -> str:
        """Send variants to user for approval. Returns message_id."""
        lines = [f"🤖 *3 post variants ready for {repo}*\n"]

        for i, (variant, score) in enumerate(variants, 1):
            lines.append(f"{i}️⃣ [{variant.narrative}] — Score: {score:.1f}/10")
            lines.append(f"```\n{variant.post_text}\n```\n")

        lines.append("*Reply:*")
        lines.append("`/choose 1` post variant 1")
        lines.append("`/choose 2` post variant 2")
        lines.append("`/choose 3` post variant 3")
        lines.append("`/edit <text>` customize before posting")
        lines.append("`/refine` regenerate based on feedback")
        lines.append("`/reject` discard all")

        message = "\n".join(lines)
        result = self.send_message(message, parse_mode="Markdown")
        return result.get("result", {}).get("message_id", "")
