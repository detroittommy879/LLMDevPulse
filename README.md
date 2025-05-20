# Reddit Data Collection and Markdown Export

This project provides tools for collecting Reddit posts and comments from specified subreddits and exporting them in Markdown format.

## Scripts Overview

### 1. `fetch_reddit_data.py`

**Purpose:**  
Fetches posts and comments from a list of subreddits and saves them as structured JSON files and in a SQLite database.

**Features:**

- Reads subreddit names from `subreddits.txt`.
- Fetches recent posts (configurable via environment variables).
- Retrieves comments for each post up to a configurable depth.
- Saves each post (with comments) as a JSON file in a date-based folder.
- Stores all posts and comments in a SQLite database (`data/reddit_data.db` by default).
- Creates an index file summarizing the collected data.
- Supports configuration via `.env` file (API limits, folder paths, etc.).

### 2. `export_reddit_text.py`

**Purpose:**  
Exports posts and their threaded comments from the SQLite database to a Markdown file, using blockquote indentation to represent comment nesting.

**Features:**

- Connects to the SQLite database created by `fetch_reddit_data.py`.
- Extracts posts and comments within a user-specified date range.
- Outputs data to a Markdown file, with each post as a section and comments shown as indented blockquotes (using `>`).
- Preserves comment threading and author information.
- Supports command-line arguments for date range, output file path, and database path.
- Useful for preparing Reddit data for sharing, documentation, or further Markdown-based processing.

## Typical Workflow

1. **Collect Data:**  
   Run `fetch_reddit_data.py` to gather Reddit posts and comments from your target subreddits.

2. **Export Data:**  
   Use `export_reddit_text.py` to extract and format the collected data as Markdown.

## Requirements

- Python 3.6+
- Dependencies listed in `requirements.txt`
- Reddit API access (no authentication required for public data, but user-agent is required)

## Configuration

Use the `.env` file to set environment variables such as:

- `REDDIT_USER_AGENT`
- `POSTS_PER_SUBREDDIT`
- `REDDIT_POST_SORT`
- `REDDIT_DB_PATH`
- `TEXT_DATA_FOLDER`
- `REDDIT_COMMENT_DEPTH`

## License

See `LICENSE` file if present.
