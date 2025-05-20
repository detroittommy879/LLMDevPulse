#!/usr/bin/env python3
"""
Reddit Post Lister

This script connects to the SQLite database created by the Reddit Data Fetcher
and lists all post IDs and titles in chronological order (oldest to newest).
"""

import sqlite3
import os
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Constants
DB_PATH = os.getenv("REDDIT_DB_PATH", "data/reddit_data.db") # Use the same env var as the fetcher

def list_posts_chronologically(db_path: str):
    """
    Connects to the SQLite database, fetches post IDs and titles,
    and prints them in chronological order (oldest to newest).
    """
    if not os.path.exists(db_path):
        logger.error(f"Database file not found at {db_path}")
        print(f"Error: Database file not found at {db_path}")
        print("Please ensure the Reddit Data Fetcher script has run and created the database.")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # SQL query to select post id and title, ordered by creation time (UTC timestamp)
        # 'created_utc' is an INTEGER and stores the Unix timestamp, which is ideal for sorting.
        query = """
            SELECT id, title, created_date
            FROM posts
            ORDER BY created_utc ASC;
        """

        cursor.execute(query)
        posts = cursor.fetchall()

        if not posts:
            logger.info("No posts found in the database.")
            print("No posts found in the database.")
            return

        logger.info(f"Found {len(posts)} posts. Listing them chronologically:")
        print("\nPosts from the database (oldest to newest):")
        print("--------------------------------------------")
        for post in posts:
            post_id, title, created_date = post
            # Print in the format: post_id - Title (YYYY-MM-DD HH:MM:SS)
            print(f"{post_id} - {title} ({created_date})")

    except sqlite3.Error as e:
        logger.error(f"SQLite error: {e}")
        print(f"An error occurred while accessing the database: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            logger.info("Database connection closed.")

def main():
    """
    Main function to initiate the listing of posts.
    """
    logger.info("Starting Reddit Post Lister script.")
    list_posts_chronologically(DB_PATH)
    logger.info("Reddit Post Lister script finished.")

if __name__ == "__main__":
    main()