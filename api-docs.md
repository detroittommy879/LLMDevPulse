Quick Start
In this section, we go over everything you need to know to start building scripts or bots using PRAW, the Python Reddit API Wrapper. It’s fun and easy. Let’s get started.

Prerequisites
Python Knowledge:
You need to know at least a little Python to use PRAW. PRAW supports Python 3.7+. If you are stuck on a problem, r/learnpython is a great place to ask for help.

Reddit Knowledge:
A basic understanding of how Reddit works is a must. In the event you are not already familiar with Reddit start at Reddit Help.

Reddit Account:
A Reddit account is required to access Reddit’s API. Create one at reddit.com.

Client ID & Client Secret:
These two values are needed to access Reddit’s API as a script application (see Authenticating via OAuth for other application types). If you don’t already have a client ID and client secret, follow Reddit’s First Steps Guide to create them.

User Agent:
A user agent is a unique identifier that helps Reddit determine the source of network requests. To use Reddit’s API, you need a unique and descriptive user agent. The recommended format is <platform>:<app ID>:<version string> (by u/<Reddit username>). For example, android:com.example.myredditapp:v1.2.3 (by u/kemitche). Read more about user agents at Reddit’s API wiki page.

With these prerequisites satisfied, you are ready to learn how to do some of the most common tasks with Reddit’s API.

Common Tasks
Obtain a Reddit Instance
Warning

For the sake of brevity, the following examples pass authentication information via arguments to praw.Reddit(). If you do this, you need to be careful not to reveal this information to the outside world if you share your code. It is recommended to use a praw.ini file in order to keep your authentication information separate from your code.

You need an instance of the Reddit class to do anything with PRAW. There are two distinct states a Reddit instance can be in: read-only, and authorized.

Read-only Reddit Instances
To create a read-only Reddit instance, you need three pieces of information:

Client ID

Client secret

User agent

You may choose to provide these by passing in three keyword arguments when calling the initializer of the Reddit class: client_id, client_secret, user_agent (see Configuring PRAW for other methods of providing this information). For example:

import praw

reddit = praw.Reddit(
client_id="my client id",
client_secret="my client secret",
user_agent="my user agent",
)
Just like that, you now have a read-only Reddit instance.

print(reddit.read_only)

# Output: True

With a read-only instance, you can do something like obtaining 10 “hot” submissions from r/test:

# continued from code above

for submission in reddit.subreddit("test").hot(limit=10):
print(submission.title)

# Output: 10 submissions

If you want to do more than retrieve public information from Reddit, then you need an authorized Reddit instance.

Note

In the above example we are limiting the results to 10. Without the limit parameter PRAW should yield as many results as it can with a single request. For most endpoints this results in 100 items per request. If you want to retrieve as many as possible pass in limit=None.

Authorized Reddit Instances
In order to create an authorized Reddit instance, two additional pieces of information are required for script applications (see Authenticating via OAuth for other application types):

Your Reddit username, and

Your Reddit password

Again, you may choose to provide these by passing in keyword arguments username and password when you call the Reddit initializer, like the following:

import praw

reddit = praw.Reddit(
client_id="my client id",
client_secret="my client secret",
password="my password",
user_agent="my user agent",
username="my username",
)

print(reddit.read_only)

# Output: False

Now you can do whatever your Reddit account is authorized to do. And you can switch back to read-only mode whenever you want:

# continued from code above

reddit.read_only = True
Note

If you are uncomfortable hard-coding your credentials into your program, there are some options available to you. Please see: Configuring PRAW.

Obtain a Subreddit
To obtain a Subreddit instance, pass the subreddit’s name when calling subreddit on your Reddit instance. For example:

# assume you have a praw.Reddit instance bound to variable `reddit`

subreddit = reddit.subreddit("redditdev")

print(subreddit.display_name)

# Output: redditdev

print(subreddit.title)

# Output: reddit development

print(subreddit.description)

# Output: a subreddit for discussion of ...

