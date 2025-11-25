import praw
import os
import time
import logging
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class RedditClientError(Exception):
    pass


class RedditClient:
    def __init__(self):
        try:
            self.reddit = praw.Reddit(
                client_id=os.getenv("REDDIT_CLIENT_ID"),
                client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
                user_agent=os.getenv("REDDIT_USER_AGENT"),
                username=os.getenv("REDDIT_USERNAME"),
                password=os.getenv("REDDIT_PASSWORD"),
            )
            self.rate_limit_reset = 0
            logger.info("RedditClient initialized")
        except Exception as e:
            logger.error(f"Failed to initialize RedditClient: {e}")
            raise RedditClientError(f"Authentication failed: {e}")

    def verify_connection(self) -> Dict:
        try:
            user = self.reddit.user.me()
            result = {
                "success": True,
                "username": user.name,
                "link_karma": user.link_karma,
                "comment_karma": user.comment_karma,
                "account_age_days": (datetime.now() - datetime.fromtimestamp(user.created_utc)).days,
                "message": f"✓ Authenticated as {user.name}"
            }
            logger.info(f"Connection verified: {user.name}")
            return result
        except praw.exceptions.InvalidToken:
            logger.error("Invalid authentication token")
            return {
                "success": False,
                "message": "Invalid credentials. Check your .env file."
            }
        except Exception as e:
            logger.error(f"Connection verification failed: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }

    def get_subreddit_posts(
        self,
        subreddit_name: str,
        limit: int = 25,
        sort: str = "new",
        time_filter: str = "day"
    ) -> List[Dict]:
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            _ = subreddit.display_name

            if sort == "top":
                submissions = subreddit.top(time_filter=time_filter, limit=limit)
            elif sort == "hot":
                submissions = subreddit.hot(limit=limit)
            elif sort == "rising":
                submissions = subreddit.rising(limit=limit)
            elif sort == "controversial":
                submissions = subreddit.controversial(time_filter=time_filter, limit=limit)
            else:
                submissions = subreddit.new(limit=limit)

            posts = []
            for submission in submissions:
                post = self._normalize_post(submission, subreddit_name)
                posts.append(post)

            logger.info(f"Fetched {len(posts)} posts from r/{subreddit_name}")
            return posts

        except praw.exceptions.InvalidSubreddit:
            logger.error(f"Subreddit not found: r/{subreddit_name}")
            raise RedditClientError(f"Subreddit r/{subreddit_name} not found")
        except praw.exceptions.Forbidden:
            logger.error(f"Access denied to r/{subreddit_name}")
            raise RedditClientError(f"Access denied to r/{subreddit_name}")
        except Exception as e:
            logger.error(f"Error fetching posts from r/{subreddit_name}: {e}")
            return []

    def get_post_comments(
        self,
        submission_id: str,
        limit: int = 10,
        sort: str = "best"
    ) -> List[Dict]:
        try:
            submission = self.reddit.submission(id=submission_id)
            submission.comments.replace_more(limit=0)
            submission.comment_sort = sort

            comments = []
            for i, comment in enumerate(submission.comments):
                if i >= limit:
                    break

                comment_data = {
                    "id": comment.id,
                    "author": comment.author.name if comment.author else "[deleted]",
                    "body": comment.body,
                    "score": comment.score,
                    "created_utc": comment.created_utc,
                    "is_submitter": comment.is_submitter,
                    "depth": comment.depth,
                }
                comments.append(comment_data)

            return comments

        except Exception as e:
            logger.error(f"Error fetching comments for {submission_id}: {e}")
            return []

    def search_posts(
        self,
        query: str,
        subreddit: Optional[str] = None,
        limit: int = 25,
        sort: str = "relevance",
        time_filter: str = "all"
    ) -> List[Dict]:
        try:
            if subreddit:
                sub = self.reddit.subreddit(subreddit)
                search_results = sub.search(
                    query,
                    sort=sort,
                    time_filter=time_filter,
                    limit=limit
                )
            else:
                search_results = self.reddit.subreddit("all").search(
                    query,
                    sort=sort,
                    time_filter=time_filter,
                    limit=limit
                )

            posts = []
            for submission in search_results:
                post = self._normalize_post(submission)
                posts.append(post)

            logger.info(f"Found {len(posts)} posts matching '{query}'")
            return posts

        except Exception as e:
            logger.error(f"Error searching for '{query}': {e}")
            return []

    def get_user_profile(self, username: str) -> Dict:
        try:
            user = self.reddit.redditor(username)
            profile = {
                "username": user.name,
                "link_karma": user.link_karma,
                "comment_karma": user.comment_karma,
                "account_age_days": (datetime.now() - datetime.fromtimestamp(user.created_utc)).days,
                "is_gold": user.is_gold,
                "is_mod": len(user.moderated()) > 0,
            }
            return profile
        except Exception as e:
            logger.error(f"Error fetching user {username}: {e}")
            return {}

    def get_subreddit_info(self, subreddit_name: str) -> Dict:
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            info = {
                "name": subreddit.display_name,
                "subscribers": subreddit.subscribers,
                "description": subreddit.public_description,
                "created_utc": subreddit.created_utc,
                "is_private": subreddit.private,
                "subreddit_type": subreddit.subreddit_type,
            }
            return info
        except Exception as e:
            logger.error(f"Error fetching subreddit info: {e}")
            return {}

    @staticmethod
    def _normalize_post(submission, subreddit_name: str = None) -> Dict:
        return {
            "id": submission.id,
            "title": submission.title,
            "selftext": submission.selftext,
            "subreddit": subreddit_name or submission.subreddit.display_name,
            "author": submission.author.name if submission.author else "[deleted]",
            "score": submission.score,
            "upvote_ratio": submission.upvote_ratio,
            "num_comments": submission.num_comments,
            "created_utc": submission.created_utc,
            "edited": submission.edited,
            "is_self": submission.is_self,
            "url": submission.url,
            "permalink": f"https://reddit.com{submission.permalink}",
            "fetched_at": datetime.now().isoformat(),
        }

    def handle_rate_limit(self):
        try:
            pass
        except praw.exceptions.ResponseException as e:
            if e.response.status_code == 429:
                logger.warning("Rate limit hit. Waiting...")
                time.sleep(60)
