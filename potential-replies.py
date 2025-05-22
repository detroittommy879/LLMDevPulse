#!/usr/bin/env python3
"""
Reddit Reply Suggester - Plain Text Output

This script analyzes Reddit posts and their comment threads from a local SQLite database, uses LLMs (configured via models.json) to generate high-quality reply suggestions, and outputs a structured plain text file with potential Reddit replies, action points, and data for easy parsing.

Features:
- Reads posts and comments from a SQLite database (default: data/reddit_data.db).
- For each post in a specified date range, formats the thread and sends it to an LLM for reply suggestion.
- Outputs a plain text file (default: potential_replies.txt) with structured blocks for each post, including post info, body, comments, and LLM-suggested reply.
- Includes action points and fields for manual review (e.g., MARK_TO_POST, TARGET_PARENT_ID).
- Supports configuration of LLMs via models.json.
- Command-line arguments for date range, output file, database path, and models config.

Usage:
    python potential-replies.py START_DATE [END_DATE] [-o OUTPUT_FILE] [--db-path DB_PATH] [--models-json MODELS_JSON]

    Example:
        python potential-replies.py 2024-05-20 2024-05-21 -o data/potential_replies.txt --db-path data/reddit_data.db --models-json models.json

Environment Variables (set in .env):
    REDDIT_DB_PATH         - Path to SQLite database (default: data/reddit_data.db).
    TEXT_DATA_FOLDER       - Base folder for saving output files (default: data).

Outputs:
    - Plain text file with structured reply suggestions and action blocks for each post.
"""

import sqlite3
import os
import argparse
import datetime
import logging
import time
import json
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Optional
from dotenv import load_dotenv

try:
    from openai import OpenAI, APITimeoutError, APIConnectionError, RateLimitError, APIStatusError
except ImportError:
    print("ERROR: The 'openai' library is not installed. Please install it with 'pip install openai'.")
    exit(1)

# --- Script Configuration ---
SYSTEM_PROMPT_REPLY_GENERATOR = (
    "You are an expert AI assistant skilled at analyzing discussions and crafting insightful replies. "
    "You will be given a Reddit post and its comment thread. Your task is to read the entire thread and suggest "
    "one well-reasoned, helpful, or engaging reply. This reply can be to the original post or to any specific "
    "comment within the thread. Your reply should add value to the conversation. "
    "If you reply to a specific comment, try to implicitly show what you are replying to or very briefly reference it. "
    "If the thread seems uninteresting, or if no constructive reply comes to mind, you can state that, "
    "for example: 'The discussion is quite general, no specific reply stands out as particularly valuable.' "
    "Focus on a single, concise, and high-quality suggestion. Your output should be only the suggested reply itself, without any preamble like 'Here's a suggested reply:'."
)
USER_PROMPT_REPLY_GENERATOR_TEMPLATE = (
    "Please analyze the following Reddit thread and suggest a reply. "
    "Remember, your output should be only the suggested reply itself.\n\n"
    "Reddit Thread:\n{formatted_thread_for_llm}"
)

MAX_FAILURES_PER_MODEL = 2
MODELS_JSON_PATH_DEFAULT = "models.json"
OUTPUT_TXT_FILENAME_DEFAULT = "potential_replies.txt" # Changed to .txt
# --- End Script Configuration ---

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

load_dotenv()
DB_PATH_DEFAULT = os.getenv("REDDIT_DB_PATH", "data/reddit_data.db")
TEXT_DATA_FOLDER_DEFAULT = os.getenv("TEXT_DATA_FOLDER", "data")

MODEL_CONFIGS = []
current_model_index = 0