Obtain Submission Instances from a Subreddit
Now that you have a Subreddit instance, you can iterate through some of its submissions, each bound to an instance of Submission. There are several sorts that you can iterate through:

controversial

gilded

hot

new

rising

top

Each of these methods will immediately return a ListingGenerator, which is to be iterated through. For example, to iterate through the first 10 submissions based on the hot sort for a given subreddit try:

# assume you have a Subreddit instance bound to variable `subreddit`

for submission in subreddit.hot(limit=10):
print(submission.title) # Output: the submission's title
print(submission.score) # Output: the submission's score
print(submission.id) # Output: the submission's ID
print(submission.url) # Output: the URL the submission points to or the submission's URL if it's a self post
Note

The act of calling a method that returns a ListingGenerator does not result in any network requests until you begin to iterate through the ListingGenerator.

You can create Submission instances in other ways too:

# assume you have a praw.Reddit instance bound to variable `reddit`

submission = reddit.submission("39zje0")
print(submission.title)

# Output: reddit will soon only be available ...

# or

submission = reddit.submission(url="https://www.reddit.com/...")
Obtain Redditor Instances
There are several ways to obtain a redditor (a Redditor instance). Two of the most common ones are:

via the author attribute of a Submission or Comment instance

via the redditor() method of Reddit

For example:

# assume you have a Submission instance bound to variable `submission`

redditor1 = submission.author
print(redditor1.name)

# Output: name of the redditor

# assume you have a praw.Reddit instance bound to variable `reddit`

redditor2 = reddit.redditor("bboe")
print(redditor2.link_karma)

# Output: u/bboe's karma

Obtain Comment Instances
Submissions have a comments attribute that is a CommentForest instance. That instance is iterable and represents the top-level comments of the submission by the default comment sort (confidence). If you instead want to iterate over all comments as a flattened list you can call the list() method on a CommentForest instance. For example:

# assume you have a praw.Reddit instance bound to variable `reddit`

top_level_comments = list(submission.comments)
all_comments = submission.comments.list()
Note

The comment sort order can be changed by updating the value of comment_sort on the Submission instance prior to accessing comments (see: /api/set_suggested_sort for possible values). For example to have comments sorted by new try something like:

# assume you have a praw.Reddit instance bound to variable `reddit`

submission = reddit.submission("39zje0")
submission.comment_sort = "new"
top_level_comments = list(submission.comments)
As you may be aware there will periodically be MoreComments instances scattered throughout the forest. Replace those MoreComments instances at any time by calling replace_more() on a CommentForest instance. Calling replace_more() access comments, and so must be done after comment_sort is updated. See Extracting comments with PRAW for an example.

Determine Available Attributes of an Object
If you have a PRAW object, e.g., Comment, Message, Redditor, or Submission, and you want to see what attributes are available along with their values, use the built-in vars() function of python. For example:

import pprint

# assume you have a praw.Reddit instance bound to variable `reddit`

submission = reddit.submission("39zje0")
print(submission.title) # to make it non-lazy
pprint.pprint(vars(submission))
Note the line where we print the title. PRAW uses lazy objects so that network requests to Reddit’s API are only issued when information is needed. Here, before the print line, submission points to a lazy Submission object. When we try to print its title, additional information is needed, thus a network request is made, and the instances ceases to be lazy. Outputting all the attributes of a lazy object will result in fewer attributes than expected.

Authenticating via OAuth
PRAW supports all three types of applications that can be registered on Reddit. Those are:

Web Applications

Installed Applications

Script Applications

Before you can use any one of these with PRAW, you must first register an application of the appropriate type on Reddit.

If your application does not require a user context, it is read-only.

PRAW supports the flows that each of these applications can use. The following table defines which application types can use which flows:

Application Type

Script

Web

Installed

Default Flow

Password

Code

Alternative Flows

Code

Application-Only (Client Credentials)

Implicit

Application-Only (Client Credentials)

Application-Only (Installed Client)

Warning

