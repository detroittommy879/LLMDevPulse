#!/usr/bin/env python3
"""
Reddit Data Fetcher

This script fetches posts and comments from specified subreddits (listed in subreddits.txt), saves each post (with comments) as a JSON file in a date-based folder, and stores all posts and comments in a SQLite database. It handles Reddit API rate limiting, supports configuration via environment variables, and creates an index file summarizing the collected data.

Features:
- Reads subreddit names from subreddits.txt (ignores comments and blank lines).
- Fetches recent posts from each subreddit (number and sort order configurable).
- Retrieves comments for each post up to a configurable depth.
- Saves each post (with comments) as a JSON file in a date-based folder.
- Stores all posts and comments in a SQLite database (default: data/reddit_data.db).
- Creates an index.json file summarizing the day's collected data.
- Supports configuration via .env file (API limits, folder paths, etc.).
- Handles Reddit API rate limiting with exponential backoff.

Usage:
    python fetch_reddit_data.py

Environment Variables (set in .env):
    REDDIT_USER_AGENT      - User-Agent string for Reddit API requests (required).
    POSTS_PER_SUBREDDIT    - Number of posts to fetch per subreddit (default: 40).
    REDDIT_POST_SORT       - Post sorting method: "new", "top", etc. (default: "new").
    REDDIT_DB_PATH         - Path to SQLite database (default: data/reddit_data.db).
    TEXT_DATA_FOLDER       - Base folder for saving JSON files (default: text_data).
    REDDIT_COMMENT_DEPTH   - Max depth for comment fetching (default: 8).

Outputs:
    - JSON files for each post (with comments) in a dated folder.
    - SQLite database with posts and comments.
    - index.json summarizing the day's collection.
"""

import os
import time
import json
import logging
import requests
import datetime
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Constants
USER_AGENT = os.getenv("REDDIT_USER_AGENT", "LLMUsageResearchBot/1.0")
BASE_URL = "https://www.reddit.com"
POSTS_PER_SUBREDDIT = int(os.getenv("POSTS_PER_SUBREDDIT", "40"))
INITIAL_BACKOFF = 61  # seconds (starting with 61 seconds)
MAX_BACKOFF = 3600  # 1 hour (increased from 10 minutes)
# Post sorting method (default to "new" if not specified)
POST_SORT_METHOD = os.getenv("REDDIT_POST_SORT", "new")
DB_PATH = os.getenv("REDDIT_DB_PATH", "data/reddit_data.db")

# New constants for comment fetching depth
DEFAULT_COMMENT_DEPTH = 8  # Default depth if not specified in .env
REDDIT_COMMENT_LIMIT = 2000 # Max comments to request in one go (API has its own caps)

def init_db(db_path: str):
    """Initialize the SQLite3 database and create tables if they don't exist."""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id TEXT PRIMARY KEY,
            subreddit TEXT,
            title TEXT,
            author TEXT,
            url TEXT,
            created_utc INTEGER,
            created_date TEXT,
            score INTEGER,
            upvote_ratio REAL,
            selftext TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id TEXT PRIMARY KEY,
            post_id TEXT,
            parent_id TEXT,
            author TEXT,
            created_utc INTEGER,
            created_date TEXT,
            body TEXT,
            score INTEGER,
            is_submitter BOOLEAN,
            awards TEXT,
            FOREIGN KEY(post_id) REFERENCES posts(id)
        )
    """)
    conn.commit()
    return conn


def read_subreddits(file_path: str) -> List[str]:
    """Read subreddit names from a file, skipping comments and empty lines."""
    subreddits = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('//'):
                subreddits.append(line)
    return subreddits


def create_date_folder() -> Path:
    """Create and return a folder path based on today's date and TEXT_DATA_FOLDER env variable."""
    today = datetime.datetime.now()
    date_folder = f"{today.month:02d}-{today.day:02d}-{today.year}"
    base_folder = os.getenv("TEXT_DATA_FOLDER", "text_data")
    folder_path = Path(base_folder) / date_folder
    folder_path.mkdir(parents=True, exist_ok=True)
    return folder_path


def get_headers() -> Dict[str, str]:
    """Return headers for Reddit API requests."""
    return {
        "User-Agent": USER_AGENT
    }