# --- load_model_configs_from_json, validate_date_string (no changes) ---
def load_model_configs_from_json(json_path: str):
    global MODEL_CONFIGS; MODEL_CONFIGS = []
    logger.info(f"Loading LLM model configurations from JSON file: {json_path}")
    try:
        with open(json_path, 'r', encoding='utf-8') as f: raw_configs = json.load(f)
    except FileNotFoundError: logger.error(f"CRITICAL: Models JSON not found: {json_path}"); return
    except json.JSONDecodeError as e: logger.error(f"CRITICAL: Error decoding JSON {json_path}: {e}"); return
    # ... (rest of the function is the same as previous versions)
    if not isinstance(raw_configs, list): logger.error(f"CRITICAL: Expected list in {json_path}, got {type(raw_configs)}."); return
    loaded_count = 0
    for i, cfg in enumerate(raw_configs):
        if not isinstance(cfg, dict): logger.warning(f"Skipping invalid entry (not dict) at index {i}."); continue
        api_key, base_url, model_id = cfg.get("apiKey"), cfg.get("openai_endpoint"), cfg.get("id")
        display_name = cfg.get("displayName", model_id)
        if not all([api_key, base_url, model_id]): logger.warning(f"Skipping incomplete config at index {i}: {cfg}"); continue
        MODEL_CONFIGS.append({"api_key": api_key, "base_url": base_url, "model_name": model_id, "displayName": display_name, "failure_count": 0, "config_id": f"json_model_{i}"})
        logger.info(f"Loaded config for '{display_name}' (ID: {model_id})")
        loaded_count +=1
    if not MODEL_CONFIGS: logger.warning(f"WARNING: No valid LLM configs loaded from {json_path}.")
    else: logger.info(f"Finished loading model configs. Total valid: {loaded_count}")


def validate_date_string(date_str: str) -> datetime.date:
    try: return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError: logger.error(f"Invalid date: '{date_str}'. Use YYYY-MM-DD."); raise argparse.ArgumentTypeError(f"Invalid date: '{date_str}'. Use YYYY-MM-DD.")

# --- format_thread_recursive now only produces plain text with IDs ---
def format_thread_recursive_for_text(
    parent_id_str: str, # Raw ID of parent (post or comment)
    comments_by_parent_id: Dict[str, List[Dict]],
    level: int
) -> str:
    output_str = ""
    child_comments_list = sorted(
        comments_by_parent_id.get(parent_id_str, []),
        key=lambda c: c.get('created_utc', 0)
    )

    for comment_data in child_comments_list:
        comment_id_raw = comment_data['id']
        comment_id_full = f"t1_{comment_id_raw}"
        comment_body = comment_data.get('body', "").strip()
        comment_author = comment_data.get('author', '[deleted]')
        
        try:
            comment_date_obj = datetime.datetime.fromtimestamp(comment_data.get('created_utc', 0), tz=datetime.timezone.utc)
            comment_date_str = comment_date_obj.strftime('%Y-%m-%d %H:%M UTC')
        except Exception: comment_date_str = "[invalid date]"

        if comment_body and comment_body.lower() not in ('[deleted]', '[removed]'):
            indent = "  " * level
            output_str += f"{indent}Comment by {comment_author} (ID: {comment_id_full}, Date: {comment_date_str}):\n"
            for line in comment_body.splitlines():
                output_str += f"{indent}  {line}\n"
            output_str += f"{indent}\n" # Add a blank indented line for spacing between comments
            
            output_str += format_thread_recursive_for_text(
                comment_id_raw, comments_by_parent_id, level + 1
            )
    return output_str.rstrip() + "\n" # Ensure one trailing newline for the whole block

