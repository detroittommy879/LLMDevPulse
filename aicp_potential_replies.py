#!/usr/bin/env python3
"""
AICP Reddit Reply Suggester - Plain Text Output

This script analyzes Reddit posts and their comment threads from a local SQLite database, 
uses LLMs (configured via models.json) to determine if posts/discussions would benefit from 
AI Code Prep GUI or budget coding guidance, and outputs a structured plain text file with 
potential Reddit replies promoting the appropriate resources.

Features:
- Reads posts and comments from a SQLite database (default: data/reddit_data.db).
- For each post in a specified date range, analyzes if the discussion indicates users who 
  could benefit from AI Code Prep GUI or budget AI coding guidance.
- Uses aicp-info.md content to understand both the tool and coding strategies.
- Targets TWO scenarios:
  1. CODING WORKFLOW: Copy/paste frustrations, file organization issues with AI tools
  2. AI MODEL COSTS/CONFUSION: Questions about which models to use, API costs, free options
- Outputs a plain text file with structured blocks for each relevant post, including 
  LLM-suggested comments promoting AICP or the budget guide.
- Includes action points and fields for manual review (e.g., MARK_TO_POST, TARGET_PARENT_ID).
- Supports configuration of LLMs via models.json.
- Command-line arguments for date range, output file, database path, and models config.

Usage:
    python aicp_potential_replies.py START_DATE [END_DATE] [-o OUTPUT_FILE] 
           [--db-path DB_PATH] [--models-json MODELS_JSON]

    Example:
        python aicp_potential_replies.py 2024-05-20 2024-05-21 
               -o data/aicp_potential_replies.txt --db-path data/reddit_data.db 
               --models-json models.json

Environment Variables (set in .env):
    REDDIT_DB_PATH         - Path to SQLite database (default: data/reddit_data.db).
    TEXT_DATA_FOLDER       - Base folder for saving output files (default: data).

Outputs:
    - Plain text file with structured AICP/budget guide promotion suggestions and action 
      blocks for each relevant post.
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
SYSTEM_PROMPT_AICP_ANALYZER = (
    "You are a real human Reddit user who occasionally comments on programming and AI discussion threads. "
    "You know about two useful resources that sometimes help people: AI Code Prep GUI and a guide about coding with AI on a budget. "
    "You'll analyze if the discussion relates to either of these topics:\n"
    "1. CODING WORKFLOW ISSUES: People struggling with putting code into AI chats, context limits, file organization issues with tools like Cursor, Cline, etc. -> Maybe mention AI Code Prep GUI\n"
    "2. AI MODEL COSTS/CONFUSION: People asking about which models to use, API costs, free options -> Maybe mention budget guide\n"
    "If discussion doesn't match either topic, just write 'NOT_RELEVANT'.\n\n"
    "IMPORTANT GUIDELINES FOR RESPONSES:\n"    "- Keep it short and casual - 1-3 sentences usually enough\n"
    "- Be a human, not a helper bot - don't be overly formal or perfect\n"
    "- Don't analyze the thread in your comment\n"
    "- Sometimes skip capitals, punctuation is optional\n"
    "- No introductions like 'I noticed you're having trouble with...'\n"
    "- Don't ask multiple questions\n"
    "- Sometimes be brief, just 'check out this tool: [link]' is fine\n"
    "- Never say things like 'this thread seems relevant to' or 'this looks like it fits scenario X'\n"
    "- Just write the direct comment content that would appear on Reddit\n"
    "- Don't worry about MARK_TO_POST, TARGET_PARENT_ID, or other structural elements - the script adds those automatically\n"
    "- If it's not a good match, just write 'NOT_RELEVANT' by itself"
)

USER_PROMPT_AICP_TEMPLATE = (
    "Here's info about these resources:\n\n{aicp_info}\n\n"
    "Review this Reddit thread to see if it's about coding workflow issues or AI model costs/confusion:\n\n"
    "Reddit Thread:\n{formatted_thread_for_llm}\n\n"
    "Instructions:\n"
    "- If people are talking about file organization for AI tools, context limits, copying code to AI chats, or tools like Cursor/Cline, mention the AI Code Prep GUI (https://wuu73.org/aicp)\n"
    "- If people are discussing model costs, which AI models to use, or budget concerns for AI coding, mention the guide at https://wuu73.org/blog/guide.html\n"
    "- If neither applies, just write 'NOT_RELEVANT'\n\n"
    "IMPORTANT: Your response should look like a casual Reddit comment. Keep it short (1-3 sentences). Don't be too formal or perfect. Skip some capitalization and punctuation sometimes. Don't ask multiple questions. Sometimes a quick mention of the tool is enough. Never analyze the thread - just write the actual comment that would appear on Reddit."
)

MAX_FAILURES_PER_MODEL = 10
MODELS_JSON_PATH_DEFAULT = "models.json"
OUTPUT_TXT_FILENAME_DEFAULT = "aicp_potential_replies.txt"
AICP_INFO_FILE = "aicp-info.md"
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
AICP_INFO_CONTENT = ""

def load_aicp_info():
    """Load the AI Code Prep GUI information from aicp-info.md"""
    global AICP_INFO_CONTENT
    try:
        with open(AICP_INFO_FILE, 'r', encoding='utf-8') as f:
            AICP_INFO_CONTENT = f.read()
        logger.info(f"Loaded AICP info from {AICP_INFO_FILE} ({len(AICP_INFO_CONTENT)} chars)")
    except FileNotFoundError:
        logger.error(f"CRITICAL: AICP info file not found: {AICP_INFO_FILE}")
        # Provide fallback minimal content in case the file is missing
        AICP_INFO_CONTENT = (
            "AI Code Prep GUI: A tool for preparing code files for AI chat tools to avoid copy/paste hassles. "
            "Visit https://wuu73.org/aicp for details.\n\n"
            "AI on a Budget Guide: A comprehensive guide for coding with AI affordably. "
            "Learn about model selection, cost-efficient workflows, and more at https://wuu73.org/blog/guide.html"
        )
        logger.warning(f"Using fallback AICP info content ({len(AICP_INFO_CONTENT)} chars)")
        print(f"WARNING: AICP info file not found. Using fallback content.")
        return True  # Continue with fallback content
    except Exception as e:
        logger.error(f"Error reading AICP info file: {e}")
        return False
    return True

def load_model_configs_from_json(json_path: str):
    global MODEL_CONFIGS
    MODEL_CONFIGS = []
    logger.info(f"Loading LLM model configurations from JSON file: {json_path}")
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            raw_configs = json.load(f)
    except FileNotFoundError:
        logger.error(f"CRITICAL: Models JSON not found: {json_path}")
        return
    except json.JSONDecodeError as e:
        logger.error(f"CRITICAL: Error decoding JSON {json_path}: {e}")
        return

    if not isinstance(raw_configs, list):
        logger.error(f"CRITICAL: Expected list in {json_path}, got {type(raw_configs)}.")
        return
    
    loaded_count = 0
    for i, cfg in enumerate(raw_configs):
        if not isinstance(cfg, dict):
            logger.warning(f"Skipping invalid entry (not dict) at index {i}.")
            continue
        
        api_key, base_url, model_id = cfg.get("apiKey"), cfg.get("openai_endpoint"), cfg.get("id")
        display_name = cfg.get("displayName", model_id)
        
        if not all([api_key, base_url, model_id]):
            logger.warning(f"Skipping incomplete config at index {i}: {cfg}")
            continue
        
        MODEL_CONFIGS.append({
            "api_key": api_key,
            "base_url": base_url,
            "model_name": model_id,
            "displayName": display_name,
            "failure_count": 0,
            "config_id": f"json_model_{i}"
        })
        logger.info(f"Loaded config for '{display_name}' (ID: {model_id})")
        loaded_count += 1
    
    if not MODEL_CONFIGS:
        logger.warning(f"WARNING: No valid LLM configs loaded from {json_path}.")
    else:
        logger.info(f"Finished loading model configs. Total valid: {loaded_count}")

def validate_date_string(date_str: str) -> datetime.date:
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        logger.error(f"Invalid date: '{date_str}'. Use YYYY-MM-DD.")
        raise argparse.ArgumentTypeError(f"Invalid date: '{date_str}'. Use YYYY-MM-DD.")

def format_thread_recursive_for_text(
    parent_id_str: str,
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
            comment_date_obj = datetime.datetime.fromtimestamp(
                comment_data.get('created_utc', 0), 
                tz=datetime.timezone.utc
            )
            comment_date_str = comment_date_obj.strftime('%Y-%m-%d %H:%M UTC')
        except Exception:
            comment_date_str = "[invalid date]"

        if comment_body and comment_body.lower() not in ('[deleted]', '[removed]'):
            indent = "  " * level
            output_str += f"{indent}Comment by {comment_author} (ID: {comment_id_full}, Date: {comment_date_str}):\n"
            for line in comment_body.splitlines():
                output_str += f"{indent}  {line}\n"
            output_str += f"{indent}\n"
            
            output_str += format_thread_recursive_for_text(
                comment_id_raw, comments_by_parent_id, level + 1
            )
    return output_str.rstrip() + "\n"

def format_post_and_comments_for_text_file(
    post_data: dict,
    comments_by_parent_id: Dict[str, List[Dict]]
) -> tuple:
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
        post_date_str = datetime.datetime.fromtimestamp(
            post_data['created_utc'], 
            tz=datetime.timezone.utc
        ).strftime('%Y-%m-%d %H:%M UTC')
    except Exception:
        post_date_str = "[invalid date]"
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

    return post_info_block, post_body_content, comments_block_content

def make_llm_api_call(model_config: dict, system_prompt: str, user_prompt_content: str, timeout_seconds: int = 180) -> str:
    model_display_name = model_config['displayName']
    model_api_id = model_config['model_name']
    model_base_url = model_config['base_url']
    
    logger.info(f"API call to model: '{model_display_name}' (ID: {model_api_id}) at {model_base_url}")
    
    client = OpenAI(
        api_key=model_config["api_key"], 
        base_url=model_base_url, 
        timeout=timeout_seconds, 
        max_retries=0
    )
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_content}
            ], 
            model=model_api_id
        )
        response_content = chat_completion.choices[0].message.content
        
        if response_content is None:
            logger.warning(f"LLM '{model_display_name}' null response.")
            return "[LLM returned no content]"
        
        logger.info(f"Response from '{model_display_name}', len: {len(response_content)} chars.")
        return response_content.strip()
        
    except (APITimeoutError, APIConnectionError, RateLimitError, APIStatusError) as e:
        logger.error(f"OpenAI API error for '{model_display_name}': {type(e).__name__} - {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected API call error to '{model_display_name}': {e}", exc_info=True)
        raise

def process_and_suggest_aicp_replies(
    db_path: str, 
    start_date_str: str, 
    end_date_str: str, 
    output_txt_filepath: Path
):
    global current_model_index 
    logger.info(f"Processing for dates: {start_date_str} to {end_date_str}. Output TXT: {output_txt_filepath}")

    # Check if output file already exists and backup if needed
    if output_txt_filepath.exists():
        timestamp = datetime.datetime.now().strftime("%m%d%y_%H%M%S")
        backup_filepath = output_txt_filepath.with_name(f"{output_txt_filepath.stem}_old_{timestamp}{output_txt_filepath.suffix}")
        try:
            output_txt_filepath.rename(backup_filepath)
            logger.info(f"Existing file backed up to: {backup_filepath}")
            print(f"Previous output file backed up to: {backup_filepath}")
        except Exception as e:
            logger.warning(f"Could not rename existing file: {e}. Will append to existing file.")
            print(f"Warning: Could not back up existing file. Will continue with append mode.")
    
    if not MODEL_CONFIGS:
        logger.critical("No LLM models. Aborting.")
        print("Error: No LLM models.")
        return
    
    if not AICP_INFO_CONTENT:
        logger.critical("No AICP info content. Aborting.")
        print("Error: No AICP info content.")
        return
    
    try:
        start_date_obj = validate_date_string(start_date_str)
        end_date_obj = validate_date_string(end_date_str)
    except argparse.ArgumentTypeError as e:
        logger.error(str(e))
        print(f"Error: {e}")
        return
    
    if start_date_obj > end_date_obj:
        logger.error("Start date after end.")
        print("Error: Start after end.")
        return
    
    start_ts = int(datetime.datetime(
        start_date_obj.year, start_date_obj.month, start_date_obj.day, 
        0, 0, 0, tzinfo=datetime.timezone.utc
    ).timestamp())
    end_ts = int(datetime.datetime(
        end_date_obj.year, end_date_obj.month, end_date_obj.day, 
        23, 59, 59, tzinfo=datetime.timezone.utc
    ).timestamp())
    
    if not os.path.exists(db_path):
        logger.error(f"DB not found: {db_path}")
        print(f"Error: DB not found.")
        return
    
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        logger.info(f"DB connected: {db_path}")
        
        posts_cursor = conn.cursor()
        posts_query = "SELECT id, subreddit, title, author, url, created_utc, selftext FROM posts WHERE created_utc >= ? AND created_utc <= ? ORDER BY created_utc ASC;"
        posts_cursor.execute(posts_query, (start_ts, end_ts))
        all_posts_data = [dict(row) for row in posts_cursor.fetchall()]
        
        date_range_display = start_date_str if start_date_str == end_date_str else f"{start_date_str} to {end_date_str}"

        if not all_posts_data:
            logger.info(f"No posts for date(s): {date_range_display}.")
            output_txt_filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(output_txt_filepath, 'w', encoding='utf-8') as txt_file:
                txt_file.write(f"# AICP Reddit Reply Suggestions - Plain Text Format\n")
                txt_file.write(f"# Processed Date(s): {date_range_display}\n")
                txt_file.write("# No posts found for the specified date(s).\n")
                print(f"No posts found. Output file '{output_txt_filepath}' created with this info.")
            return
        
        logger.info(f"Found {len(all_posts_data)} posts for {date_range_display}.")
        output_txt_filepath.parent.mkdir(parents=True, exist_ok=True)
        
        relevant_posts_count = 0

        # Create a new file (we've already backed up the old one if needed)
        with open(output_txt_filepath, 'w', encoding='utf-8') as txt_file:
            txt_file.write(f"# AICP Reddit Reply Suggestions - Plain Text Format\n")
            txt_file.write(f"# Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            txt_file.write(f"# System Prompt for LLM: {SYSTEM_PROMPT_AICP_ANALYZER}\n\n")
            txt_file.write(f"\n### AICP Analysis for Date(s): {date_range_display} ###\n\n")

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
                llm_input_text = f"{post_info_block.replace('POST_ID_FULL:', 'Post ID:')}"
                llm_input_text += f"---POST_BODY_START---\n{post_body_block}\n---POST_BODY_END---\n\n"
                llm_input_text += f"---COMMENTS_START---\n{comments_block}\n---COMMENTS_END---"

                user_prompt_for_llm = USER_PROMPT_AICP_TEMPLATE.format(
                    aicp_info=AICP_INFO_CONTENT,
                    formatted_thread_for_llm=llm_input_text
                )

                # LLM Call
                llm_suggested_reply = None
                used_model_display_name = "N/A"
                initial_model_idx = current_model_index
                
                model_attempts = 0
                while model_attempts < len(MODEL_CONFIGS):
                    model_idx_to_try = (initial_model_idx + model_attempts) % len(MODEL_CONFIGS)
                    current_config = MODEL_CONFIGS[model_idx_to_try]

                    if current_config["failure_count"] >= MAX_FAILURES_PER_MODEL:
                        model_attempts += 1
                        continue

                    fail_count = current_config["failure_count"]
                    backoff_base = 2  # seconds
                    for fail_try in range(fail_count, MAX_FAILURES_PER_MODEL):
                        try:
                            llm_suggested_reply = make_llm_api_call(
                                current_config,
                                SYSTEM_PROMPT_AICP_ANALYZER,
                                user_prompt_for_llm
                            )
                            current_config["failure_count"] = 0
                            current_model_index = model_idx_to_try
                            used_model_display_name = current_config['displayName']
                            break
                        except Exception:
                            current_config["failure_count"] += 1
                            fail_count = current_config["failure_count"]
                            if fail_count >= MAX_FAILURES_PER_MODEL:
                                logger.error(f"Model '{current_config['displayName']}' max failures.")
                                break
                            sleep_time = backoff_base * (2 ** (fail_count - 1))
                            logger.warning(f"Failure {fail_count} for model '{current_config['displayName']}'. Waiting {sleep_time} seconds before retry.")
                            time.sleep(sleep_time)
                    if llm_suggested_reply is not None:
                        break
                    model_attempts += 1
                
                if llm_suggested_reply is None:
                    llm_suggested_reply = "[LLM failed to generate reply.]"

                # Only write to file if LLM found it relevant
                if llm_suggested_reply.strip().upper() != "NOT_RELEVANT":
                    relevant_posts_count += 1
                    
                    # Write to plain text file
                    txt_file.write("===START_POST_ENTRY===\n")
                    txt_file.write(post_info_block)
                    txt_file.write("---POST_BODY_START---\n")
                    txt_file.write(post_body_block + "\n")
                    txt_file.write("---POST_BODY_END---\n\n")
                    txt_file.write("---COMMENTS_START---\n")
                    txt_file.write(comments_block + "\n")
                    txt_file.write("---COMMENTS_END---\n\n")
                    txt_file.write("---ACTION_BLOCK_START---\n")
                    txt_file.write("MARK_TO_POST: [ ]\n")
                    txt_file.write("TARGET_PARENT_ID:\n")
                    txt_file.write(f"AICP_SUGGESTED_COMMENT (via {used_model_display_name}):\n")
                    txt_file.write("---SUGGESTED_COMMENT_START---\n")
                    txt_file.write(llm_suggested_reply + "\n")
                    txt_file.write("---SUGGESTED_COMMENT_END---\n")
                    txt_file.write("---ACTION_BLOCK_END---\n")
                    txt_file.write("===END_POST_ENTRY===\n\n---\n\n")

                    txt_file.flush()
                    logger.info(f"Wrote relevant entry for post t3_{post_id_raw} to TXT file.")
                else:
                    logger.info(f"Post t3_{post_id_raw} marked as NOT_RELEVANT by LLM, skipping.")
                
                time.sleep(1)
            # Add summary at the end
            txt_file.write(f"\n### SUMMARY ###\n")
            txt_file.write(f"Total posts analyzed: {len(all_posts_data)}\n")
            txt_file.write(f"Relevant posts found: {relevant_posts_count}\n")
            txt_file.write(f"Processing completed on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            
            logger.info(f"All posts processed. Found {relevant_posts_count}/{len(all_posts_data)} relevant posts. Output in {output_txt_filepath}")
            print(f"\nProcessing complete. Found {relevant_posts_count}/{len(all_posts_data)} relevant posts. Output: {output_txt_filepath}")
            
    except sqlite3.Error as db_error:
        logger.error(f"SQLite error: {db_error}", exc_info=True)
        print(f"Database error: {db_error}")
    except IOError as io_error:
        logger.error(f"File I/O error: {io_error}", exc_info=True)
        print(f"File error: {io_error}")
        # Try to create a fallback file in the current directory if there was an issue with the specified path
        try:
            fallback_path = Path(f"aicp_results_{datetime.datetime.now().strftime('%m%d%y_%H%M%S')}.txt")
            with open(fallback_path, 'w', encoding='utf-8') as fallback_file:
                fallback_file.write("# AICP Results - Fallback File (Error occurred with original path)\n")
                fallback_file.write(f"# Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
                fallback_file.write(f"# Error with original path: {io_error}\n")
                if 'llm_suggested_reply' in locals() and llm_suggested_reply is not None:
                    fallback_file.write("\n### Last Generated Reply ###\n")
                    fallback_file.write(llm_suggested_reply)
            logger.info(f"Created fallback file at: {fallback_path}")
            print(f"Created fallback file at: {fallback_path}")
        except Exception as fallback_error:
            logger.critical(f"Could not create fallback file: {fallback_error}", exc_info=True)
    except Exception as general_error:
        logger.critical(f"Unexpected error: {general_error}", exc_info=True)
        print(f"Critical error: {general_error}")
    finally:
        if conn:
            conn.close()
            logger.info("DB connection closed.")

def main():
    logger.info("--- AICP Reddit Reply Suggester Script Starting ---")
    
    # Load AICP info first
    if not load_aicp_info():
        print("ERROR: Could not load AICP info file. Exiting.")
        return
    
    parser = argparse.ArgumentParser(description="Generates plain text file with potential AICP promotion replies.")
    parser.add_argument("start_date", type=str, help="Start date (YYYY-MM-DD).")
    parser.add_argument("end_date", type=str, nargs='?', default=None, help="Optional end date (YYYY-MM-DD).")
    
    default_output_dir = Path(TEXT_DATA_FOLDER_DEFAULT)
    default_txt_output_path = default_output_dir / OUTPUT_TXT_FILENAME_DEFAULT
    
    parser.add_argument("-o", "--output", type=str, default=str(default_txt_output_path), 
                       help=f"Output TXT file (default: {default_txt_output_path}).")
    parser.add_argument("--db-path", type=str, default=DB_PATH_DEFAULT, help="SQLite DB path.")
    parser.add_argument("--models-json", type=str, default=MODELS_JSON_PATH_DEFAULT, help="models.json path.")
    
    args = parser.parse_args()

    actual_start_date_str = args.start_date
    actual_end_date_str = args.end_date if args.end_date else args.start_date
    
    try:
        start_dt = validate_date_string(actual_start_date_str)
        end_dt = validate_date_string(actual_end_date_str)
        
        if start_dt > end_dt:
            logger.error("Start date after end.")
            print("Error: Start after end.")
            return
    except argparse.ArgumentTypeError:
        return
        
    load_model_configs_from_json(args.models_json)
    if not MODEL_CONFIGS:
        logger.critical("No models configured. Attempting to use default OpenAI configuration...")
        # Provide a fallback model config if none are loaded
        try:
            import os
            default_api_key = os.environ.get("OPENAI_API_KEY", "")
            if default_api_key:
                MODEL_CONFIGS.append({
                    "api_key": default_api_key,
                    "base_url": "https://api.openai.com/v1",
                    "model_name": "gpt-3.5-turbo",
                    "displayName": "Default-GPT-3.5-Turbo",
                    "failure_count": 0,
                    "config_id": "default_fallback"
                })
                logger.info("Added fallback model configuration using OPENAI_API_KEY environment variable")
                print("Added fallback model configuration using environment variable")
            else:
                logger.critical("No OPENAI_API_KEY environment variable found. Cannot proceed without model access.")
                print("CRITICAL ERROR: No models available and no OPENAI_API_KEY environment variable found.")
                return
        except Exception as model_error:
            logger.critical(f"Could not configure fallback model: {model_error}")
            print("CRITICAL ERROR: No models available. Please check your models.json file.")
            return

    logger.info(f"Output TXT: {args.output}")
    logger.info(f"Date range: {actual_start_date_str} to {actual_end_date_str}")
    logger.info("--- Starting AICP Analysis ---")
    print("\n--- Generating AICP Promotion Suggestions ---")
    
    process_and_suggest_aicp_replies(args.db_path, actual_start_date_str, actual_end_date_str, Path(args.output))
    
    logger.info("--- AICP Reddit Reply Suggester Script Finished ---")
    print("\n--- Script Finished ---")

if __name__ == "__main__":
    main()
