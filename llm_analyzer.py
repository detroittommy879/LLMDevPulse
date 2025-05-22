#!/usr/bin/env python3
"""
Reddit Data LLM Analyzer

This script connects to an SQLite database (created by a Reddit data fetcher),
extracts posts and comments within a date range, formats them, and sends them
in chunks to an OpenAI-compatible LLM API for analysis based on a user-defined prompt.
Results are saved to a Markdown file.

It loads LLM configurations from a `models.json` file and supports fallback.
"""

import sqlite3
import os
import argparse
import datetime
import logging
import time
import json # For loading models.json
from collections import defaultdict
from dotenv import load_dotenv

try:
    from openai import OpenAI, APITimeoutError, APIConnectionError, RateLimitError, APIStatusError
except ImportError:
    print("The 'openai' library is not installed. Please install it with 'pip install openai'.")
    exit(1)

# --- Script Configuration (Defaults, can be overridden by CLI args or .env) ---
SYSTEM_PROMPT = "You are an expert AI assistant. You follow instructions very well. Analyze the provided extracted Reddit posts and comments to answer the user's question."
USER_QUESTION_PROMPT_DEFAULT = (
    "List any discussed AI models and what types of tasks people are using them for. "
    "Certain models are good for certain things and we are trying to gather data about them. "
    "For example, people saying that GPT-a.b is good for debugging, or o4-mini is great at high level planning, "
    "or XYZ-3 is a good balance of low cost and being super good problem solving. "
    "Just put the model name no need to put the company name but definitely be specific if there are any variations for a model "
    "(like o3, o3-mini, o3-mini-high etc).\n"
    "Make a list with model-name: then if 3 people mention tool use say 3 people said good for tool use.\n"
    "newline then next model-name-2: 4 people say it is bad at coding.\n"
    "So like this:\n"
    "example-modelname: 5 people are discussing how great it is at agent type coding tasks but 2 people think it isn't good.\n"
    "example-modelname-2: People discussed trying it for writing documentation but its too early to tell.\n"
    "Also, at the end you can make a notes section with any other interesting things you noticed about the posts.\n"
    "List any programming languages that certain models are mentioned as being particularly good or bad at, especially more rare languages or newer languages.\n"    
)
POSTS_PER_API_CALL_SCRIPT_DEFAULT = 5
ENV_DEFAULT_CHUNK_SIZE_VAR = "DEFAULT_POSTS_PER_API_CALL"
MAX_FAILURES_PER_MODEL = 2
MODELS_JSON_PATH_DEFAULT = "models.json" # Default path for models config
# --- End Script Configuration ---

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

load_dotenv() # Load .env for REDDIT_DB_PATH, DEFAULT_POSTS_PER_API_CALL etc.

DB_PATH_DEFAULT = os.getenv("REDDIT_DB_PATH", "data/reddit_data.db")

MODEL_CONFIGS = []
current_model_index = 0

