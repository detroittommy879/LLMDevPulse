#!/usr/bin/env python3
"""
Reddit Text Exporter

This script connects to the SQLite database created by the Reddit Data Fetcher,
extracts posts and their comments within a given date range, and saves them
to a text file with a specific tagging format.
"""

import sqlite3
import os
import argparse
import datetime
import logging

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

def export_posts_to_text(start_date_str: str, end_date_str: str, output_filepath: str, db_path: str):
    """
    Fetches posts and comments from the database within the date range
    and writes them to a tagged text file.
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

    # Convert dates to Unix timestamps for querying the 'created_utc' column
    # Start of the day for start_date
    start_timestamp = int(datetime.datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0).timestamp())
    # End of the day for end_date (to include all posts on the end_date)
    end_timestamp = int(datetime.datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59).timestamp())

    logger.info(f"Exporting posts from {start_date_str} to {end_date_str} to {output_filepath}")

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Query to get posts within the date range, ordered by creation time
        posts_query = """
            SELECT id, title, selftext, created_utc
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
            for post_id, title, selftext, _ in posts:
                # Sanitize title for the tag attribute (replace double quotes)
                safe_title = title.replace('"', "'") if title else "Untitled Post"
                post_text = selftext if selftext else "" # Use empty string if no selftext

                f_out.write(f'<post_title="{safe_title}">\n')
                f_out.write(f'{post_text}\n')
                f_out.write('<comments_section>\n')

                # Query to get comments for the current post, ordered by creation time
                comments_query = """
                    SELECT body
                    FROM comments
                    WHERE post_id = ?
                    ORDER BY created_utc ASC;
                """
                comment_cursor = conn.cursor() # Use a new cursor or reuse, but new is cleaner for nested loops
                comment_cursor.execute(comments_query, (post_id,))
                comments = comment_cursor.fetchall()

                for (comment_body,) in comments: # Each row is a tuple with one element
                    comment_text = comment_body if comment_body else ""
                    f_out.write(f'{comment_text}\n')

                f_out.write('</comments_section>\n\n') # Extra newline between posts

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
        description="Export Reddit posts and comments from an SQLite database to a tagged text file.",
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
        default="reddit_export.txt",
        help="Path to the output text file (default: reddit_export.txt)."
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=DB_PATH,
        help=f"Path to the SQLite database file (default: {DB_PATH} or REDDIT_DB_PATH env var)."
    )

    args = parser.parse_args()

    logger.info("Starting Reddit Text Exporter script.")
    export_posts_to_text(args.start_date, args.end_date, args.output, args.db_path)
    logger.info("Reddit Text Exporter script finished.")

if __name__ == "__main__":
    main()