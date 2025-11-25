# Reddit Community Reader

A personal tool for monitoring Reddit discussions in communities relevant to your expertise.

## Overview

**Reddit Community Reader** helps you stay engaged in Reddit communities without missing important conversations. Rather than manually scrolling, the tool:

- **Monitors** specified subreddits every 2 hours for new discussions
- **Filters** posts by relevance using keyword matching and optional AI analysis
- **Stores** everything locally for review and audit purposes
- **Enables** thoughtful, intentional community participation

All features are read-only. Any posting or responses remain fully manual—you review and approve before anything is published.

## Key Features

| Feature | Description |
|---------|-------------|
| **Read-only Monitoring** | Fetches public posts from target subreddits without modification |
| **Relevance Filtering** | Identifies posts matching your expertise using keywords and Claude AI |
| **Local Storage** | All data stored in SQLite locally—no external sharing or cloud sync |
| **Manual Approval** | Zero automated posting; every response requires human review |
| **Audit Logging** | Full activity logs for compliance and debugging |
| **Rate Limit Aware** | Built-in respects of Reddit's 60 req/min rate limits |
| **Scheduled Monitoring** | Configurable polling intervals (default: every 2 hours) |

## Technology Stack

| Component | Purpose |
|-----------|---------|
| **PRAW 7.7.1** | Official Reddit API wrapper for Python |
| **Python 3.11+** | Core language |
| **SQLite** | Lightweight local database |
| **APScheduler** | Background job scheduling |
| **LangChain + Claude** | Optional AI relevance analysis |
| **python-dotenv** | Environment variable management |

## Installation

### Prerequisites
- Python 3.11 or higher
- A Reddit account
- A Reddit Developer App (create one at https://www.reddit.com/prefs/apps)

### Setup

```bash
# Clone the repository
git clone https://github.com/your-username/reddit-agent.git
cd reddit-agent

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your Reddit credentials
```

## Configuration

### Reddit API Credentials

1. Go to https://www.reddit.com/prefs/apps
2. Click "Create App" or "Create Another App"
3. Select "script" as the app type
4. Note your **client_id** and **client_secret**

### Environment Variables

Create a `.env` file with:

```env
# Required: Reddit API credentials
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password
REDDIT_USER_AGENT=RedditCommunityReader/1.0 (by /u/your_username)

# Optional: For Claude AI integration
OPENAI_API_KEY=sk-your_key_here

# Configuration
TARGET_SUBREDDITS=SaaS,startup,indiehackers,entrepreneur
MONITOR_INTERVAL=120  # minutes between checks
KEYWORDS=feedback,customer,automation,scaling
```

## Usage

### Quick Start: Fetch Posts

```bash
# Fetch recent posts from r/SaaS
python src/main.py --subreddit SaaS

# Fetch with custom limit and sort order
python src/main.py --subreddit startup --limit 25 --sort hot
```

### Monitor for Relevant Discussions

```bash
# View monitoring statistics
python src/main.py --monitor

# Search for specific topics
python src/main.py --search "customer feedback" --subreddit SaaS
```

### Start Background Monitoring

```bash
# Runs scheduler with 2-hour polling intervals
python src/scheduler.py
```

The scheduler will:
- Check each configured subreddit every 2 hours
- Identify relevant posts by keywords
- Store results in `data.db`
- Log all activity to `logs/monitor.log`

### Output Formats

```bash
# Pretty-printed console output (default)
python src/main.py --subreddit SaaS

# JSON output for programmatic use
python src/main.py --subreddit SaaS --json
```

## Project Structure

```
reddit-agent/
├── src/
│   ├── __init__.py
│   ├── main.py              # CLI entry point
│   ├── scheduler.py         # Background job runner
│   ├── reddit_client.py     # PRAW wrapper for Reddit API
│   ├── database.py          # SQLite operations
│   └── ai_analyzer.py       # (Future) Claude integration
├── logs/                    # Monitoring logs
├── data.db                  # SQLite database
├── .env.example             # Environment template
├── .gitignore               # Git exclusions
├── requirements.txt         # Python dependencies
└── README.md                # This file
```
