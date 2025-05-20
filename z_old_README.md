# Reddit LLM Usage Data Collector

This tool collects posts and comments from AI/LLM-focused subreddits to analyze discussion trends about various LLM models and their use cases.

## Overview

The script `fetch_reddit_data.py` collects posts from each subreddit listed in `subreddits.txt` and saves them as markdown files organized by date. By default, it fetches the 40 newest posts (configurable in `.env` file), and each file contains a post and all its comments, formatted for easy analysis.

## How It Works

1. The script reads a list of subreddits from `subreddits.txt`
2. Creates a date-based folder in the `data/text_data` directory
3. For each subreddit, fetches posts based on sort method (new, top, etc.)
4. For each post, fetches all comments
5. Saves each post with its comments as a JSON file
6. Creates an index.json file with metadata about all collected posts

## File Organization

- `text_data/`: Main data directory
  - `MM-DD-YYYY/`: Folders organized by date
    - `subreddit_postid.json`: Individual post files (JSON format)
    - `index.json`: Index file with metadata about all posts

## Running the Script

```bash
python fetch_reddit_data.py
```

### Configuration Options

Edit the `.env` file to customize:

- `REDDIT_POST_SORT`: Sorting method for posts (options: `new`, `top`, `hot`, `rising`, `controversial`)
- `POSTS_PER_SUBREDDIT`: Number of posts to fetch per subreddit (default: 40)

## Features

- **Error handling**: Exponential backoff for rate limit errors
- **Progress logging**: Detailed terminal output during execution
- **JSON output**: Structured data for easy parsing and analysis
- **Index file**: Comprehensive listing of all collected data

## Data Structure

### Post JSON Format

```json
{
  "title": "Post Title",
  "author": "username",
  "url": "https://www.reddit.com/r/subreddit/comments/postid/title/",
  "id": "postid",
  "created_utc": 1747082137.0,
  "created_date": "2025-05-12 15:30:45",
  "subreddit": "subreddit",
  "score": 42,
  "upvote_ratio": 0.95,
  "selftext": "Post content here...",
  "comments": [
    {
      "author": "commenter",
      "id": "commentid",
      "created_utc": 1747082200.0,
      "created_date": "2025-05-12 15:32:12",
      "body": "Comment text here...",
      "score": 12,
      "is_submitter": false
    }
  ]
}
```

### Index JSON Format

```json
{
  "collected_date": "2025-05-13",
  "post_count": 42,
  "subreddits": ["ChatGPT", "ClaudeAI", "LLMDevs"],
  "posts": [
    {
      "filename": "ChatGPT_abc123.json",
      "subreddit": "ChatGPT",
      "post_id": "abc123",
      "title": "Post Title",
      "url": "https://www.reddit.com/r/ChatGPT/comments/abc123/post_title/",
      "created_utc": 1747082137.0,
      "created_date": "2025-05-12 15:30:45",
      "comment_count": 12
    }
  ]
}

## Next Steps

After collecting the data, you can use an LLM to analyze each file to:

1. Identify which LLM models are mentioned (GPT-4, Claude, Gemini, etc.)
2. Extract tasks associated with each model (coding, debugging, etc.)
3. Analyze sentiment toward different model-task pairings
4. Generate insights about which models are preferred for which tasks

For future versions, consider adding:

- Automated comment thread analysis with proper parent-child relationships
- Sentiment scoring for comments mentioning specific models
- Tracking new model mentions over time
```
