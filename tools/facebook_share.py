"""
Facebook Graph API client for sharing posts to groups.

Setup:
1. Create a Facebook App at developers.facebook.com
2. Request permissions: publish_to_groups, groups_access_member_info
3. Generate a long-lived user access token and set FACEBOOK_ACCESS_TOKEN in .env
4. Set FACEBOOK_GROUP_IDS in .env (comma-separated group IDs)

Token exchange (short-lived → long-lived, valid ~60 days):
  GET https://graph.facebook.com/oauth/access_token
    ?grant_type=fb_exchange_token
    &client_id={APP_ID}
    &client_secret={APP_SECRET}
    &fb_exchange_token={SHORT_LIVED_TOKEN}
"""
from __future__ import annotations

from typing import Optional

import httpx

from config import FACEBOOK_ACCESS_TOKEN, FACEBOOK_GRAPH_VERSION
from models import (
    FacebookGroup,
    FacebookGroupsResult,
    FacebookPostResult,
    FacebookShareSummary,
)

_GRAPH_BASE = f"https://graph.facebook.com/{FACEBOOK_GRAPH_VERSION}"


class FacebookClient:
    def __init__(self, access_token: str = FACEBOOK_ACCESS_TOKEN):
        if not access_token:
            raise ValueError(
                "FACEBOOK_ACCESS_TOKEN is not set. "
                "Add it to your .env file (see .env.example for instructions)."
            )
        self.token = access_token
        self._http = httpx.Client(timeout=30)

    def _get(self, path: str, params: dict | None = None) -> dict:
        p = dict(params or {})
        p["access_token"] = self.token
        resp = self._http.get(f"{_GRAPH_BASE}/{path}", params=p)
        resp.raise_for_status()
        return resp.json()

    def _post_form(self, path: str, data: dict) -> dict:
        d = dict(data)
        d["access_token"] = self.token
        resp = self._http.post(f"{_GRAPH_BASE}/{path}", data=d)
        resp.raise_for_status()
        return resp.json()

    # ── Public helpers ────────────────────────────────────────────────────────

    def verify_token(self) -> dict:
        """Return basic info about the authenticated user."""
        return self._get("me", {"fields": "id,name"})

    def get_groups(self) -> FacebookGroupsResult:
        """List Facebook Groups the authenticated user is a member of."""
        data = self._get(
            "me/groups",
            {"fields": "id,name,privacy,member_count", "limit": 200},
        )
        groups = [
            FacebookGroup(
                id=g["id"],
                name=g["name"],
                privacy=g.get("privacy", ""),
                member_count=g.get("member_count", 0),
            )
            for g in data.get("data", [])
        ]
        return FacebookGroupsResult(groups=groups, total=len(groups))

    def post_to_group(
        self,
        group_id: str,
        message: str,
        link: Optional[str] = None,
        group_name: str = "",
    ) -> FacebookPostResult:
        """Post a message (and optional link) to a single group."""
        payload: dict = {"message": message}
        if link:
            payload["link"] = link
        try:
            result = self._post_form(f"{group_id}/feed", payload)
            return FacebookPostResult(
                group_id=group_id,
                group_name=group_name,
                post_id=result.get("id", ""),
                success=True,
            )
        except httpx.HTTPStatusError as exc:
            error_body = ""
            try:
                error_body = exc.response.json().get("error", {}).get("message", str(exc))
            except Exception:
                error_body = str(exc)
            return FacebookPostResult(
                group_id=group_id,
                group_name=group_name,
                post_id="",
                success=False,
                error=error_body,
            )

    def share_to_groups(
        self,
        group_ids: list[str],
        message: str,
        link: Optional[str] = None,
    ) -> FacebookShareSummary:
        """Post a message to multiple groups and return a summary."""
        results = [
            self.post_to_group(gid, message, link)
            for gid in group_ids
        ]
        return FacebookShareSummary(
            total=len(results),
            succeeded=sum(1 for r in results if r.success),
            failed=sum(1 for r in results if not r.success),
            results=results,
        )


# ── Module-level convenience functions (used by agent.py) ────────────────────

def list_facebook_groups(access_token: str = FACEBOOK_ACCESS_TOKEN) -> FacebookGroupsResult:
    """Return all groups the user belongs to."""
    return FacebookClient(access_token).get_groups()


def share_to_facebook_groups(
    group_ids: list[str],
    message: str,
    link: Optional[str] = None,
    access_token: str = FACEBOOK_ACCESS_TOKEN,
) -> FacebookShareSummary:
    """Share a post to the given group IDs."""
    return FacebookClient(access_token).share_to_groups(group_ids, message, link)
