import logging
from typing import List, Dict, Tuple
import re

logger = logging.getLogger(__name__)


class Analyzer:
    def __init__(self, keywords: List[str], use_ai: bool = False):
        self.keywords = [k.lower() for k in keywords]
        self.use_ai = use_ai
        self.ai_client = None

        if use_ai:
            try:
                from langchain_openai import ChatOpenAI
                self.ai_client = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
                logger.info("AI analyzer initialized")
            except ImportError:
                logger.warning("LangChain not installed. Disabling AI analysis.")
                self.use_ai = False

    def analyze(self, post: Dict) -> Tuple[bool, float, List[str]]:
        is_relevant, score, keywords = self._keyword_match(post)

        if self.use_ai and is_relevant:
            ai_score = self._ai_analyze(post)
            score = (score + ai_score) / 2

        return is_relevant, score, keywords

    def _keyword_match(self, post: Dict) -> Tuple[bool, float, List[str]]:
        text = (
            post.get("title", "") + " " +
            post.get("selftext", "")
        ).lower()

        matched = []
        for keyword in self.keywords:
            if keyword in text:
                matched.append(keyword)

        if matched:
            score = min(len(matched) / max(len(self.keywords), 1), 1.0)
            return True, score, matched
        else:
            return False, 0.0, []

    def _ai_analyze(self, post: Dict) -> float:
        try:
            prompt = f"""
Post Title: {post.get('title')}
Post Content: {post.get('selftext', '')[:500]}

Keywords I care about: {', '.join(self.keywords)}

Rate how relevant this post is to those keywords on a scale of 0-1.
Respond with just a number between 0 and 1.
"""

            response = self.ai_client.invoke(prompt)
            try:
                score = float(response.content.strip())
                return max(0, min(1, score))
            except:
                return 0.5
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return 0.5
