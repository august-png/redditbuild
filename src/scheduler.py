import logging
import time
from datetime import datetime
from typing import List
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from reddit_client import RedditClient
from database import Database
from analyzer import Analyzer

logger = logging.getLogger(__name__)


class MonitoringScheduler:
    def __init__(
        self,
        subreddits: List[str],
        keywords: List[str],
        interval_minutes: int = 120,
        use_ai: bool = False
    ):
        self.subreddits = subreddits
        self.keywords = keywords
        self.interval_minutes = interval_minutes

        self.client = RedditClient()
        self.db = Database()
        self.analyzer = Analyzer(keywords, use_ai=use_ai)

        self.scheduler = BackgroundScheduler()
        logger.info(f"Scheduler initialized for {len(subreddits)} subreddits")

    def run_monitoring_cycle(self):
        start_time = time.time()
        logger.info("Starting monitoring cycle")

        for subreddit in self.subreddits:
            try:
                self._monitor_subreddit(subreddit)
            except Exception as e:
                logger.error(f"Error monitoring r/{subreddit}: {e}")

        duration = time.time() - start_time
        logger.info(f"Monitoring cycle complete ({duration:.2f}s)")

    def _monitor_subreddit(self, subreddit: str):
        logger.info(f"Monitoring r/{subreddit}")

        try:
            posts = self.client.get_subreddit_posts(subreddit, limit=25, sort="new")

            stored = 0
            relevant = 0

            for post in posts:
                post_id = self.db.insert_post(post)
                if post_id:
                    stored += 1

                    is_relevant, score, keywords = self.analyzer.analyze(post)

                    if is_relevant:
                        self.db.mark_relevant(post_id, True, score, keywords)
                        relevant += 1
                        logger.info(f"  ✓ Relevant: {post['title'][:50]}... ({score:.2f})")

            self.db.log_monitoring_run(
                subreddit,
                posts_fetched=len(posts),
                posts_stored=stored,
                posts_relevant=relevant,
                duration_seconds=0,
            )

            logger.info(f"  Fetched: {len(posts)}, Stored: {stored}, Relevant: {relevant}")

        except Exception as e:
            logger.error(f"Error monitoring r/{subreddit}: {e}")
            self.db.log_monitoring_run(
                subreddit,
                posts_fetched=0,
                posts_stored=0,
                posts_relevant=0,
                duration_seconds=0,
                errors=str(e),
            )

    def start(self):
        self.scheduler.add_job(
            self.run_monitoring_cycle,
            trigger=IntervalTrigger(minutes=self.interval_minutes),
            id="reddit_monitor",
            name="Reddit Community Monitor",
            replace_existing=True,
            max_instances=1,
        )

        self.scheduler.start()
        logger.info(f"Scheduler started (interval: {self.interval_minutes} minutes)")

    def stop(self):
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")

    def run_once(self):
        self.run_monitoring_cycle()
