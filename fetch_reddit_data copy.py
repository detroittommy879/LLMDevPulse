#!/usr/bin/env python3
"""
Reddit Data Fetcher

This script fetches posts and comments from specified subreddits and saves them
as text files organized by date.
"""

import os
import time
import json
import logging
import requests
import datetime
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


def fetch_comments(post_id: str, subreddit: str) -> List[Dict[str, Any]]:
    """Fetch comments for a specific post."""
    url = f"{BASE_URL}/r/{subreddit}/comments/{post_id}.json"
    logger.info(f"Fetching comments for post {post_id} in r/{subreddit}")
    
    response_data = fetch_with_backoff(url)
    if not response_data or len(response_data) < 2:
        logger.error(f"Could not fetch comments for post {post_id}")
        return []
    
    # The second object in the response contains the comments
    comment_data = response_data[1].get('data', {}).get('children', [])
    comments = [comment.get('data', {}) for comment in comment_data]
    
    logger.info(f"Retrieved {len(comments)} top-level comments for post {post_id}")
    return comments


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


def save_post_as_file(post: Dict[str, Any], comments: List[Dict[str, Any]], folder_path: Path) -> Dict[str, Any]:
    """Save a post and its comments as a JSON file and return index data."""
    subreddit = post.get('subreddit', 'unknown')
    post_id = post.get('id', 'unknown')
    
    # Create a filename based on subreddit and post ID
    filename = f"{subreddit}_{post_id}.json"
    file_path = folder_path / filename
    
    # Prepare the data
    post_data = prepare_post_json(post, comments)
    
    # Save as JSON
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(post_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved post {post_id} to {file_path}")
    
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
            
            comments = fetch_comments(post_id, subreddit)
            post_index_entry = save_post_as_file(post, comments, date_folder)
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
