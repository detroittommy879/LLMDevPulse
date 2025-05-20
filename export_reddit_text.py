#!/usr/bin/env python3
"""
Reddit Text Exporter (Markdown Version)

This script connects to the SQLite database created by the Reddit Data Fetcher,
extracts posts and their comments within a given date range, and saves them
to a Markdown file with blockquote-based indentation for comments.
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

def format_comment_for_markdown(full_comment_content: str, level: int) -> str:
    """
    Formats a full comment string (header + body) with markdown blockquotes
    for indentation. Level 1 gets one '>', level 2 gets '>>', etc.
    """
    if not full_comment_content:
        return ""
    
    # Ensure level is at least 1 for blockquoting, or handle level 0 if needed elsewhere
    # For this function, we assume level >= 1 means it needs a prefix.
    # If level is 0, it means no prefix.
    if level == 0: # Should not happen if we call with level=1 for top comments
        prefix = ""
    else:
        prefix = "> " * level
    
    # Apply prefix to each line of the comment content
    indented_lines = []
    for line in full_comment_content.splitlines():
        indented_lines.append(f"{prefix}{line if line.strip() else ''}") # Preserve empty lines within comment slightly better
    
    return "\n".join(indented_lines) + "\n\n" # Two newlines for spacing between comments

def write_comments_markdown_recursive(
    f_out,
    parent_id_str: str, 
    comments_by_parent_id: dict,
    all_comments_data: dict,
    level: int  # Current nesting level (1 for top-level comments, 2 for replies, etc.)
):
    """
    Recursively writes comments to the file in Markdown format, handling threading.
    parent_id_str is expected to be a bare ID (no t1_ or t3_ prefix).
    """
    actual_parent_key = parent_id_str # parent_id_str is already a bare ID

    if actual_parent_key not in comments_by_parent_id:
        return

    child_comment_ids = sorted(
        comments_by_parent_id[actual_parent_key],
        key=lambda cid: all_comments_data[cid]['created_utc']
    )

    for comment_id in child_comment_ids:
        comment_data = all_comments_data[comment_id]
        comment_body_text = comment_data.get('body', "").strip()
        comment_author = comment_data.get('author', '[deleted]')
        comment_created_utc = comment_data.get('created_utc', 0)
        
        # Format date - ensure created_utc is valid
        try:
            comment_date_str = datetime.datetime.fromtimestamp(comment_created_utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        except ValueError:
            comment_date_str = "[invalid date]"

        if comment_body_text: # Only write if there's actual text
            comment_header = f"**{comment_author}** ({comment_date_str}):\n"
            full_comment_content = f"{comment_header}{comment_body_text}"
            
            f_out.write(format_comment_for_markdown(full_comment_content, level))
        
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
                    f_out.write("\n---\n\n") 

                post_title = title if title else "Untitled Post"
                post_body = selftext if selftext else ""
                post_author = author if author else "Unknown Author"
                post_date = datetime.datetime.fromtimestamp(post_created_utc).strftime('%Y-%m-%d %H:%M:%S UTC')

                f_out.write(f"# {post_title}\n")
                f_out.write(f"**Author:** {post_author} | **Posted:** {post_date} | **URL:** {url}\n\n")
                if post_body.strip():
                    f_out.write(f"{post_body.strip()}\n\n")
                
                f_out.write("## Comments\n\n")

                comments_query = """
                    SELECT id, parent_id, body, author, created_utc
                    FROM comments
                    WHERE post_id = ?
                    ORDER BY created_utc ASC; 
                """
                comment_cursor = conn.cursor()
                comment_cursor.execute(comments_query, (post_id,))
                fetched_comments = comment_cursor.fetchall()

                if not fetched_comments:
                    f_out.write("*No comments yet.*\n\n")
                else:
                    all_comments_data = {} 
                    comments_by_parent_id = defaultdict(list)

                    for c_id, c_parent_id, c_body, c_author, c_created_utc in fetched_comments:
                        all_comments_data[c_id] = {
                            'id': c_id,
                            'parent_id': c_parent_id, # This is the bare ID from the DB
                            'body': c_body,
                            'author': c_author,
                            'created_utc': c_created_utc
                        }
                        comments_by_parent_id[c_parent_id].append(c_id)
                    
                    # Start recursion for top-level comments (children of the post_id)
                    # Use level=1 for the first level of comments to get one '>'
                    write_comments_markdown_recursive(f_out, post_id, comments_by_parent_id, all_comments_data, level=1)

            f_out.write("\n")

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
        default="reddit_export.md",
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