"""
Cron-job scheduler for Facebook auto-sharing.

Posts are read from a JSON file (default: facebook_posts.json).
The scheduler cycles through the queue, posting one item per trigger.

Post queue format (facebook_posts.json):
[
  {"message": "Your post text", "link": "https://optional-link.com"},
  {"message": "Another post", "link": null}
]
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

import schedule

from config import FACEBOOK_ACCESS_TOKEN, FACEBOOK_GROUP_IDS
from tools.facebook_share import FacebookClient

logger = logging.getLogger(__name__)


class FacebookCronJob:
    def __init__(
        self,
        access_token: str = FACEBOOK_ACCESS_TOKEN,
        group_ids: Optional[list[str]] = None,
        posts_file: str = "facebook_posts.json",
    ):
        self.client = FacebookClient(access_token)
        self.group_ids = group_ids if group_ids is not None else list(FACEBOOK_GROUP_IDS)
        self.posts_file = Path(posts_file)
        self._post_index = 0

        if not self.group_ids:
            raise ValueError(
                "No group IDs configured. "
                "Set FACEBOOK_GROUP_IDS in .env or pass group_ids explicitly."
            )

    # ── Post queue ────────────────────────────────────────────────────────────

    def _load_posts(self) -> list[dict]:
        if not self.posts_file.exists():
            logger.warning("Posts file not found: %s", self.posts_file)
            return []
        try:
            posts = json.loads(self.posts_file.read_text(encoding="utf-8"))
            if not isinstance(posts, list):
                raise ValueError("Posts file must be a JSON array")
            return posts
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("Failed to load posts: %s", exc)
            return []

    def _next_post(self) -> Optional[dict]:
        posts = self._load_posts()
        if not posts:
            return None
        post = posts[self._post_index % len(posts)]
        self._post_index += 1
        return post

    # ── Execution ─────────────────────────────────────────────────────────────

    def run_once(self) -> None:
        """Post the next queued item to all configured groups."""
        post = self._next_post()
        if not post:
            logger.warning("Post queue is empty — skipping")
            return

        message = post.get("message", "").strip()
        if not message:
            logger.warning("Post has empty message — skipping")
            return

        link: Optional[str] = post.get("link") or None
        logger.info(
            "Sharing to %d group(s): %.80s%s",
            len(self.group_ids),
            message,
            "..." if len(message) > 80 else "",
        )

        summary = self.client.share_to_groups(
            group_ids=self.group_ids,
            message=message,
            link=link,
        )

        for result in summary.results:
            if result.success:
                logger.info("  [OK] group %s → post %s", result.group_id, result.post_id)
            else:
                logger.error("  [FAIL] group %s → %s", result.group_id, result.error)

        logger.info(
            "Done: %d/%d succeeded", summary.succeeded, summary.total
        )

    # ── Scheduling ────────────────────────────────────────────────────────────

    def schedule_every_hours(self, hours: int) -> "FacebookCronJob":
        """Post every N hours."""
        schedule.every(hours).hours.do(self.run_once)
        logger.info("Scheduled: every %d hour(s)", hours)
        return self

    def schedule_every_minutes(self, minutes: int) -> "FacebookCronJob":
        """Post every N minutes (useful for testing)."""
        schedule.every(minutes).minutes.do(self.run_once)
        logger.info("Scheduled: every %d minute(s)", minutes)
        return self

    def schedule_daily(self, at_time: str = "09:00") -> "FacebookCronJob":
        """Post once per day at a fixed time (HH:MM, 24-hour)."""
        schedule.every().day.at(at_time).do(self.run_once)
        logger.info("Scheduled: daily at %s", at_time)
        return self

    def schedule_weekly(self, weekday: str = "monday", at_time: str = "09:00") -> "FacebookCronJob":
        """Post once per week on a given weekday at a fixed time."""
        getattr(schedule.every(), weekday).at(at_time).do(self.run_once)
        logger.info("Scheduled: every %s at %s", weekday, at_time)
        return self

    def run_forever(self, poll_interval_seconds: int = 60) -> None:
        """Block forever, executing pending jobs every poll_interval_seconds."""
        logger.info(
            "Facebook cron started — %d job(s) scheduled, polling every %ds",
            len(schedule.jobs),
            poll_interval_seconds,
        )
        try:
            while True:
                schedule.run_pending()
                time.sleep(poll_interval_seconds)
        except KeyboardInterrupt:
            logger.info("Facebook cron stopped")
