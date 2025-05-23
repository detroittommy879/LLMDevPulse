'''AI Code Prep GUI - Vibe Code Faster
Tom Brothers
1 rating

This SAVES YOU TIME! No more copy paste copy paste!

We have lots of tools to code with AI today.. like Cursor, Cline, Windsurf, v0, but sometimes they do not give the AI the right context. Often way too little or too much causing the LLM to get confused.

Then you are like "ah.. ugh" and have to copy lots of code to a AI chat (Gemini in AI studio, ChatGPT, Openrouter, Claude 3.5 or 3.7 Sonnet, etc) and you have to copy and paste each file over and over, it sucks. That's why I created this little app.

Windows GUI application (also have Mac and Electron/Linux) designed to streamline the process of sharing your project's code with ChatGPT, Claude, other AI chatbots. It allows you to quickly gather code files into a single text file and copy the content to your clipboard, making it easy to paste into AI chatbots for coding assistance. Uses xml (or markdown) tags that AI understands.

Purpose

The main goal of aicodeprep is to save time, and save on tokens. Instead of copying and pasting over and over for each code file, it auto-detects most likely needed files, and lets you check or uncheck any other files to add/subtract. With the GUI, you can effortlessly right click in a folder, select/unselect files, then process to clipboard/txt file with automatic tags and filenames in the text.

Features

Right-Click Context Menu: After installation, you can right-click in any Windows folder, click AI Code Prep GUI, to open the GUI and auto-detect code files.

It auto-skips the ones that you probably don't need to copy, like node files or .min.css, git files, etc.

Easy Processing: Click "Process Selected" to compile code into fullcode.txt and copy it to the clipboard.

This version is lean but if you want a different version that is more polished looking, look on my profile for the Electron versions. Also have a Mac version.

## -- Buying this will get you the newest Windows version, the older Windows version (just in case the updated one glitches or something), and a Linux version

## It may not look sophisticated, but a lot of other tools will burn though way too many tokens from including too much information in each API call. Claude 3.5 Sonnet will cut you off if you use too many too fast. This allows fine control and it saves you money. It's designed for speed, something I personally use every day.

When you use the app and click some files, and click Process Selected, the output to clipboard and fullcode.txt looks like this:

## Example output:

App.css:
<code>
..code here..
</code>

App.jsx:
<code>
..code here..
</code>

firebase.js:
<code>
..code here..
</code>

fileName.cpp:
</code>
code from file here...
</code>

Text from prompt box here...

---

Then you can quickly paste it right into Gemini on AI studio, ChatGPT, Deepseek, etc.

Made a Mac version and also a Web/Electron version.
<ai> <code> <aicodeprep> <claude> <ChatGPT> <llm> <deepseek> <openai> <vibe coding>

### Updated April 30 2025...

- Collapsable/Expandable folders, automatic expand if code detected

- Token counter (live, as you click files)

- Better smart file automatic pre-checking on load

- Saves an .aicodeprep file with the files you last had checked in that folder, plus your window size / adjustment preferences. This helps when you need to keep grabbing the code / context often for the same project. I hated having to click the same boxes over again so it's a great feature.

- Optional prompt box to type in something such as a question to ask AI - it just appends this to the bottom of the code context section - which will be on the clipboard and fullcode.txt

- Sorry Mac version hasn't been compiled yet, will soon. This zip contains the newest Windows version, the older Windows version (in case something goes wrong, at least we know the older one is very stable), and a Linux version all in one zip file. Standard Windows installer wizards.

- Also included a html guide/writeup of how to vibe code or use AI to help code, using the best models but still being cheap, even free. It took a while to figure all that stuff out on there so it should save anyone some time. What models to use when, what do you do if you want to save money, how to debug free and which web chat's you can use free/unlimited. As of today, your options are wild 😂
  '''
  other info - this is how to code on a budget, cheap, and know which models to use:
  The link for this is https://wuu73.org/blog/guide.html

