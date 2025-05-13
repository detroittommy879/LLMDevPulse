import os
import re
from dotenv import load_dotenv
import praw

def main():
    load_dotenv()
    client_id = os.getenv("REDDIT_CLIENT_ID")
    client_secret = os.getenv("REDDIT_CLIENT_SECRET")
    user_agent = os.getenv("REDDIT_USER_AGENT")
    # Optional: username/password for script access
    username = os.getenv("REDDIT_USERNAME")
    password = os.getenv("REDDIT_PASSWORD")

    reddit_kwargs = dict(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )
    if username and password:
        reddit_kwargs["username"] = username
        reddit_kwargs["password"] = password

    reddit = praw.Reddit(**reddit_kwargs)

    with open("subreddits.txt", "r", encoding="utf-8") as f:
        subreddits = [line.strip() for line in f if line.strip()]
    with open("output.md", "w", encoding="utf-8") as out:
        for sub in subreddits:
            out.write(f"## r/{sub}\n\n")
            subreddit = reddit.subreddit(sub)
            for submission in subreddit.hot(limit=4):
                out.write(f"### {submission.title} (u/{submission.author})\n")
                out.write(f"- URL: https://reddit.com{submission.permalink}\n")
                out.write(f"- Posted: {submission.created_utc}\n")
                if submission.selftext:
                    out.write(f"**Body:**\n{submission.selftext}\n\n")
                else:
                    out.write(f"**Link:** {submission.url}\n\n")
                # Fetch all comments
                submission.comments.replace_more(limit=None)
                out.write("**Comments:**\n")
                for comment in submission.comments.list():
                    if comment.author:
                        out.write(f"- u/{comment.author}: {comment.body}\n")
                    else:
                        out.write(f"- [deleted]: {comment.body}\n")
                out.write("\n---\n\n")

if __name__ == "__main__":
    main()
