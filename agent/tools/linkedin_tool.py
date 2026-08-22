"""LinkedIn API wrapper."""

import requests
from typing import Dict, Any
from agent.logger import setup_logger
from agent.config import Config

logger = setup_logger(__name__)


class LinkedInTool:
    """Wrapper for LinkedIn UGC Posts API."""

    def __init__(self, config: Config):
        self.config = config
        self.base_url = "https://api.linkedin.com/v2/ugcPosts"

    def _call_with_retry(self, method: str, url: str, max_retries: int = 3, **kwargs) -> requests.Response:
        """Call LinkedIn API with exponential backoff retry."""
        import time

        for attempt in range(max_retries):
            try:
                resp = requests.request(
                    method,
                    url,
                    headers={
                        "Authorization": f"Bearer {self.config.linkedin_access_token}",
                        "Content-Type": "application/json",
                        "X-Restli-Protocol-Version": "2.0.0",
                    },
                    timeout=self.config.api_timeout,
                    **kwargs,
                )

                if resp.status_code == 429:  # Rate limited
                    if attempt < max_retries - 1:
                        delay = self.config.retry_delay_base * (2**attempt)
                        logger.warning(f"LinkedIn rate limited, retrying in {delay}s...")
                        time.sleep(delay)
                        continue
                elif resp.status_code >= 500:
                    if attempt < max_retries - 1:
                        delay = self.config.retry_delay_base * (2**attempt)
                        logger.warning(f"LinkedIn {resp.status_code}, retrying in {delay}s...")
                        time.sleep(delay)
                        continue

                return resp
            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    delay = self.config.retry_delay_base * (2**attempt)
                    logger.warning(f"LinkedIn request failed: {e}, retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"LinkedIn API failed after {max_retries} retries: {e}")
                    raise

    def post_ugc(self, post_text: str) -> Dict[str, Any]:
        """Post content to LinkedIn."""
        logger.info(f"Posting to LinkedIn: {post_text[:50]}...")

        payload = {
            "author": self.config.linkedin_person_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": post_text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }

        resp = self._call_with_retry("POST", self.base_url, json=payload)

        if resp.status_code not in (200, 201):
            logger.error(f"LinkedIn post failed: {resp.status_code} {resp.text}")
            resp.raise_for_status()

        logger.info("Successfully posted to LinkedIn")
        return {"success": True, "status_code": resp.status_code}