# --- format_post_and_comments_for_llm_and_text_file (unified) ---
def format_post_and_comments_for_text_file(
    post_data: dict,
    comments_by_parent_id: Dict[str, List[Dict]]
) -> (str, str): # Returns (post_info_block, comments_block)
    """Formats post and comments as plain text blocks for the .txt file output."""
    post_id_raw = post_data.get('id', 'unknown_post')
    post_id_full = f"t3_{post_id_raw}"
    logger.debug(f"Formatting post {post_id_full} for .txt file.")

    # Post Info Block
    post_info_lines = [f"POST_ID_FULL: {post_id_full}"]
    post_info_lines.append(f"POST_URL: {post_data.get('url', 'N/A')}")
    post_info_lines.append(f"POST_TITLE: {post_data.get('title', 'N/A')}")
    post_info_lines.append(f"POST_AUTHOR: {post_data.get('author', '[deleted]')}")
    post_info_lines.append(f"POST_SUBREDDIT: r/{post_data.get('subreddit', 'unknown')}")
    try:
        post_date_str = datetime.datetime.fromtimestamp(post_data['created_utc'], tz=datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    except Exception: post_date_str = "[invalid date]"
    post_info_lines.append(f"POST_DATE: {post_date_str}")
    post_info_block = "\n".join(post_info_lines) + "\n"

    # Post Body Block
    post_body_content = post_data.get('selftext', '').strip()
    if not post_body_content or post_body_content.lower() in ('[deleted]', '[removed]'):
        post_body_content = "[No body text or body was deleted/removed]"
    
    # Comments Block
    formatted_comments_str = format_thread_recursive_for_text(
        post_id_raw, comments_by_parent_id, 0
    )
    comments_block_content = formatted_comments_str.strip() if formatted_comments_str.strip() else "[No comments found for this post]"

    # The text sent to LLM will be a concatenation of these parts.
    # For the .txt file, we'll write them between specific delimiters.
    return post_info_block, post_body_content, comments_block_content


# --- make_llm_api_call (no changes needed) ---
def make_llm_api_call(model_config: dict, system_prompt: str, user_prompt_content: str, timeout_seconds: int = 180) -> str:
    model_display_name = model_config['displayName']; model_api_id = model_config['model_name']; model_base_url = model_config['base_url']
    logger.info(f"API call to model: '{model_display_name}' (ID: {model_api_id}) at {model_base_url}")
    client = OpenAI(api_key=model_config["api_key"], base_url=model_base_url, timeout=timeout_seconds, max_retries=0)
    try:
        chat_completion = client.chat.completions.create(messages=[{"role": "system", "content": system_prompt},{"role": "user", "content": user_prompt_content}], model=model_api_id)
        response_content = chat_completion.choices[0].message.content
        if response_content is None: logger.warning(f"LLM '{model_display_name}' null response."); return "[LLM returned no content]"
        logger.info(f"Response from '{model_display_name}', len: {len(response_content)} chars.")
        return response_content.strip()
    except (APITimeoutError, APIConnectionError, RateLimitError, APIStatusError) as e: logger.error(f"OpenAI API error for '{model_display_name}': {type(e).__name__} - {e}"); raise
    except Exception as e: logger.error(f"Unexpected API call error to '{model_display_name}': {e}", exc_info=True); raise


# --- MODIFIED process_and_suggest_replies for plain text output ---
def process_and_suggest_replies(
    db_path: str, 
    start_date_str: str, 
    end_date_str: str, 
    output_txt_filepath: Path
    ):
    global current_model_index 
    logger.info(f"Processing for dates: {start_date_str} to {end_date_str}. Output TXT: {output_txt_filepath}")

    if not MODEL_CONFIGS: logger.critical("No LLM models. Aborting."); print("Error: No LLM models."); return
    try: start_date_obj = validate_date_string(start_date_str); end_date_obj = validate_date_string(end_date_str)
    except argparse.ArgumentTypeError as e: logger.error(str(e)); print(f"Error: {e}"); return
    if start_date_obj > end_date_obj: logger.error("Start date after end."); print("Error: Start after end."); return
    start_ts = int(datetime.datetime(start_date_obj.year,start_date_obj.month,start_date_obj.day,0,0,0,tzinfo=datetime.timezone.utc).timestamp())
    end_ts = int(datetime.datetime(end_date_obj.year,end_date_obj.month,end_date_obj.day,23,59,59,tzinfo=datetime.timezone.utc).timestamp())
    if not os.path.exists(db_path): logger.error(f"DB not found: {db_path}"); print(f"Error: DB not found."); return
    
    conn = None
    try:
        conn = sqlite3.connect(db_path); conn.row_factory = sqlite3.Row; logger.info(f"DB connected: {db_path}")
        posts_cursor = conn.cursor()
        posts_query = "SELECT id, subreddit, title, author, url, created_utc, selftext FROM posts WHERE created_utc >= ? AND created_utc <= ? ORDER BY created_utc ASC;"
        posts_cursor.execute(posts_query, (start_ts, end_ts))
        all_posts_data = [dict(row) for row in posts_cursor.fetchall()]
        
        date_range_display = start_date_str if start_date_str == end_date_str else f"{start_date_str} to {end_date_str}"

        if not all_posts_data:
            logger.info(f"No posts for date(s): {date_range_display}.")
            output_txt_filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(output_txt_filepath, 'w', encoding='utf-8') as txt_file: # Overwrite if no posts
                txt_file.write(f"# Reddit Reply Suggestions - Plain Text Format\n")
                txt_file.write(f"# Processed Date(s): {date_range_display}\n")
                txt_file.write("# No posts found for the specified date(s).\n")
            print(f"No posts found. Output file '{output_txt_filepath}' created with this info.")
            return

        logger.info(f"Found {len(all_posts_data)} posts for {date_range_display}.")
        output_txt_filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(output_txt_filepath, 'a', encoding='utf-8') as txt_file:
            if txt_file.tell() == 0: # File is new or empty
                txt_file.write(f"# Reddit Reply Suggestions - Plain Text Format\n")
                txt_file.write(f"# Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
                txt_file.write(f"# System Prompt for LLM: {SYSTEM_PROMPT_REPLY_GENERATOR}\n\n")
            
            txt_file.write(f"\n### Data for Date(s): {date_range_display} ###\n\n")

            for post_idx, post_data in enumerate(all_posts_data):
                post_id_raw = post_data['id']
                logger.info(f"--- Processing Post {post_idx+1}/{len(all_posts_data)}: ID t3_{post_id_raw} ---")
                print(f"\nProcessing Post {post_idx+1}/{len(all_posts_data)}: t3_{post_id_raw}...")

                comment_cursor = conn.cursor()
                comments_query = "SELECT id, parent_id, author, body, created_utc FROM comments WHERE post_id = ? ORDER BY created_utc ASC;"
                comment_cursor.execute(comments_query, (post_id_raw,))
                fetched_comments_raw = [dict(row) for row in comment_cursor.fetchall()]
                
                comments_by_parent_id: Dict[str, List[Dict]] = defaultdict(list)
                for comment_dict in fetched_comments_raw:
                    comments_by_parent_id[comment_dict['parent_id']].append(comment_dict)
                
                post_info_block, post_body_block, comments_block = format_post_and_comments_for_text_file(
                    post_data, comments_by_parent_id
                )
                
                # Construct text for LLM (includes post info, body, comments with IDs)
                llm_input_text = f"{post_info_block.replace('POST_ID_FULL:', 'Post ID:')}" # Slight rephrase for LLM
                llm_input_text += f"---POST_BODY_START---\n{post_body_block}\n---POST_BODY_END---\n\n"
                llm_input_text += f"---COMMENTS_START---\n{comments_block}\n---COMMENTS_END---"

                user_prompt_for_llm = USER_PROMPT_REPLY_GENERATOR_TEMPLATE.format(
                    formatted_thread_for_llm=llm_input_text
                )

                # LLM Call (same logic as before)
                llm_suggested_reply = None; used_model_display_name = "N/A"
                # ... (LLM call loop as in previous versions) ...
                initial_model_idx = current_model_index
                for attempt_idx in range(len(MODEL_CONFIGS)):
                    model_idx_to_try = (initial_model_idx + attempt_idx) % len(MODEL_CONFIGS)
                    current_config = MODEL_CONFIGS[model_idx_to_try]
                    if current_config["failure_count"] >= MAX_FAILURES_PER_MODEL: continue
                    try:
                        llm_suggested_reply = make_llm_api_call(current_config, SYSTEM_PROMPT_REPLY_GENERATOR, user_prompt_for_llm)
                        current_config["failure_count"] = 0; current_model_index = model_idx_to_try
                        used_model_display_name = current_config['displayName']; break
                    except Exception:
                        current_config["failure_count"] += 1
                        if current_config["failure_count"] >= MAX_FAILURES_PER_MODEL: logger.error(f"Model '{current_config['displayName']}' max failures.")
                    if attempt_idx < len(MODEL_CONFIGS) -1 : time.sleep(3)
                if llm_suggested_reply is None: llm_suggested_reply = "[LLM failed to generate reply.]"

                # Write to plain text file
                txt_file.write("===START_POST_ENTRY===\n")
                txt_file.write(post_info_block) # Already has trailing newline
                txt_file.write("---POST_BODY_START---\n")
                txt_file.write(post_body_block + "\n")
                txt_file.write("---POST_BODY_END---\n\n")
                txt_file.write("---COMMENTS_START---\n")
                txt_file.write(comments_block + "\n") # comments_block should have trailing newline
                txt_file.write("---COMMENTS_END---\n\n")
                txt_file.write("---ACTION_BLOCK_START---\n")
                txt_file.write("MARK_TO_POST: [ ]\n")
                txt_file.write("TARGET_PARENT_ID:\n") # User fills after colon
                txt_file.write(f"LLM_SUGGESTED_REPLY (via {used_model_display_name}):\n")
                txt_file.write("---SUGGESTED_REPLY_START---\n")
                txt_file.write(llm_suggested_reply + "\n")
                txt_file.write("---SUGGESTED_REPLY_END---\n")
                txt_file.write("---ACTION_BLOCK_END---\n")
                txt_file.write("===END_POST_ENTRY===\n\n---\n\n") # Visual separator after entry

                txt_file.flush()
                logger.info(f"Wrote entry for post t3_{post_id_raw} to TXT file.")
                time.sleep(1)

            logger.info(f"All posts processed. Output in {output_txt_filepath}")
            print(f"\nProcessing complete. Output: {output_txt_filepath}")

    except sqlite3.Error as e: logger.error(f"SQLite error: {e}", exc_info=True); print(f"DB error: {e}")
    except IOError as e: logger.error(f"File I/O error: {e}", exc_info=True); print(f"File I/O error: {e}")
    except Exception as e: logger.critical(f"Unexpected error: {e}", exc_info=True); print(f"Critical error: {e}")
    finally:
        if conn: conn.close(); logger.info("DB connection closed.")

# --- main function: MODIFIED for new TXT filename ---
def main():
    logger.info("--- Reddit Reply Suggester Script (Plain Text Output) Starting ---")
    parser = argparse.ArgumentParser(description="Generates plain text file with potential Reddit replies.")
    parser.add_argument("start_date", type=str, help="Start date (YYYY-MM-DD).")
    parser.add_argument("end_date", type=str, nargs='?', default=None, help="Optional end date (YYYY-MM-DD).")
    default_output_dir = Path(TEXT_DATA_FOLDER_DEFAULT)
    default_txt_output_path = default_output_dir / OUTPUT_TXT_FILENAME_DEFAULT # Use new default
    parser.add_argument("-o", "--output", type=str, default=str(default_txt_output_path), help=f"Output TXT file (default: {default_txt_output_path}).")
    parser.add_argument("--db-path", type=str, default=DB_PATH_DEFAULT, help="SQLite DB path.")
    parser.add_argument("--models-json", type=str, default=MODELS_JSON_PATH_DEFAULT, help="models.json path.")
    args = parser.parse_args()

    actual_start_date_str = args.start_date
    actual_end_date_str = args.end_date if args.end_date else args.start_date
    try: # Date validation
        start_dt = validate_date_string(actual_start_date_str); end_dt = validate_date_string(actual_end_date_str)
        if start_dt > end_dt: logger.error("Start date after end."); print("Error: Start after end."); return
    except argparse.ArgumentTypeError: return

    load_model_configs_from_json(args.models_json)
    if not MODEL_CONFIGS: logger.critical("No models. Abort."); print("CRIT ERR: No models."); return

    logger.info(f"Output TXT: {args.output}")
    logger.info(f"Date range: {actual_start_date_str} to {actual_end_date_str}")
    logger.info("--- Starting Processing ---")
    print("\n--- Generating Plain Text File for Reddit Replies ---")
    
    process_and_suggest_replies(args.db_path, actual_start_date_str, actual_end_date_str, Path(args.output))
    
    logger.info("--- Reddit Reply Suggester Script (Plain Text Output) Finished ---")
    print("\n--- Script Finished ---")

if __name__ == "__main__":
    main()