'''How I Code with AI on a budget/free My Browser Setup: The Free AI Buffet
First things first, I have a browser open loaded with tabs pointing to the free tiers of powerful AI models. Why stick to one when you can get multiple perspectives for free? My typical lineup includes:

At least one tab of Google Gemini AI Studio (Gemini 2.5 Pro/Flash are often free and unlimited here).
Several tabs of OpenRouter, set to several models, some free models they offer.
At least one tab for ChatGPT (the free version is still useful).
At least one tab for Perplexity AI, especially good for research-heavy questions.
At least one tab for Deepseek (v3 and r1 are free on their web interface, though watch the context limit).
At least one tab for Grok.com. Good, free and seemingly unlimited for general use and deep research/image editing.
Sometimes Poe.com for its free daily credits on premium models like Claude or o4.
Phind is another free one worth checking out.
The Core Workflow: Manual Context is King
AI in web chat's are almost always better at solving problems, and coming up with solutions compared to the agents like Cline, Trae, Copilot.. Not always, but usually.

So I use my tool often, to generate the context bundle. Then I paste it into one of the many AI web chat's (sometimes more than one, since they sometimes give different answers) and just ask it questions or ask it to code review, to try to figure out why x is happening when y is happening...etc

After doing this for a while, you really get a feel for which models excel at which types of tasks. I plan to collect more data on this eventually, but for now, hands-on experience is key.

How AI Code Prep Helps (Example Prompt Structure):

Can you help me debug/figure out why my app is not working when a, b, and c happens? Here are all the relevant code files:

Then, AI Code Prep GUI (for Windows/Mac - check the site for Mac instructions) steps in. It recursively scans your project folder (subfolders, sub-subfolders, you name it) and grabs the code, formatting it nicely like this:

The tool generates output similar to this structure:

fileName.js:
<code>
... the contents of the file..
</code>

nextFile.py:
<code>
import example
...etc
</code>
On Windows, you just right-click somewhere inside your project folder (or on the folder itself) and select "AI Code Prep GUI" from the context menu (look at the screenshots on the site). A GUI window pops up, usually with the right code files pre-selected. It smartly tries to skip things you likely don't need, like node_modules, .git, etc. If its guess isn't perfect, you can easily check or uncheck files.

This is super useful when your project is huge and blows past an AI's context limit. You can manually curate exactly what the AI needs to see.

The problem with many coding agents like Cline, Github Copilot, Cursor, Windsurf, etc., is that they often send either WAY too much context or WAY too little. This is why they can seem dumb or ineffective sometimes. Sometimes, you just gotta do things yourself, use a tool like mine to select the files yourself, but it helps auto-select the code files while skipping the stuff you probably don't need (but still have the option to add what you want with the checkboxes) and then dump that curated context into several AIs (especially the free web ones!).

Sure, there are other context-generating tools, but many are command-line only, or need a public GitHub repo link. What if your code is private? What if you want to keep it local? What if you prefer checkboxes on a GUI? For something like this a GUI makes sense.

Model Strategy: Picking the Right Brain for the Job
Since many great models are free to use via web interfaces (like Gemini in AI Studio, Grok, Deepseek), I prioritize these. Poe.com also gives free daily credits for top models like Claude and the new o4 series.

Gemini 2.5 Pro/Preview (via AI Studio) is great for debugging, great for planning, and also finding it the best at lots of things now. For really thorny issues, I might try the new o4-mini (available via OpenRouter or Poe). It surprisingly fixed a persistent bug for me right away, though I'm still figuring out its best use cases. It's notably cheaper via API than the previous top dogs like Claude 3.5/3.7.

I usually try Claude 3.7 at some point, maybe via Poe or API (OpenRouter makes this easy), but it's pricier for frequent use. Think of Claude 3.7 as Claude on caffeine – brilliant, sometimes verbose, maybe a bit 'psychotic' like Hunter S. Thompson. Lots of great output, but you might need a calmer model like Claude 3.5 to refine it or do the actual coding.

OpenRouter is my go-to for API access. It has tons of free models and all the latest paid ones like GPT 4.1 & 4.1 mini and o4-mini. Bonus is it doesn't have that problem from the official Claude API from Anthropic where its constantly overloaded (common issue widely talked about, those people can save themselves the pain by using Openrouter's API). Oh! and GPT 4.1 mini is real good!! I use it a lot now and its FAST and low cost.

Using Cline (The AI Coding Agent)
I have OpenRouter set up in Cline for when I need API access, but be warned, it can get expensive fast. The GitHub Copilot API, however, is super cheap ($10/month as of writing, though this could change) and Cline can use it!

I find GPT 4.1 (via API, often through Copilot's endpoint in Cline) is currently the best for doing the actual coding within the agent. Some smarter models like o4-mini can be slower or mess up when using agentic tools/commands in Cline.

My Agent Workflow:

Plan & Brainstorm: Use the smarter/free web models (Gemini 2.5, o4-mini, Claude 3.7, Grok, etc.) to figure out the approach, plan the steps, identify libraries, etc.
Generate Agent Prompt: Ask one of these smart models: "Write a detailed-enough prompt for Cline, my AI coding agent, to complete the following tasks: [describe tasks]". Sometimes, I'll copy this generated prompt and paste it into another free AI good at rewriting (like ChatGPT) to refine it further.
Execute with Cline: Paste the step-by-step task list into Cline, configured to use a stable and efficient model like GPT 4.1 or 4.1 Mini (its insanely great, seems about equal to regular 4.1, cost effective). The 4.1's have been trained to follow instructions well.
Fallback: If GPT 4.1 struggles, switch Cline to use Claude 3.5 via API. It seems to be the next best for reliable execution.
Essentially: Use expensive/smart models (and the excellent free Gemini 2.5 Pro) to strategize and plan. Validate the plan by pasting it into 2-3 other free models (Deepseek R1, Claude on Poe if context allows) and ask "Is this good? Can you improve it or find flaws?". Then, use a stable workhorse like GPT 4.1 or Claude 3.5 within Cline to do the heavy lifting (coding).

o4-mini seems particularly adept at untangling complex code logic or figuring out high-level implementation strategies (like choosing frameworks or libraries). I'll often throw my initial idea at Gemini 2.5, o4-mini, GPT 4.1, ChatGPT, maybe o3-mini (try duck.ai - often free), and Phind to get a range of ideas. If the free/cheap options don't crack it, I'll escalate to pricier models via API.

Alternative Agents & Setups
Trae.ai (from Bytedance) offers models like GPT 4.1 and Claude 3.7 for free sometimes, but I find its built-in agent isn't as robust as Cline. However, since Trae seems to be a VS Code clone, you can likely install the Cline extension within it!

So, you could have two setups:

VS Code + Cline extension + Copilot extension (get the $10/mo subscription for cheap API access via Cline, though the free tier might offer some basic use).
Trae.ai + Cline extension (potentially leveraging Trae's free model access if Cline can use it, or using your own API keys).
Try both! Sometimes the native Copilot agent solves things Cline struggles with, and vice-versa. I suspect Cline sometimes sends overly large prompts which might hinder performance on certain tasks compared to the more integrated Copilot agent.

Cline for VS Code is free, but remember you pay for the API calls unless you're leveraging the Copilot subscription trick. Using the VS Code LM API setting in Cline with a $10/month Copilot sub is currently the most cost-effective way to get near-unlimited access to powerful models within the agent.

Worth Checking Out: New Models & Tools
chat.qwen.ai – Qwen 3
Newer model, worth a try for chat and coding tasks.
Cline: You can set separate plan & act AI models.
Paying as you go and want to save some money?

Sign up on Openrouter
claude 3.7 / gemini 2.5 pro / o4-mini for plan mode
gpt 4.1 mini for act mode (do the coding). I have not tested 4.1 nano.
Roo Code is an alternative to Cline, its a clone but different – worth installing, so you can try both and see what works best for what. Some users find Cline more stable, but results may vary.
Some Thoughts
AI is an incredible force multiplier, but it’s not a magic wand. The real magic happens when you combine your curiosity, persistence, and willingness to experiment with these powerful tools. Don’t get discouraged by bugs or setbacks—every challenge is a chance to learn something new. Mix and match models, try wild ideas, and don’t be afraid to break things and rebuild. The best coders aren’t the ones who never get stuck—they’re the ones who keep moving forward, using every tool and trick at their disposal. Embrace the chaos, enjoy the process, and let your creativity lead the way!'''

Link to buy AI Code Prep GUI: https://wuu73.org/aicp