def fetch_with_backoff(url: str) -> Optional[Dict[str, Any]]:
    """Fetch data from Reddit API with exponential backoff for rate limiting.
    Keeps retrying indefinitely with increasing wait times."""
    backoff = INITIAL_BACKOFF
    attempt = 1
    
    while True:  # No limit on retries - will keep trying until successful
        try:
            response = requests.get(url, headers=get_headers())
            
            # Check if we're being rate limited
            if response.status_code == 429:
                # Use Retry-After header if available, otherwise use our backoff
                wait_time = int(response.headers.get('Retry-After', backoff))
                logger.warning(f"Rate limited. Waiting {wait_time} seconds (attempt {attempt})")
                time.sleep(wait_time)
                # Double the backoff for next time, capped at MAX_BACKOFF
                backoff = min(backoff * 2, MAX_BACKOFF)
                attempt += 1
                continue
                
            # Check for other errors
            if response.status_code != 200:
                logger.error(f"Error fetching {url}: Status code {response.status_code}")
                logger.warning(f"Retrying in {backoff} seconds (attempt {attempt})")
                time.sleep(backoff)
                backoff = min(backoff * 2, MAX_BACKOFF)
                attempt += 1
                continue
                
            # Success! Return the JSON data
            logger.info(f"Successfully fetched data after {attempt} attempt(s)")
            return response.json()
            
        except Exception as e:
            logger.error(f"Exception when fetching {url}: {str(e)}")
            logger.warning(f"Retrying in {backoff} seconds (attempt {attempt})")
            time.sleep(backoff)
            backoff = min(backoff * 2, MAX_BACKOFF)
            attempt += 1


def fetch_posts(subreddit: str) -> List[Dict[str, Any]]:
    """Fetch posts from a subreddit based on the sorting method."""
    url = f"{BASE_URL}/r/{subreddit}/{POST_SORT_METHOD}.json?limit={POSTS_PER_SUBREDDIT}"
    
    # Add time parameter for 'top' sorting only
    if POST_SORT_METHOD == "top":
        url += "&t=month"
        
    logger.info(f"Fetching {POST_SORT_METHOD} posts from r/{subreddit}")
    
    response_data = fetch_with_backoff(url)
    if not response_data:
        logger.error(f"Could not fetch posts from r/{subreddit}")
        return []
    
    posts = []
    for post in response_data.get('data', {}).get('children', []):
        posts.append(post.get('data', {}))
    
    logger.info(f"Retrieved {len(posts)} posts from r/{subreddit}")
    return posts


def _extract_replies_recursive(comment_api_obj: Dict[str, Any], current_depth: int, max_depth: int) -> List[Dict[str, Any]]:
    """
    Recursively extracts a comment and its replies from a Reddit comment API object.
    Skips 'more' comment objects for simplicity in this version.

    Args:
        comment_api_obj: A dict representing a comment object from the Reddit API
                         (e.g., an item from a 'children' list like {'kind': 't1', 'data': {...}}).
        current_depth: The current depth of this comment in the recursion.
        max_depth: The maximum depth to recurse.

    Returns:
        A flat list of comment data dictionaries.
    """
    flat_list_of_comments = []

    if not isinstance(comment_api_obj, dict):
        return flat_list_of_comments

    kind = comment_api_obj.get('kind')
    
    # We only process actual comments ('t1').
    # 'more' objects would require additional API calls to expand, which adds complexity.
    # We'll rely on the initial fetch depth to get most of what we need.
    if kind != 't1':
        if kind == 'more':
            logger.debug(f"Skipping 'more' comments object at depth {current_depth}. ID: {comment_api_obj.get('data', {}).get('name')}, Count: {comment_api_obj.get('data', {}).get('count')}")
        return flat_list_of_comments

    actual_comment_data = comment_api_obj.get('data')
    if not actual_comment_data or not isinstance(actual_comment_data, dict):
        return flat_list_of_comments

    # Add the current comment's data
    flat_list_of_comments.append(actual_comment_data)

    # If we haven't reached max_depth, process its replies
    if current_depth < max_depth:
        replies_listing = actual_comment_data.get('replies')
        # Ensure replies_listing is a dict (it's a Listing object from Reddit API)
        if replies_listing and isinstance(replies_listing, dict):
            reply_data_container = replies_listing.get('data')
            if reply_data_container and isinstance(reply_data_container, dict):
                reply_children = reply_data_container.get('children')
                if reply_children and isinstance(reply_children, list):
                    for reply_child_api_obj in reply_children:
                        flat_list_of_comments.extend(
                            _extract_replies_recursive(reply_child_api_obj, current_depth + 1, max_depth)
                        )
    elif current_depth == max_depth and actual_comment_data.get('replies'):
        # Log if we are cutting off replies due to depth limit
        logger.debug(f"Max depth {max_depth} reached. Not processing further replies for comment ID {actual_comment_data.get('id')}")
        
    return flat_list_of_comments

