#!/usr/bin/env python3
"""
Reddit Text Exporter (Markdown Version)

This script connects to the SQLite database created by the Reddit Data Fetcher,
extracts posts and their comments within a given date range, and saves them
to a Markdown file.
"""

import sqlite3
import os
import argparse
import datetime
import logging
from collections import defaultdict

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Constants
DB_PATH = os.getenv("REDDIT_DB_PATH", "data/reddit_data.db")

def validate_date_string(date_str: str) -> datetime.date:
    """Validate and convert 'YYYY-MM-DD' string to a date object."""
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: '{date_str}'. Please use YYYY-MM-DD.")

def format_comment_for_markdown(comment_body: str, level: int) -> str:
    """Formats a comment body with markdown blockquotes for indentation."""
    if not comment_body:
        return ""
    # Add blockquote for each level of nesting
    prefix = "> " * level
    # Ensure each line of the comment gets the prefix
    indented_body = "\n".join([f"{prefix}{line}" for line in comment_body.splitlines()])
    return f"{indented_body}\n\n" # Add two newlines for spacing between comments

def write_comments_markdown_recursive(
    f_out,
    parent_id_str: str, # Can be post_id (t3_...) or comment_id (t1_...)
    comments_by_parent_id: dict,
    all_comments_data: dict,
    level: int
):
    """
    Recursively writes comments to the file in Markdown format, handling threading.
    """
    # The parent_id in the DB for top-level comments refers to the post_id without a prefix.
    # For the data fetcher, it might store parent_id with t1_ or t3_ prefixes.
    # We need to ensure we handle this consistently. For this version, we assume
    # comments_by_parent_id keys are bare IDs (no t1_ or t3_ prefix).
    
    # If parent_id_str has a prefix (like 't1_xxxx' or 't3_xxxx'), strip it.
    # The keys in comments_by_parent_id are expected to be bare IDs from the parent_id column.
    actual_parent_key = parent_id_str.split('_')[-1] if '_' in parent_id_str else parent_id_str

    if actual_parent_key not in comments_by_parent_id:
        return

    # Sort comments by creation time before processing
    child_comment_ids = sorted(
        comments_by_parent_id[actual_parent_key],
        key=lambda cid: all_comments_data[cid]['created_utc']
    )

    for comment_id in child_comment_ids:
        comment_data = all_comments_data[comment_id]
        comment_text = comment_data.get('body', "").strip()
        if comment_text: # Only write if there's actual text
             # User info could be added here: e.g., f_out.write(f"{'> ' * level}**{comment_data.get('author', 'anon')}** says:\n")
            f_out.write(format_comment_for_markdown(comment_text, level))
        
        # Recursively write replies to this comment
        write_comments_markdown_recursive(f_out, comment_id, comments_by_parent_id, all_comments_data, level + 1)


