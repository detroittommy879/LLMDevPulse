import os
import re
from dotenv import load_dotenv
import praw

def main():
    print("Loading environment variables...")
    load_dotenv()
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT")
    username = os.getenv("REDDIT_USERNAME")
    password = os.getenv("REDDIT_PASSWORD")

    print("Preparing Reddit API credentials...")
    reddit_kwargs = dict(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )
    if username and password:
        reddit_kwargs["username"] = username
        reddit_kwargs["password"] = password

    print("Connecting to Reddit...")
    reddit = praw.Reddit(**reddit_kwargs)

    print("Reading subreddits from subreddits.txt...")
    with open("subreddits.txt", "r", encoding="utf-8") as f:
        subreddits = [line.strip() for line in f if line.strip()]
    print(f"Found {len(subreddits)} subreddits.")

    with open("output.md", "w", encoding="utf-8") as out:
        for sub in subreddits:
            print(f"Processing subreddit: r/{sub}")
            out.write(f"## r/{sub}\n\n")
            out.flush()
            os.fsync(out.fileno())
            subreddit = reddit.subreddit(sub)
            for submission in subreddit.hot(limit=4):
                print(f"  Fetching post: {submission.title} (u/{submission.author})")
                out.write(f"### {submission.title} (u/{submission.author})\n")
                out.write(f"- URL: https://reddit.com{submission.permalink}\n")
                out.write(f"- Posted: {submission.created_utc}\n")
                if submission.selftext:
                    out.write(f"**Body:**\n{submission.selftext}\n\n")
                else:
                    out.write(f"**Link:** {submission.url}\n\n")
                out.flush()
                os.fsync(out.fileno())
                print("    Fetching comments...")
                submission.comments.replace_more(limit=None)
                out.write("**Comments:**\n")
                for comment in submission.comments.list():
                    if comment.author:
                        out.write(f"- u/{comment.author}: {comment.body}\n")
                        print(f"      Comment by u/{comment.author}")
                    else:
                        out.write(f"- [deleted]: {comment.body}\n")
                        print("      Comment by [deleted]")
                    out.flush()
                    os.fsync(out.fileno())
                out.write("\n---\n\n")
                out.flush()
                os.fsync(out.fileno())
            print(f"Finished processing r/{sub}")

if __name__ == "__main__":
    main()
