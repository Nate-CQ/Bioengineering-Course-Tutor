# Course Tutor

A practice question generator, answer checker, and step-by-step explainer for four bioengineering courses: Bioengineering Signals and Systems, Principles of Human Physiology, Biomaterials, and Biological Data Science I (Fundamentals of Biostatistics).

## Features

- Multiple choice, fill-in-the-blank, short answer, and long-form problem questions, generated fresh each time and matched to your current skill level
- Automatic difficulty adjustment based on your performance, with a calibration phase for new topics
<<<<<<< HEAD
- Questions stay varied: the app avoids repeating the same question or defaulting to the same go-to example every time
- Password-protected accounts, so your progress is genuinely yours and can't be overwritten by someone else using the same name
=======
- Progress saved across sessions under a username, no password required
>>>>>>> 0ec3714f93e0df1313327e958b3fb8eda2716abf
- Short answers and long-form problems graded against a rubric, with partial credit
- Built-in explainer: paste any concept or problem set question for a step-by-step walkthrough

## Requirements

- Python 3.9 or later
- An Anthropic API key ([console.anthropic.com](https://console.anthropic.com))

## Setup

Clone the repository and install dependencies:

```bash
git clone <your-repo-url>
cd <repo-folder>
pip install -r requirements.txt
```

<<<<<<< HEAD
=======
Create a `.streamlit/secrets.toml` file in the project folder with your API key:

```toml
ANTHROPIC_API_KEY = "your-key-here"
```

>>>>>>> 0ec3714f93e0df1313327e958b3fb8eda2716abf
Run the app:

```bash
streamlit run app.py
```

<<<<<<< HEAD
No API key needs to be configured ahead of time. Each person enters their own when they log in (see below).

## How Accounts Work

There's no separate sign-up page. **The first time you log in with a username, an account is created automatically** using whatever password you type in that same login screen. Every login after that checks your username and password against what was created that first time.

Pick a username and password you'll actually remember. There's no "forgot password" recovery built in, if you lose it, you'd need to start over under a new username, and your old progress would stay under the old one.

Under the hood, your password is never stored as plain text. It's run through a salted one-way hash before being saved, so even someone with direct access to the database file couldn't read passwords back out of it.

## How Your API Key Works

Every login also asks for your own Anthropic API key, and it's required, not optional. This means every question you generate and every answer you submit is billed to your own Anthropic account. Nobody's usage gets mixed together, and nobody's questions run up someone else's bill.

**Your key is never stored anywhere.** It isn't written to the database alongside your username and password, it isn't saved to a file on disk, and it isn't logged anywhere. It exists only in your browser session's temporary memory for as long as you're actively using the app. Closing the tab, restarting the app, or clicking "Switch user" all erase it immediately.

The practical tradeoff: you'll need to paste your key in again each time you log in, since nothing remembers it for you. That's intentional, it's what keeps the key from ever sitting somewhere it could later leak.

If you don't have a key yet, create one at [console.anthropic.com](https://console.anthropic.com) under API Keys.

## Usage
=======
## Usage

Enter a username on the login screen (any name works, it's just used to keep your progress separate, no account or password needed).
>>>>>>> 0ec3714f93e0df1313327e958b3fb8eda2716abf

Pick a course from the sidebar. You can either choose a specific topic or let the app automatically pick whichever topic you're currently weakest on.

Choose a question type, or leave it on "Mixed" for a random mix each time. Generate a question, answer it, and submit for instant grading and an explanation.

<<<<<<< HEAD
Your rating and progress are saved automatically after every question and will still be there the next time you log in with the same username and password.

## Deployment

To deploy on Streamlit Community Cloud: push this repository to GitHub, go to [share.streamlit.io](https://share.streamlit.io), create a new app pointing at this repo with `app.py` as the entry point, and deploy. No secrets need to be configured on the deployment side, since each user supplies their own API key at login rather than the app relying on one shared key.
=======
Your rating and progress are saved automatically after every question and will still be there the next time you log in with the same username.

## Deployment

To deploy on Streamlit Community Cloud: push this repository to GitHub, go to [share.streamlit.io](https://share.streamlit.io), create a new app pointing at this repo with `app.py` as the entry point, and add your `ANTHROPIC_API_KEY` under Advanced Settings > Secrets before deploying.
>>>>>>> 0ec3714f93e0df1313327e958b3fb8eda2716abf