For the sake of brevity, the following examples pass authentication information via arguments to Reddit. If you do this, you need to be careful not to reveal this information to the outside world if you share your code. It is recommended to use a praw.ini file in order to keep your authentication information separate from your code.

Password Flow
Password Flow is the simplest type of authentication flow to work with because no callback process is involved in obtaining an access_token.

While password flow applications do not involve a redirect URI, Reddit still requires that you provide one when registering your script application – http://localhost:8080 is a simple one to use.

In order to use a password flow application with PRAW you need four pieces of information:

client_id:
The client ID is at least a 14-character string listed just under “personal use script” for the desired developed application

client_secret:
The client secret is at least a 27-character string listed adjacent to secret for the application.

password:
The password for the Reddit account used to register the application.

username:
The username of the Reddit account used to register the application.

With this information authorizing as username using a password flow app is as simple as:

reddit = praw.Reddit(
client_id="SI8pN3DSbt0zor",
client_secret="xaxkj7HNh8kwg8e5t4m6KvSrbTI",
password="1guiwevlfo00esyy",
user_agent="testscript by u/fakebot3",
username="fakebot3",
)
To verify that you are authenticated as the correct user run:

print(reddit.user.me())
The output should contain the same name as you entered for username.

Note

If the following exception is raised, double-check your credentials, and ensure that that the username and password you are using are for the same user with which the application is associated:

OAuthException: invalid_grant error processing request
Two-Factor Authentication
A 2FA token can be used by joining it to the password with a colon:

reddit = praw.Reddit(
client_id="SI8pN3DSbt0zor",
client_secret="xaxkj7HNh8kwg8e5t4m6KvSrbTI",
password="1guiwevlfo00esyy:955413",
user_agent="testscript by u/fakebot3",
username="fakebot3",
)
However, for such an app there is little benefit to using 2FA. The token must be refreshed after one hour; therefore, the 2FA secret would have to be stored along with the rest of the credentials in order to generate the token, which defeats the point of having an extra credential beyond the password.

If you do choose to use 2FA, you must handle the prawcore.OAuthException that will be raised by API calls after one hour.

Code Flow
A code flow application is useful for two primary purposes:

You have an application and want to be able to access Reddit from your users’ accounts.

You have a personal-use script application and you either want to

limit the access one of your PRAW-based programs has to Reddit

avoid the hassle of 2FA (described above)

not pass your username and password to PRAW (and thus not keep it in memory)

When registering your application you must provide a valid redirect URI. If you are running a website you will want to enter the appropriate callback URL and configure that endpoint to complete the code flow.

If you aren’t actually running a website, you can follow the Working with Refresh Tokens tutorial to learn how to obtain and use the initial refresh token.

Whether or not you follow the Working with Refresh Tokens tutorial there are two processes involved in obtaining access or refresh tokens.

Obtain the Authorization URL
The first step to completing the code flow is to obtain the authorization URL. You can do that as follows:

reddit = praw.Reddit(
client_id="SI8pN3DSbt0zor",
client_secret="xaxkj7HNh8kwg8e5t4m6KvSrbTI",
redirect_uri="http://localhost:8080",
user_agent="testscript by u/fakebot3",
)
print(reddit.auth.url(scopes=["identity"], state="...", duration="permanent"))
The above will output an authorization URL for a permanent token (i.e., the resulting authorization will include both a short-lived access_token, and a longer-lived, single use refresh_token) that has only the identity scope. See url() for more information on these parameters.

This URL should be accessed by the account that desires to authorize their Reddit access to your application. On completion of that flow, the user’s browser will be redirected to the specified redirect_uri. After verifying the state and extracting the code you can obtain the refresh token via:

print(reddit.auth.authorize(code))
print(reddit.user.me())
The first line of output is the refresh_token. You can save this for later use (see Using a Saved Refresh Token).

The second line of output reveals the name of the Redditor that completed the code flow. It also indicates that the Reddit instance is now associated with that account.

The code flow can be used with an installed application just as described above with one change: set the value of client_secret to None when initializing Reddit.