def export_posts_to_markdown(start_date_str: str, end_date_str: str, output_filepath: str, db_path: str):
    """
    Fetches posts and comments from the database within the date range
    and writes them to a Markdown file.
    """
    if not os.path.exists(db_path):
        logger.error(f"Database file not found at {db_path}")
        print(f"Error: Database file not found at {db_path}")
        return

    try:
        start_date = validate_date_string(start_date_str)
        end_date = validate_date_string(end_date_str)
    except argparse.ArgumentTypeError as e:
        logger.error(str(e))
        print(f"Error: {e}")
        return

    if start_date > end_date:
        logger.error("Start date cannot be after end date.")
        print("Error: Start date cannot be after end date.")
        return

    start_timestamp = int(datetime.datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0).timestamp())
    end_timestamp = int(datetime.datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59).timestamp())

    logger.info(f"Exporting posts from {start_date_str} to {end_date_str} to {output_filepath}")

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        # Optional: conn.row_factory = sqlite3.Row  # To access columns by name
        cursor = conn.cursor()

        posts_query = """
            SELECT id, title, selftext, author, url, created_utc
            FROM posts
            WHERE created_utc >= ? AND created_utc <= ?
            ORDER BY created_utc ASC;
        """
        cursor.execute(posts_query, (start_timestamp, end_timestamp))
        posts = cursor.fetchall()

        if not posts:
            logger.info("No posts found in the specified date range.")
            print("No posts found in the specified date range.")
            return

        with open(output_filepath, 'w', encoding='utf-8') as f_out:
            for i, (post_id, title, selftext, author, url, post_created_utc) in enumerate(posts):
                if i > 0:
                    f_out.write("\n---\n\n") # Horizontal rule between posts

                post_title = title if title else "Untitled Post"
                post_body = selftext if selftext else ""
                post_author = author if author else "Unknown Author"
                post_date = datetime.datetime.fromtimestamp(post_created_utc).strftime('%Y-%m-%d %H:%M:%S UTC')

                f_out.write(f"# {post_title}\n")
                f_out.write(f"**Author:** {post_author} | **Posted:** {post_date} | **URL:** {url}\n\n")
                if post_body.strip(): # Only write body if it's not empty
                    f_out.write(f"{post_body.strip()}\n\n")
                
                f_out.write("## Comments\n\n")

                # Query to get all comments for the current post, including IDs for threading
                comments_query = """
                    SELECT id, parent_id, body, author, created_utc
                    FROM comments
                    WHERE post_id = ?
                    ORDER BY created_utc ASC; 
                """
                # Using a new cursor for comments is fine
                comment_cursor = conn.cursor()
                comment_cursor.execute(comments_query, (post_id,))
                fetched_comments = comment_cursor.fetchall()

                if not fetched_comments:
                    f_out.write("*No comments yet.*\n\n")
                else:
                    all_comments_data = {} # Stores full comment data: 'comment_id' -> {data}
                    comments_by_parent_id = defaultdict(list) # 'parent_id' -> ['child_comment_id1', ...]

                    for c_id, c_parent_id, c_body, c_author, c_created_utc in fetched_comments:
                        # parent_id from DB might be 't3_POSTID' for top-level or 't1_COMMENTID' for replies
                        # Or it could be just the ID string if your fetcher script cleans it.
                        # For this recursive writer, we need the bare ID.
                        
                        # The `parent_id` column in your `comments` table stores the ID of the direct parent.
                        # If it's a top-level comment, `parent_id` refers to the post ID.
                        # If it's a reply, `parent_id` refers to another comment's ID.
                        # The reddit API uses prefixes like t1_ (comment) t3_ (post).
                        # Your `Reddit Data Fetcher` cleans this:
                        # if parent_id and parent_id.startswith('t3_'):
                        #     parent_id = parent_id[3:]
                        # elif parent_id and parent_id.startswith('t1_'):
                        #     parent_id = parent_id[3:]
                        # So c_parent_id here should be the bare ID.

                        all_comments_data[c_id] = {
                            'id': c_id,
                            'parent_id': c_parent_id,
                            'body': c_body,
                            'author': c_author,
                            'created_utc': c_created_utc
                        }
                        # Group comments by their parent ID
                        comments_by_parent_id[c_parent_id].append(c_id)

                    # Start recursion for top-level comments (those whose parent_id is the post_id)
                    write_comments_markdown_recursive(f_out, post_id, comments_by_parent_id, all_comments_data, level=0)

            f_out.write("\n") # Ensure a final newline

        logger.info(f"Successfully exported {len(posts)} posts to {output_filepath}")
        print(f"Successfully exported {len(posts)} posts to {output_filepath}")

    except sqlite3.Error as e:
        logger.error(f"SQLite error: {e}")
        print(f"An error occurred while accessing the database: {e}")
    except IOError as e:
        logger.error(f"File I/O error: {e}")
        print(f"An error occurred while writing to the file: {e}")
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection closed.")

def main():
    parser = argparse.ArgumentParser(
        description="Export Reddit posts and comments from an SQLite database to a Markdown text file.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "start_date",
        type=str,
        help="Start date for fetching posts (YYYY-MM-DD)."
    )
    parser.add_argument(
        "end_date",
        type=str,
        help="End date for fetching posts (YYYY-MM-DD)."
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="reddit_export.md", # Changed default extension
        help="Path to the output markdown file (default: reddit_export.md)."
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=DB_PATH,
        help=f"Path to the SQLite database file (default: {DB_PATH} or REDDIT_DB_PATH env var)."
    )

    args = parser.parse_args()

    logger.info("Starting Reddit Markdown Exporter script.")
    export_posts_to_markdown(args.start_date, args.end_date, args.output, args.db_path)
    logger.info("Reddit Markdown Exporter script finished.")

if __name__ == "__main__":
    main()