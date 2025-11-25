import argparse
import logging
from datetime import datetime
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from reddit_client import RedditClient
from database import Database
from scheduler import MonitoringScheduler

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("reddit_monitor.log"),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)


def cmd_test(args):
    client = RedditClient()
    result = client.verify_connection()

    if result["success"]:
        print(f"✓ {result['message']}")
        print(f"  Link Karma: {result['link_karma']}")
        print(f"  Comment Karma: {result['comment_karma']}")
        print(f"  Account Age: {result['account_age_days']} days")
    else:
        print(f"✗ {result['message']}")


def cmd_fetch(args):
    client = RedditClient()
    db = Database()

    posts = client.get_subreddit_posts(
        args.subreddit,
        limit=args.limit,
        sort=args.sort
    )

    if args.json:
        print(json.dumps(posts, indent=2))
    else:
        for post in posts:
            print(f"\n{post['title']}")
            print(f"  r/{post['subreddit']} | {post['score']} pts | {post['num_comments']} comments")
            print(f"  by {post['author']}")

            post_id = db.insert_post(post)
            if post_id:
                print(f"  [Stored]")


def cmd_monitor(args):
    subreddits = os.getenv("TARGET_SUBREDDITS", "SaaS,startup").split(",")
    keywords = os.getenv("KEYWORDS", "feedback,customer").split(",")
    interval = int(os.getenv("MONITOR_INTERVAL", "120"))

    scheduler = MonitoringScheduler(
        subreddits=[s.strip() for s in subreddits],
        keywords=[k.strip() for k in keywords],
        interval_minutes=interval,
        use_ai=args.ai
    )

    try:
        if args.once:
            print("Running monitoring cycle once...")
            scheduler.run_once()
        else:
            print(f"Starting scheduler (every {interval} minutes)")
            print("Press Ctrl+C to stop")
            scheduler.start()

            import time
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping scheduler...")
        if not args.once:
            scheduler.stop()


def cmd_stats(args):
    db = Database()
    stats = db.get_stats()

    print("\n📊 Database Statistics")
    print("=" * 40)
    print(f"Total Posts: {stats['total_posts']}")
    print(f"Relevant Posts: {stats['relevant_posts']}")
    print(f"Unique Subreddits: {stats['unique_subreddits']}")
    print(f"Monitoring Runs: {stats['monitoring_runs']}")

    if stats.get('top_subreddits'):
        print("\nTop Subreddits:")
        for sub, count in stats['top_subreddits'].items():
            print(f"  r/{sub}: {count} posts")


def cmd_search(args):
    client = RedditClient()
    db = Database()

    posts = client.search_posts(
        args.query,
        subreddit=args.subreddit,
        limit=args.limit,
        sort=args.sort
    )

    if not posts:
        print("No posts found.")
        return

    for post in posts:
        print(f"\n{post['title']}")
        print(f"  r/{post['subreddit']} | {post['score']} pts")
        print(f"  by {post['author']}")

        if args.store:
            post_id = db.insert_post(post)
            if post_id:
                print(f"  [Stored]")


def cmd_user(args):
    client = RedditClient()
    profile = client.get_user_profile(args.username)

    if not profile:
        print(f"User {args.username} not found.")
        return

    print(f"\n👤 {profile['username']}")
    print(f"  Link Karma: {profile['link_karma']}")
    print(f"  Comment Karma: {profile['comment_karma']}")
    print(f"  Account Age: {profile['account_age_days']} days")
    print(f"  Gold: {'Yes' if profile['is_gold'] else 'No'}")
    print(f"  Moderator: {'Yes' if profile['is_mod'] else 'No'}")


def cmd_subreddit(args):
    client = RedditClient()
    info = client.get_subreddit_info(args.name)

    if not info:
        print(f"Subreddit r/{args.name} not found.")
        return

    print(f"\n📍 r/{info['name']}")
    print(f"  Subscribers: {info['subscribers']:,}")
    print(f"  Type: {info['subreddit_type']}")
    print(f"  Private: {'Yes' if info['is_private'] else 'No'}")
    print(f"  Description: {info['description'][:100]}...")


def cmd_posts(args):
    db = Database()

    posts = db.get_posts(
        subreddit=args.subreddit,
        is_relevant=args.relevant,
        limit=args.limit,
        days_old=args.days
    )

    if not posts:
        print("No posts found.")
        return

    for post in posts:
        status = ""
        if post['is_relevant'] is not None:
            status = "✓" if post['is_relevant'] else "✗"

        print(f"\n{status} {post['title']}")
        print(f"  r/{post['subreddit']} | {post['score']} pts | {post['num_comments']} comments")
        print(f"  by {post['author']}")

        if post.get('relevance_score'):
            print(f"  Relevance: {post['relevance_score']:.2f}")


def main():
    parser = argparse.ArgumentParser(
        description="Reddit Community Reader - Monitor and analyze Reddit discussions"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    subparsers.add_parser("test", help="Test Reddit API connection")

    fetch_parser = subparsers.add_parser("fetch", help="Fetch posts from subreddit")
    fetch_parser.add_argument("subreddit", help="Subreddit to fetch from")
    fetch_parser.add_argument("-l", "--limit", type=int, default=10, help="Number of posts")
    fetch_parser.add_argument("-s", "--sort", default="new", help="Sort order (new, hot, top)")
    fetch_parser.add_argument("-j", "--json", action="store_true", help="JSON output")

    monitor_parser = subparsers.add_parser("monitor", help="Start monitoring")
    monitor_parser.add_argument("-a", "--ai", action="store_true", help="Use AI analysis")
    monitor_parser.add_argument("--once", action="store_true", help="Run once and exit")

    subparsers.add_parser("stats", help="Show database statistics")

    search_parser = subparsers.add_parser("search", help="Search Reddit posts")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("-s", "--subreddit", help="Limit to subreddit")
    search_parser.add_argument("-l", "--limit", type=int, default=10, help="Number of results")
    search_parser.add_argument("--sort", default="relevance", help="Sort order")
    search_parser.add_argument("--store", action="store_true", help="Store results in database")

    user_parser = subparsers.add_parser("user", help="Get user profile")
    user_parser.add_argument("username", help="Reddit username")

    sub_parser = subparsers.add_parser("subreddit", help="Get subreddit info")
    sub_parser.add_argument("name", help="Subreddit name (without r/)")

    posts_parser = subparsers.add_parser("posts", help="View stored posts")
    posts_parser.add_argument("-s", "--subreddit", help="Filter by subreddit")
    posts_parser.add_argument("-r", "--relevant", type=bool, help="Filter by relevance")
    posts_parser.add_argument("-l", "--limit", type=int, default=20, help="Number of posts")
    posts_parser.add_argument("-d", "--days", type=int, default=7, help="Days old")

    args = parser.parse_args()

    if args.command == "test":
        cmd_test(args)
    elif args.command == "fetch":
        cmd_fetch(args)
    elif args.command == "monitor":
        cmd_monitor(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "user":
        cmd_user(args)
    elif args.command == "subreddit":
        cmd_subreddit(args)
    elif args.command == "posts":
        cmd_posts(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