def load_model_configs_from_json(json_path: str):
    """Loads LLM API configurations from a JSON file into MODEL_CONFIGS."""
    global MODEL_CONFIGS
    MODEL_CONFIGS = []
    logger.info(f"Loading LLM model configurations from JSON file: {json_path}")

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            raw_configs = json.load(f)
    except FileNotFoundError:
        logger.error(f"Models JSON file not found: {json_path}")
        return
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {json_path}: {e}")
        return
    except Exception as e:
        logger.error(f"An unexpected error occurred while reading {json_path}: {e}")
        return

    if not isinstance(raw_configs, list):
        logger.error(f"Expected a list of model configurations in {json_path}, but got {type(raw_configs)}.")
        return

    for i, config_entry in enumerate(raw_configs):
        if not isinstance(config_entry, dict):
            logger.warning(f"Skipping invalid entry (not a dictionary) at index {i} in {json_path}.")
            continue

        api_key = config_entry.get("apiKey")
        base_url = config_entry.get("openai_endpoint")
        model_id = config_entry.get("id") # This is the 'model' parameter for OpenAI client
        display_name = config_entry.get("displayName", model_id) # Fallback display name to model_id
        provider = config_entry.get("provider", "unknown")

        # Basic validation for required fields
        if not all([api_key, base_url, model_id]):
            logger.warning(f"Skipping incomplete model configuration at index {i} in {json_path} (missing apiKey, openai_endpoint, or id). Entry: {config_entry}")
            continue
        
        # Optional: Check provider if you want to enforce 'openai' compatibility
        if provider.lower() != "openai" and "openai_endpoint" not in config_entry:
             logger.warning(f"Model '{display_name}' (index {i}) provider is '{provider}' but does not explicitly define 'openai_endpoint'. Assuming it's OpenAI compatible due to presence of other fields.")


        MODEL_CONFIGS.append({
            "api_key": api_key,
            "base_url": base_url,
            "model_name": model_id, # Used as 'model' in API call
            "displayName": display_name, # For logging
            "failure_count": 0,
            "config_id": f"json_model_{i}" # Unique internal ID for this config
        })
        logger.info(f"Successfully loaded configuration for '{display_name}' (ID: {model_id}) from {json_path}")

    if not MODEL_CONFIGS:
        logger.warning(f"No valid LLM model configurations were loaded from {json_path}. The script may not be able to make API calls.")


def validate_date_string(date_str: str) -> datetime.date:
    """Validate and convert 'YYYY-MM-DD' string to a date object."""
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: '{date_str}'. Please use YYYY-MM-DD.")