def fetch_comments(post_id: str, subreddit: str, max_depth: int) -> List[Dict[str, Any]]:
    """
    Fetch comments for a specific post, attempting to get replies up to max_depth.
    """
    # Construct URL with depth and limit parameters
    # The 'limit' here often refers to the number of top-level items, 
    # 'depth' controls how many levels of replies are included for those items.
    # Reddit API's behavior can be nuanced. Max depth is often capped by API (e.g., 8-15).
    url = f"{BASE_URL}/r/{subreddit}/comments/{post_id}.json?limit={REDDIT_COMMENT_LIMIT}&depth={max_depth}&sort=top"
    # You can change 'sort' to 'new', 'confidence', 'qa', etc. 'top' is often good for capturing significant threads.
    
    logger.info(f"Fetching comments for post {post_id} in r/{subreddit} (max_depth={max_depth}, limit={REDDIT_COMMENT_LIMIT})")
    
    response_data = fetch_with_backoff(url)
    if not response_data or len(response_data) < 2:
        logger.error(f"Could not fetch comments for post {post_id}. Response was empty or malformed.")
        return []
    
    # The second object in the response is the comment listing
    top_level_comment_listing_children = response_data[1].get('data', {}).get('children', [])
    
    all_comments_from_post = []
    for comment_api_obj in top_level_comment_listing_children:
        # Start recursion at depth 1 for top-level items from the API
        all_comments_from_post.extend(
            _extract_replies_recursive(comment_api_obj, current_depth=1, max_depth=max_depth)
        )
    
    logger.info(f"Retrieved {len(all_comments_from_post)} comments (including replies up to depth {max_depth}) for post {post_id}")
    return all_comments_from_post


