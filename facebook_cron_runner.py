"""
Facebook Auto-Share Cron Runner

Usage:
  # Post daily at 09:00 (default)
  python facebook_cron_runner.py

  # Post every 4 hours
  python facebook_cron_runner.py --every-hours 4

  # Post daily at a custom time
  python facebook_cron_runner.py --daily 14:30

  # Post every Monday at 10:00
  python facebook_cron_runner.py --weekly monday --at 10:00

  # Post every 30 minutes (for testing)
  python facebook_cron_runner.py --every-minutes 30

  # Run once immediately and exit
  python facebook_cron_runner.py --run-once

  # List your groups (to find group IDs)
  python facebook_cron_runner.py --list-groups

  # Use a custom posts file
  python facebook_cron_runner.py --posts-file /path/to/posts.json
"""
from __future__ import annotations

import logging
import sys

import click
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@click.command()
@click.option("--run-once", is_flag=True, help="Post once immediately and exit")
@click.option("--list-groups", is_flag=True, help="Print all groups the account belongs to")
@click.option("--every-hours", default=0, type=int, help="Post every N hours")
@click.option("--every-minutes", default=0, type=int, help="Post every N minutes (testing)")
@click.option("--daily", default="", help="Post daily at HH:MM (e.g. 09:00)")
@click.option("--weekly", default="", help="Weekday for weekly posts (e.g. monday)")
@click.option("--at", "at_time", default="09:00", help="Time for --daily / --weekly (HH:MM)")
@click.option("--group-ids", default="", help="Override FACEBOOK_GROUP_IDS (comma-separated)")
@click.option("--posts-file", default="facebook_posts.json", show_default=True,
              help="Path to the JSON posts queue file")
def main(
    run_once: bool,
    list_groups: bool,
    every_hours: int,
    every_minutes: int,
    daily: str,
    weekly: str,
    at_time: str,
    group_ids: str,
    posts_file: str,
) -> None:
    from config import FACEBOOK_ACCESS_TOKEN
    from tools.facebook_share import FacebookClient
    from tools.facebook_cron import FacebookCronJob

    if not FACEBOOK_ACCESS_TOKEN:
        logger.error(
            "FACEBOOK_ACCESS_TOKEN is not set. "
            "Add it to your .env file (see .env.example)."
        )
        sys.exit(1)

    # ── List groups mode ──────────────────────────────────────────────────────
    if list_groups:
        client = FacebookClient(FACEBOOK_ACCESS_TOKEN)
        me = client.verify_token()
        click.echo(f"\nAuthenticated as: {me.get('name')} (id={me.get('id')})\n")
        result = client.get_groups()
        if not result.groups:
            click.echo("No groups found (you may need groups_access_member_info permission).")
            return
        click.echo(f"{'ID':<20} {'Privacy':<12} {'Members':>8}  Name")
        click.echo("-" * 70)
        for g in result.groups:
            click.echo(f"{g.id:<20} {g.privacy:<12} {g.member_count:>8}  {g.name}")
        click.echo(f"\nTotal: {result.total} group(s)")
        return

    # ── Build cron job ────────────────────────────────────────────────────────
    override_ids = [g.strip() for g in group_ids.split(",") if g.strip()]
    job = FacebookCronJob(
        access_token=FACEBOOK_ACCESS_TOKEN,
        group_ids=override_ids or None,
        posts_file=posts_file,
    )

    # ── Run-once mode ─────────────────────────────────────────────────────────
    if run_once:
        job.run_once()
        return

    # ── Schedule and run forever ──────────────────────────────────────────────
    if every_minutes:
        job.schedule_every_minutes(every_minutes)
    elif every_hours:
        job.schedule_every_hours(every_hours)
    elif weekly:
        job.schedule_weekly(weekday=weekly.lower(), at_time=at_time)
    elif daily:
        job.schedule_daily(at_time=daily)
    else:
        job.schedule_daily(at_time=at_time)  # default: daily at --at (09:00)

    job.run_forever()


if __name__ == "__main__":
    main()