def format_comments_text_recursive(
    parent_id_str: str,
    comments_by_parent_id: dict,
    all_comments_data: dict,
    level: int
) -> str:
    output_str = ""
    actual_parent_key = parent_id_str 
    if actual_parent_key not in comments_by_parent_id:
        return ""
    child_comment_ids = sorted(
        comments_by_parent_id[actual_parent_key],
        key=lambda cid: all_comments_data[cid]['created_utc']
    )
    for comment_id in child_comment_ids:
        comment_data = all_comments_data[comment_id]
        comment_body_text = comment_data.get('body', "").strip()
        comment_author = comment_data.get('author', '[deleted]')
        comment_created_utc = comment_data.get('created_utc', 0)
        try:
            comment_date_str = datetime.datetime.fromtimestamp(comment_created_utc, tz=datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        except (TypeError, ValueError, OSError): 
            comment_date_str = "[invalid date]"
        if comment_body_text and comment_body_text.lower() not in ('[deleted]', '[removed]'):
            comment_header_indent = "  " * level 
            text_indent = "  " * (level + 1) 
            output_str += f"{comment_header_indent}Comment by {comment_author} ({comment_date_str}):\n"
            for line in comment_body_text.splitlines():
                output_str += f"{text_indent}{line}\n"
            output_str += "\n" 
        output_str += format_comments_text_recursive(comment_id, comments_by_parent_id, all_comments_data, level + 1)
    return output_str

def format_single_post_with_comments_to_text(post_data: dict, formatted_comments_string: str) -> str:
    try:
        post_date_str = datetime.datetime.fromtimestamp(post_data['created_utc'], tz=datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    except (TypeError, ValueError, OSError):
        post_date_str = "[invalid date]"
    text = f"--- START OF REDDIT POST ---\n"
    text += f"Subreddit: r/{post_data.get('subreddit', 'unknown')}\n"
    text += f"Title: {post_data.get('title', 'N/A')}\n"
    text += f"Author: {post_data.get('author', '[deleted]')}\n"
    text += f"Date: {post_date_str}\n"
    text += f"URL: {post_data.get('url', 'N/A')}\n"
    post_selftext = post_data.get('selftext', '').strip()
    if post_selftext and post_selftext.lower() not in ('[deleted]', '[removed]'):
        text += f"Body:\n{post_selftext}\n\n"
    else:
        text += "Body: [No body text or body was deleted/removed]\n\n"
    text += f"--- COMMENTS FOR THIS POST ---\n"
    if formatted_comments_string.strip():
        text += formatted_comments_string
    else:
        text += "[No comments or comments were not processed for this post]\n\n"
    text += f"--- END OF REDDIT POST ---\n\n"
    return text

def fetch_and_format_posts_for_llm(db_conn: sqlite3.Connection, start_timestamp: int, end_timestamp: int):
    posts_cursor = db_conn.cursor()
    posts_query = """
        SELECT id, subreddit, title, author, url, created_utc, selftext
        FROM posts
        WHERE created_utc >= ? AND created_utc <= ?
        ORDER BY created_utc ASC;
    """
    try:
        logger.info(f"Querying posts between {datetime.datetime.fromtimestamp(start_timestamp, tz=datetime.timezone.utc)} and {datetime.datetime.fromtimestamp(end_timestamp, tz=datetime.timezone.utc)}")
        posts_cursor.execute(posts_query, (start_timestamp, end_timestamp))
    except sqlite3.Error as e:
        logger.error(f"Error querying posts: {e}")
        return 
    post_count = 0
    for post_row in posts_cursor:
        post_count += 1
        post_id, subreddit, title, author, url, post_created_utc, selftext = post_row
        logger.debug(f"Processing post ID: {post_id} from r/{subreddit}")
        post_data = {
            'id': post_id, 'subreddit': subreddit, 'title': title, 
            'author': author, 'url': url, 'created_utc': post_created_utc, 
            'selftext': selftext
        }
        comment_cursor = db_conn.cursor()
        comments_query = """
            SELECT id, parent_id, body, author, created_utc
            FROM comments
            WHERE post_id = ?
            ORDER BY created_utc ASC; 
        """
        try:
            comment_cursor.execute(comments_query, (post_id,))
            fetched_comments = comment_cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Error querying comments for post {post_id}: {e}. Proceeding without comments for this post.")
            fetched_comments = [] 
        all_comments_data = {} 
        comments_by_parent_id = defaultdict(list)
        if fetched_comments:
            for c_id, c_parent_id, c_body, c_author, c_created_utc in fetched_comments:
                all_comments_data[c_id] = {
                    'id': c_id, 'parent_id': c_parent_id, 'body': c_body,
                    'author': c_author, 'created_utc': c_created_utc
                }
                comments_by_parent_id[c_parent_id].append(c_id)
        formatted_comments_text = format_comments_text_recursive(
            post_id, comments_by_parent_id, all_comments_data, level=0 
        )
        yield format_single_post_with_comments_to_text(post_data, formatted_comments_text)
    logger.info(f"Finished fetching and formatting. Total posts retrieved from DB for date range: {post_count}")


def make_llm_api_call(model_config: dict, system_prompt: str, user_prompt_content: str, timeout_seconds: int = 180) -> str:
    logger.info(f"Attempting API call to model: '{model_config['displayName']}' (API Model ID: {model_config['model_name']}) at {model_config['base_url']}")
    
    if len(user_prompt_content) > 300000: # Rough character check
        logger.warning(f"User prompt content is very long ({len(user_prompt_content)} chars). This may exceed LLM token limits for '{model_config['displayName']}'.")

    client = OpenAI(
        api_key=model_config["api_key"],
        base_url=model_config["base_url"],
        timeout=timeout_seconds, 
        max_retries=0 
    )
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_content}
            ],
            model=model_config["model_name"], # Use the 'id' from JSON here
        )
        response_content = chat_completion.choices[0].message.content
        if response_content is None:
            logger.warning(f"LLM model '{model_config['displayName']}' returned a null/empty response.")
            return "[LLM returned no content]" 
        logger.info(f"Successfully received response from '{model_config['displayName']}'.")
        return response_content
    except APITimeoutError as e:
        logger.error(f"OpenAI API request timed out for model '{model_config['displayName']}': {e}")
        raise 
    except APIConnectionError as e:
        logger.error(f"OpenAI API connection error for model '{model_config['displayName']}': {e}")
        raise
    except RateLimitError as e:
        logger.error(f"OpenAI API rate limit exceeded for model '{model_config['displayName']}': {e}")
        raise
    except APIStatusError as e: 
        logger.error(f"OpenAI API returned an error status for model '{model_config['displayName']}' - Status {e.status_code}: {e.response.text if e.response else 'No response body'}")
        raise
    except Exception as e: 
        logger.error(f"An unexpected error occurred during API call to '{model_config['displayName']}': {e}", exc_info=True)
        raise