Implicit Flow
The implicit flow requires a similar instantiation of the Reddit class as done in Code Flow, however, the token is returned directly as part of the redirect. For the implicit flow call url() like so:

print(reddit.auth.url(scopes=["identity"], state="...", implicit=True))
Then use implicit() to provide the authorization to the Reddit instance.

Read-Only Mode
All application types support a read-only mode. Read-only mode provides access to Reddit like a logged out user would see including the default subreddits in the reddit.front listings.

In the absence of a refresh_token both Code Flow and Implicit Flow applications start in the read-only mode. With such applications read-only mode is disabled when authorize(), or implicit() are successfully called. Password Flow applications start up with read-only mode disabled.

Read-only mode can be toggled via:

# Enable read-only mode

reddit.read_only = True

# Disable read-only mode (must have a valid authorization)

reddit.read_only = False
Application-Only Flows
The following flows are the read-only mode flows for Reddit applications

Application-Only (Client Credentials)
This is the default flow for read-only mode in script and web applications. The idea behind this is that Reddit can trust these applications as coming from a given developer, however the application requires no logged-in user context.

An installed application cannot use this flow, because Reddit requires a client_secret to be given if this flow is being used. In other words, installed applications are not considered confidential clients.

Application-Only (Installed Client)
This is the default flow for read-only mode in installed applications. The idea behind this is that Reddit might not be able to trust these applications as coming from a given developer. This would be able to happen if someone other than the developer can potentially replicate the client information and then pretend to be the application, such as in installed applications where the end user could retrieve the client_id.

Note