def prepare_post_json(post: Dict[str, Any], comments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Prepare a structured JSON object with post and comments data."""
    created_utc = post.get('created_utc', 0)
    created_date = datetime.datetime.fromtimestamp(created_utc).strftime('%Y-%m-%d %H:%M:%S')
    
    # Format the comments to include only necessary data
    formatted_comments = []
    for comment in comments:
        comment_utc = comment.get('created_utc', 0)
        comment_date = datetime.datetime.fromtimestamp(comment_utc).strftime('%Y-%m-%d %H:%M:%S')
        
        formatted_comments.append({
            'author': comment.get('author', '[deleted]'),
            'id': comment.get('id', 'unknown'),
            'created_utc': comment_utc,
            'created_date': comment_date,
            'body': comment.get('body', '[No content]'),
            'score': comment.get('score', 0),
            'is_submitter': comment.get('is_submitter', False),
            'awards': comment.get('all_awardings', []),
        })
    
    # Create the post JSON structure
    post_data = {
        'title': post.get('title', 'Untitled Post'),
        'author': post.get('author', '[deleted]'),
        'url': f"{BASE_URL}{post.get('permalink', '')}",
        'id': post.get('id', 'unknown'),
        'created_utc': created_utc,
        'created_date': created_date,
        'subreddit': post.get('subreddit', 'unknown'),
        'score': post.get('score', 0),
        'upvote_ratio': post.get('upvote_ratio', 0),
        'selftext': post.get('selftext', '[No content]'),
        'comments': formatted_comments
    }
    
    return post_data


def save_post_as_file(post: Dict[str, Any], comments: List[Dict[str, Any]], folder_path: Path, db_conn) -> Dict[str, Any]:
    """Save a post and its comments as a JSON file and to the database, then return index data."""
    subreddit = post.get('subreddit', 'unknown')
    post_id = post.get('id', 'unknown')

    # Insert post into database
    try:
        db_conn.execute(
            """
            INSERT OR REPLACE INTO posts (id, subreddit, title, author, url, created_utc, created_date, score, upvote_ratio, selftext)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                post_id,
                subreddit,
                post.get('title', 'Untitled Post'),
                post.get('author', '[deleted]'),
                f"{BASE_URL}{post.get('permalink', '')}",
                post.get('created_utc', 0),
                datetime.datetime.fromtimestamp(post.get('created_utc', 0)).strftime('%Y-%m-%d %H:%M:%S'),
                post.get('score', 0),
                post.get('upvote_ratio', 0),
                post.get('selftext', '[No content]')
            )
        )
        db_conn.commit()
    except Exception as e:
        logger.error(f"Error inserting post {post_id} into database: {e}")

    # Insert comments into database
    for comment in comments:
        comment_id = comment.get('id', 'unknown')
        parent_id = comment.get('parent_id', None)
        if parent_id and parent_id.startswith('t3_'):
            parent_id = parent_id[3:]  # Remove t3_ prefix for post
        elif parent_id and parent_id.startswith('t1_'):
            parent_id = parent_id[3:]  # Remove t1_ prefix for comment

        try:
            db_conn.execute(
                """
                INSERT OR REPLACE INTO comments (id, post_id, parent_id, author, created_utc, created_date, body, score, is_submitter, awards)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    comment_id,
                    post_id,
                    parent_id,
                    comment.get('author', '[deleted]'),
                    comment.get('created_utc', 0),
                    datetime.datetime.fromtimestamp(comment.get('created_utc', 0)).strftime('%Y-%m-%d %H:%M:%S'),
                    comment.get('body', '[No content]'),
                    comment.get('score', 0),
                    int(comment.get('is_submitter', False)),
                    json.dumps(comment.get('all_awardings', []))
                )
            )
        except Exception as e:
            logger.error(f"Error inserting comment {comment_id} for post {post_id} into database: {e}")
    db_conn.commit()

    # Create a filename based on subreddit and post ID
    filename = f"{subreddit}_{post_id}.json"
    file_path = folder_path / filename

    # Prepare the data
    post_data = prepare_post_json(post, comments)

    # Save as JSON
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(post_data, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved post {post_id} to {file_path} and database")

    # Return data for the index
    return {
        'filename': filename,
        'subreddit': subreddit,
        'post_id': post_id,
        'title': post.get('title', 'Untitled Post'),
        'url': f"{BASE_URL}{post.get('permalink', '')}",
        'created_utc': post.get('created_utc', 0),
        'created_date': datetime.datetime.fromtimestamp(post.get('created_utc', 0)).strftime('%Y-%m-%d %H:%M:%S'),
        'comment_count': len(comments)
    }


def main():
    """Main function to process all subreddits and save data."""
    logger.info("Starting Reddit data collection")

    # Initialize database
    db_conn = init_db(DB_PATH)

    # Read subreddits from file
    try:
        subreddits = read_subreddits('subreddits.txt')
        logger.info(f"Found {len(subreddits)} subreddits to process")

        # Print out the list of subreddits that will be processed
        print("\nSubreddits that will be processed:")
        for i, subreddit in enumerate(subreddits, 1):
            print(f"{i}. r/{subreddit}")
        print()  # Extra line for better readability

    except Exception as e:
        logger.error(f"Error reading subreddits.txt: {str(e)}")
        return

    # Create today's folder
    date_folder = create_date_folder()
    logger.info(f"Saving files to {date_folder}")

    # List to hold index data for all posts
    index_data = []

    # Determine comment depth from environment variable (after load_dotenv())
    try:
        comment_depth_str = os.getenv("REDDIT_COMMENT_DEPTH")
        if comment_depth_str is None:
            logger.info(f"REDDIT_COMMENT_DEPTH not set, using default: {DEFAULT_COMMENT_DEPTH}")
            actual_comment_depth = DEFAULT_COMMENT_DEPTH
        else:
            actual_comment_depth = int(comment_depth_str)
            if actual_comment_depth < 0:
                logger.warning(f"REDDIT_COMMENT_DEPTH ({actual_comment_depth}) is invalid, using default: {DEFAULT_COMMENT_DEPTH}")
                actual_comment_depth = DEFAULT_COMMENT_DEPTH
            else:
                logger.info(f"Using REDDIT_COMMENT_DEPTH: {actual_comment_depth}")
    except ValueError:
        logger.warning(f"Invalid value for REDDIT_COMMENT_DEPTH: '{comment_depth_str}'. Using default: {DEFAULT_COMMENT_DEPTH}")
        actual_comment_depth = DEFAULT_COMMENT_DEPTH

    # Process each subreddit
    for subreddit in subreddits:
        logger.info(f"Processing r/{subreddit}")
        posts = fetch_posts(subreddit)

        for post in posts:
            post_id = post.get('id')
            if not post_id:
                continue

            # Add a small delay between requests to avoid rate limiting
            time.sleep(1)

            # Pass the resolved actual_comment_depth here
            comments = fetch_comments(post_id, subreddit, actual_comment_depth)
            post_index_entry = save_post_as_file(post, comments, date_folder, db_conn)
            index_data.append(post_index_entry)

        # Be nice to Reddit's servers
        logger.info(f"Finished processing r/{subreddit}, waiting before next subreddit")
        time.sleep(2)

    # Create index file
    index_file_path = date_folder / "index.json"
    with open(index_file_path, 'w', encoding='utf-8') as f:
        json.dump({
            'collected_date': datetime.datetime.now().strftime('%Y-%m-%d'),
            'post_count': len(index_data),
            'subreddits': list(set(item['subreddit'] for item in index_data)),
            'posts': index_data
        }, f, indent=2, ensure_ascii=False)
    logger.info(f"Created index file at {index_file_path}")

    logger.info("Data collection complete!")


if __name__ == "__main__":
    main()