def process_data_with_llm(
    db_path: str, 
    start_date_str: str, 
    end_date_str: str, 
    output_filepath: str,
    posts_per_call: int,
    user_question: str
    ):
    global current_model_index 

    if not MODEL_CONFIGS:
        logger.critical("CRITICAL: No LLM models loaded. Aborting analysis. Please check models.json and relevant logs.")
        print("Error: No LLM model configurations found. Aborting.")
        return

    try:
        start_date_obj = validate_date_string(start_date_str)
        end_date_obj = validate_date_string(end_date_str)
    except argparse.ArgumentTypeError as e:
        logger.error(str(e)); print(f"Error: {e}"); return
    if start_date_obj > end_date_obj:
        logger.error("Start date cannot be after end date."); print("Error: Start date cannot be after end date."); return

    start_timestamp = int(datetime.datetime(start_date_obj.year, start_date_obj.month, start_date_obj.day, 0, 0, 0, tzinfo=datetime.timezone.utc).timestamp())
    end_timestamp = int(datetime.datetime(end_date_obj.year, end_date_obj.month, end_date_obj.day, 23, 59, 59, tzinfo=datetime.timezone.utc).timestamp())
    
    logger.info(f"Attempting to connect to database: {db_path}")
    if not os.path.exists(db_path):
        logger.error(f"Database file not found: {db_path}"); print(f"Error: Database file not found at {db_path}"); return
        
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        logger.info(f"Successfully connected to database: {db_path}")
        logger.info("Starting to fetch and format posts from database for the specified date range...")
        all_formatted_post_strings = list(fetch_and_format_posts_for_llm(conn, start_timestamp, end_timestamp))
        
        if not all_formatted_post_strings:
            logger.info("No posts found in the specified date range to process.")
            with open(output_filepath, 'w', encoding='utf-8') as md_file:
                md_file.write(f"# LLM Analysis of Reddit Posts\n\n"
                              f"**Date Range:** {start_date_str} to {end_date_str}\n"
                              f"**User Question:** \"{user_question}\"\n"
                              f"**System Prompt:** \"{SYSTEM_PROMPT}\"\n\n---\n\n"
                              "No posts found in the specified date range.\n")
            print(f"No posts found for the given date range. Output file '{output_filepath}' created with this information.")
            return

        total_posts = len(all_formatted_post_strings)
        num_chunks = (total_posts + posts_per_call - 1) // posts_per_call
        logger.info(f"Total posts to process: {total_posts}. This will be divided into {num_chunks} chunks of up to {posts_per_call} posts each.")

        with open(output_filepath, 'w', encoding='utf-8') as md_file:
            md_file.write(f"# LLM Analysis of Reddit Posts\n\n"
                          f"**Date Range:** {start_date_str} to {end_date_str}\n"
                          f"**User Question:**\n```\n{user_question}\n```\n\n"
                          f"**System Prompt:**\n```\n{SYSTEM_PROMPT}\n```\n\n"
                          f"**Processed {total_posts} posts in {num_chunks} API calls (chunks).**\n---\n\n"
                          "## Analysis Results\n\n")

            for i in range(0, total_posts, posts_per_call):
                chunk_post_strings = all_formatted_post_strings[i : i + posts_per_call]
                chunk_data_context = "".join(chunk_post_strings)
                full_llm_user_prompt = f"{user_question}\n\nHere is the Reddit data to analyze:\n\n{chunk_data_context}"
                post_range_start_idx = i + 1
                post_range_end_idx = min(i + posts_per_call, total_posts)
                chunk_num = (i // posts_per_call) + 1

                logger.info(f"--- Preparing Chunk {chunk_num}/{num_chunks} (posts {post_range_start_idx}-{post_range_end_idx}) ---")
                print(f"\n--- START OF DATA CHUNK FOR LLM (Chunk {chunk_num}/{num_chunks}) ---")
                print(full_llm_user_prompt)
                print(f"--- END OF DATA CHUNK FOR LLM (Chunk {chunk_num}/{num_chunks}) ---\n")
                logger.info(f"Data for chunk {chunk_num}/{num_chunks} prepared. Length: {len(full_llm_user_prompt)} characters.")

                llm_response = None
                used_model_display_name = "N/A"
                initial_attempt_model_idx_for_chunk = current_model_index 

                for attempt_idx_for_chunk in range(len(MODEL_CONFIGS)): # Iterate through all loaded models if needed
                    model_idx_to_try_now = (initial_attempt_model_idx_for_chunk + attempt_idx_for_chunk) % len(MODEL_CONFIGS)
                    current_config_for_attempt = MODEL_CONFIGS[model_idx_to_try_now]

                    if current_config_for_attempt["failure_count"] >= MAX_FAILURES_PER_MODEL:
                        logger.warning(f"Chunk {chunk_num}: Skipping model '{current_config_for_attempt['displayName']}' as it previously reached max failures ({current_config_for_attempt['failure_count']}).")
                        continue 

                    logger.info(f"Chunk {chunk_num}: Attempting API call with model '{current_config_for_attempt['displayName']}'. Model failure count: {current_config_for_attempt['failure_count']}")
                    
                    try:
                        llm_response = make_llm_api_call(current_config_for_attempt, SYSTEM_PROMPT, full_llm_user_prompt)
                        current_config_for_attempt["failure_count"] = 0 
                        current_model_index = model_idx_to_try_now 
                        used_model_display_name = current_config_for_attempt['displayName']
                        break 
                    except Exception as e:
                        logger.warning(f"Chunk {chunk_num}: API call to '{current_config_for_attempt['displayName']}' FAILED. Error: {type(e).__name__}. Incrementing failure count.")
                        current_config_for_attempt["failure_count"] += 1
                        if current_config_for_attempt["failure_count"] >= MAX_FAILURES_PER_MODEL:
                            logger.error(f"Chunk {chunk_num}: Model '{current_config_for_attempt['displayName']}' has now reached max failures ({current_config_for_attempt['failure_count']}).")
                    
                    if attempt_idx_for_chunk < len(MODEL_CONFIGS) -1 : # If there are more models to try for this chunk
                        wait_time = 5
                        logger.info(f"Chunk {chunk_num}: Waiting {wait_time} seconds before trying next model...")
                        time.sleep(wait_time)
                
                if llm_response:
                    md_file.write(f"### API call to model `{used_model_display_name}`, for posts {post_range_start_idx}-{post_range_end_idx} (chunk {chunk_num} of {num_chunks}), response:\n\n"
                                  f"```text\n{llm_response}\n```\n\n")
                    logger.info(f"Chunk {chunk_num}/{num_chunks} processed successfully with model '{used_model_display_name}'.")
                else:
                    logger.error(f"Chunk {chunk_num}/{num_chunks} (posts {post_range_start_idx}-{post_range_end_idx}): FAILED to get response after trying all available/eligible models.")
                    md_file.write(f"### FAILED to get response for posts {post_range_start_idx}-{post_range_end_idx} (chunk {chunk_num} of {num_chunks}). All configured models attempted or reached max failures.\n\n")
                
                if i + posts_per_call < total_posts: 
                    inter_chunk_wait = 2
                    logger.info(f"Waiting {inter_chunk_wait} seconds before processing next chunk...")
                    time.sleep(inter_chunk_wait)

            logger.info(f"LLM processing complete for all {num_chunks} chunks. Output saved to {output_filepath}")
            print(f"LLM processing complete. Output saved to {output_filepath}")

    except sqlite3.Error as e:
        logger.error(f"SQLite error during processing: {e}", exc_info=True); print(f"An error occurred while accessing the database: {e}")
    except IOError as e:
        logger.error(f"File I/O error: {e}", exc_info=True); print(f"An error occurred while writing to the file: {e}")
    except Exception as e:
        logger.critical(f"An unexpected critical error occurred during LLM processing: {e}", exc_info=True); print(f"An unexpected critical error occurred: {e}")
    finally:
        if conn: conn.close(); logger.info("Database connection closed.")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze Reddit posts and comments from SQLite DB using an LLM.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("start_date", type=str, help="Start date for fetching posts (YYYY-MM-DD).")
    parser.add_argument("end_date", type=str, help="End date for fetching posts (YYYY-MM-DD).")
    parser.add_argument("-o", "--output", type=str, default="data/llm_reddit_analysis.md", help="Path to the output markdown file (default: data/llm_reddit_analysis.md).")
    parser.add_argument("--db-path", type=str, default=DB_PATH_DEFAULT, help=f"Path to the SQLite database file (default: {DB_PATH_DEFAULT}, or from REDDIT_DB_PATH in .env).")
    parser.add_argument("--models-json", type=str, default=MODELS_JSON_PATH_DEFAULT, help=f"Path to the models.json configuration file (default: {MODELS_JSON_PATH_DEFAULT}).")
    parser.add_argument("--chunk-size", type=int, default=None, help=f"Number of posts per API call. Overrides .env ({ENV_DEFAULT_CHUNK_SIZE_VAR}) and script default ({POSTS_PER_API_CALL_SCRIPT_DEFAULT}).")
    parser.add_argument("--prompt", type=str, default=USER_QUESTION_PROMPT_DEFAULT, help="The question/prompt to ask the LLM. Enclose in quotes if it contains spaces.")
    args = parser.parse_args()

    if args.chunk_size is not None:
        posts_per_call = args.chunk_size
        logger.info(f"Using chunk size from command-line argument: {posts_per_call}")
    else:
        env_chunk_size_str = os.getenv(ENV_DEFAULT_CHUNK_SIZE_VAR)
        if env_chunk_size_str:
            try: posts_per_call = int(env_chunk_size_str); logger.info(f"Using chunk size from .env variable '{ENV_DEFAULT_CHUNK_SIZE_VAR}': {posts_per_call}")
            except ValueError: posts_per_call = POSTS_PER_API_CALL_SCRIPT_DEFAULT; logger.warning(f"Invalid value for {ENV_DEFAULT_CHUNK_SIZE_VAR} in .env: '{env_chunk_size_str}'. Using script default: {posts_per_call}")
        else: posts_per_call = POSTS_PER_API_CALL_SCRIPT_DEFAULT; logger.info(f"Using script default chunk size: {posts_per_call}")
    if posts_per_call <= 0: print("Error: Chunk size must be a positive integer."); logger.error(f"Invalid chunk size: {posts_per_call}. Must be > 0."); return

    load_model_configs_from_json(args.models_json) # Load models from JSON

    logger.info("--- LLM Reddit Analyzer Script Initializing ---")
    logger.info(f"Database path: {args.db_path}")
    logger.info(f"Models configuration: {args.models_json}")
    logger.info(f"Output file: {args.output}")
    logger.info(f"Date range: {args.start_date} to {args.end_date}")
    logger.info(f"User question for LLM: \"{args.prompt}\"")
    logger.info(f"Effective posts per API call (chunk size): {posts_per_call}")
    logger.info(f"Max failures per model before trying next (for current chunk): {MAX_FAILURES_PER_MODEL}")
    logger.info(f"System prompt for LLM: \"{SYSTEM_PROMPT}\"")
    logger.info(f"Total LLM configurations loaded: {len(MODEL_CONFIGS)}")
    logger.info("--- Initialization Complete - Starting Processing ---")
    
    process_data_with_llm(args.db_path, args.start_date, args.end_date, args.output, posts_per_call, args.prompt)
    logger.info("--- LLM Reddit Analyzer Script Finished ---")

if __name__ == "__main__":
    main()