No benefit is really gained from this in script or web apps. The one exception is for when a script or web app has multiple end users, this will allow you to give Reddit the information needed in order to distinguish different users of your app from each other (as the supplied device ID should be a unique string per both device (in the case of a web app, server) and user (in the case of a web app, browser session).

Using a Saved Refresh Token
A saved refresh token can be used to immediately obtain an authorized instance of Reddit like so:

reddit = praw.Reddit(
client_id="SI8pN3DSbt0zor",
client_secret="xaxkj7HNh8kwg8e5t4m6KvSrbTI",
refresh_token="WeheY7PwgeCZj4S3QgUcLhKE5S2s4eAYdxM",
user_agent="testscript by u/fakebot3",
)
print(reddit.auth.scopes())
The output from the above code displays which scopes are available on the Reddit instance.

Note

Observe that redirect_uri does not need to be provided in such cases. It is only needed when url() is used.
Comment Extraction and Parsing
A common use for Reddit’s API is to extract comments from submissions and use them to perform keyword or phrase analysis.

As always, you need to begin by creating an instance of Reddit:

import praw

reddit = praw.Reddit(
client_id="CLIENT_ID",
client_secret="CLIENT_SECRET",
password="PASSWORD",
user_agent="Comment Extraction (by u/USERNAME)",
username="USERNAME",
)
Note

If you are only analyzing public comments, entering a username and password is optional.

In this document, we will detail the process of finding all the comments for a given submission. If you instead want to process all comments on Reddit, or comments belonging to one or more specific subreddits, please see SubredditStream.comments().

Extracting comments with PRAW
Assume we want to process the comments for this submission: https://www.reddit.com/r/funny/comments/3g1jfi/buttons/

We first need to obtain a submission object. We can do that either with the entire URL:

url = "https://www.reddit.com/r/funny/comments/3g1jfi/buttons/"
submission = reddit.submission(url=url)
or with the submission’s ID which comes after comments/ in the URL:

submission = reddit.submission("3g1jfi")
With a submission object we can then interact with its CommentForest through the submission’s Submission.comments attribute. A CommentForest is a list of top-level comments each of which contains a CommentForest of replies.

If we wanted to output only the body of the top-level comments in the thread we could do:

for top_level_comment in submission.comments:
print(top_level_comment.body)
While running this you will most likely encounter the exception AttributeError: 'MoreComments' object has no attribute 'body'. This submission’s comment forest contains a number of MoreComments objects. These objects represent the “load more comments”, and “continue this thread” links encountered on the website. While we could ignore MoreComments in our code, like so:

from praw.models import MoreComments

for top_level_comment in submission.comments:
if isinstance(top_level_comment, MoreComments):
continue
print(top_level_comment.body)
The replace_more method
In the previous snippet, we used isinstance() to check whether the item in the comment list was a MoreComments so that we could ignore it. But there is a better way: the CommentForest object has a method called replace_more(), which replaces or removes MoreComments objects from the forest.

Each replacement requires one network request, and its response may yield additional MoreComments instances. As a result, by default, replace_more() only replaces at most 32 MoreComments instances – all other instances are simply removed. The maximum number of instances to replace can be configured via the limit parameter. Additionally a threshold parameter can be set to only perform replacement of MoreComments instances that represent a minimum number of comments; it defaults to 0, meaning all MoreComments instances will be replaced up to limit.

A limit of 0 simply removes all MoreComments from the forest. The previous snippet can thus be simplified:

submission.comments.replace_more(limit=0)
for top_level_comment in submission.comments:
print(top_level_comment.body)
Note

Calling replace_more() is destructive. Calling it again on the same submission instance has no effect.

Meanwhile, a limit of None means that all MoreComments objects will be replaced until there are none left, as long as they satisfy the threshold.

submission.comments.replace_more(limit=None)
for top_level_comment in submission.comments:
print(top_level_comment.body)
Now we are able to successfully iterate over all the top-level comments. What about their replies? We could output all second-level comments like so:

submission.comments.replace_more(limit=None)
for top_level_comment in submission.comments:
for second_level_comment in top_level_comment.replies:
print(second_level_comment.body)
However, the comment forest can be arbitrarily deep, so we’ll want a more robust solution. One way to iterate over a tree, or forest, is via a breadth-first traversal using a queue:

submission.comments.replace_more(limit=None)
comment_queue = submission.comments[:] # Seed with top-level
while comment_queue:
comment = comment_queue.pop(0)
print(comment.body)
comment_queue.extend(comment.replies)
The above code will output all the top-level comments, followed by second-level, third-level, etc. While it is awesome to be able to do your own breadth-first traversals, CommentForest provides a convenience method, list(), which returns a list of comments traversed in the same order as the code above. Thus the above can be rewritten as:

submission.comments.replace_more(limit=None)
for comment in submission.comments.list():
print(comment.body)
You can now properly extract and parse all (or most) of the comments belonging to a single submission. Combine this with submission iteration and you can build some really cool stuff.

Finally, note that the value of submission.num_comments may not match up 100% with the number of comments extracted via PRAW. This discrepancy is normal as that count includes deleted, removed, and spam comments.

Next
Working with Refresh Tokens
Previous
Util
Copyright © 2023, Bryce Boe
Made with Sphinx and @pradyunsg's Furo
Ratelimits
Even though PRAW respects the X-Ratelimit-\* headers and waits the appropriate time between requests, there are other unknown ratelimits that Reddit has that might require additional wait time (anywhere from milliseconds to minutes) for things such as commenting, editing comments/posts, banning users, adding moderators, etc. PRAW will sleep and try the request again if the requested wait time (as much as 600 seconds) is less than or equal to PRAW’s ratelimit_seconds configuration setting (default: 5s), PRAW will wait for the requested time plus 1 second. If the requested wait time exceeds the set value of ratelimit_seconds, PRAW will raise RedditAPIException.

For example, given the following Reddit instance:

import praw

reddit = praw.Reddit(..., ratelimit_seconds=300)
Let’s say your bot posts a comment to Reddit every 30 seconds and Reddit returns the ratelimit error: "You're doing that too much. Try again in 3 minutes.". PRAW will wait for 181 seconds since 181 seconds is less than the configured ratelimit_seconds of 300 seconds. However, if Reddit returns the ratelimit error: "You're doing that too much. Try again in 6 minutes.", PRAW will raise an exception since 360 seconds is greater than the configured ratelimit_seconds of 300 seconds.
