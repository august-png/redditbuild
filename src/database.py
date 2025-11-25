import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    pass


class Database:
    def __init__(self, db_path: str = "reddit_data.db"):
        self.db_path = db_path
        self._init_tables()
        logger.info(f"Database initialized: {db_path}")

    def _init_tables(self):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reddit_id TEXT UNIQUE NOT NULL,
                    subreddit TEXT NOT NULL,
                    title TEXT NOT NULL,
                    selftext TEXT,
                    author TEXT,
                    score INTEGER DEFAULT 0,
                    upvote_ratio REAL DEFAULT 0.5,
                    num_comments INTEGER DEFAULT 0,
                    created_utc REAL NOT NULL,
                    url TEXT,
                    permalink TEXT,
                    is_self BOOLEAN DEFAULT 1,
                    fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_relevant BOOLEAN DEFAULT NULL,
                    relevance_score REAL DEFAULT NULL,
                    keywords_found TEXT,
                    manually_marked BOOLEAN DEFAULT 0
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER NOT NULL,
                    analysis_type TEXT,
                    analysis_result TEXT,
                    confidence_score REAL,
                    analyzed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(post_id) REFERENCES posts(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS monitoring_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subreddit TEXT NOT NULL,
                    posts_fetched INTEGER DEFAULT 0,
                    posts_stored INTEGER DEFAULT 0,
                    posts_relevant INTEGER DEFAULT 0,
                    run_duration_seconds REAL,
                    errors TEXT,
                    run_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_reddit_id ON posts(reddit_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_subreddit ON posts(subreddit)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_is_relevant ON posts(is_relevant)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_utc ON posts(created_utc)
            """)

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Failed to initialize tables: {e}")
            raise DatabaseError(f"Database initialization failed: {e}")

    def insert_post(self, post_data: Dict) -> Optional[int]:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO posts (
                    reddit_id, subreddit, title, selftext, author,
                    score, upvote_ratio, num_comments, created_utc,
                    url, permalink, is_self
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                post_data.get("id"),
                post_data.get("subreddit"),
                post_data.get("title"),
                post_data.get("selftext", ""),
                post_data.get("author"),
                post_data.get("score", 0),
                post_data.get("upvote_ratio", 0.5),
                post_data.get("num_comments", 0),
                post_data.get("created_utc"),
                post_data.get("url"),
                post_data.get("permalink"),
                post_data.get("is_self", 1),
            ))

            conn.commit()
            row_id = cursor.lastrowid
            conn.close()

            logger.debug(f"Inserted post: {post_data.get('title')[:50]}")
            return row_id

        except sqlite3.IntegrityError:
            logger.debug(f"Post already exists: {post_data.get('reddit_id')}")
            return None
        except Exception as e:
            logger.error(f"Error inserting post: {e}")
            return None

    def mark_relevant(self, post_id: int, is_relevant: bool, score: float, keywords: List[str] = None):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            keywords_str = json.dumps(keywords) if keywords else None

            cursor.execute("""
                UPDATE posts
                SET is_relevant = ?, relevance_score = ?, keywords_found = ?, manually_marked = 0
                WHERE id = ?
            """, (is_relevant, score, keywords_str, post_id))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Error marking post as relevant: {e}")

    def get_posts(
        self,
        subreddit: Optional[str] = None,
        is_relevant: Optional[bool] = None,
        limit: int = 50,
        days_old: int = 7
    ) -> List[Dict]:
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM posts WHERE 1=1"
            params = []

            if subreddit:
                query += " AND subreddit = ?"
                params.append(subreddit)

            if is_relevant is not None:
                query += " AND is_relevant = ?"
                params.append(is_relevant)

            query += " AND created_utc > ?"
            cutoff_time = (datetime.now() - timedelta(days=days_old)).timestamp()
            params.append(cutoff_time)

            query += " ORDER BY created_utc DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            posts = []
            for row in rows:
                post = dict(row)
                if post.get("keywords_found"):
                    post["keywords_found"] = json.loads(post["keywords_found"])
                posts.append(post)

            return posts

        except Exception as e:
            logger.error(f"Error fetching posts: {e}")
            return []

    def log_monitoring_run(
        self,
        subreddit: str,
        posts_fetched: int,
        posts_stored: int,
        posts_relevant: int,
        duration_seconds: float,
        errors: Optional[str] = None
    ):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO monitoring_runs (
                    subreddit, posts_fetched, posts_stored,
                    posts_relevant, run_duration_seconds, errors
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (subreddit, posts_fetched, posts_stored, posts_relevant, duration_seconds, errors))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Error logging monitoring run: {e}")

    def get_stats(self) -> Dict:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            stats = {}

            cursor.execute("SELECT COUNT(*) FROM posts")
            stats["total_posts"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM posts WHERE is_relevant = 1")
            stats["relevant_posts"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(DISTINCT subreddit) FROM posts")
            stats["unique_subreddits"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM monitoring_runs")
            stats["monitoring_runs"] = cursor.fetchone()[0]

            cursor.execute("""
                SELECT subreddit, COUNT(*) as count FROM posts
                GROUP BY subreddit ORDER BY count DESC LIMIT 5
            """)
            stats["top_subreddits"] = {row[0]: row[1] for row in cursor.fetchall()}

            conn.close()
            return stats

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}

    def cleanup_old(self, days: int = 30):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cutoff_time = (datetime.now() - timedelta(days=days)).timestamp()

            cursor.execute("DELETE FROM posts WHERE created_utc < ?", (cutoff_time,))
            deleted = cursor.rowcount

            conn.commit()
            conn.close()

            logger.info(f"Cleaned up {deleted} posts older than {days} days")
            return deleted

        except Exception as e:
            logger.error(f"Error cleaning up database: {e}")
            return 0
