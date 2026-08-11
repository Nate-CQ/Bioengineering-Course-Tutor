# Course Tutor

A practice question generator, answer checker, and step-by-step explainer for four bioengineering courses: Bioengineering Signals and Systems, Principles of Human Physiology, Biomaterials, and Biological Data Science I (Fundamentals of Biostatistics).

## Features

- Multiple choice, fill-in-the-blank, short answer, and long-form problem questions, generated fresh each time and matched to your current skill level
- Automatic difficulty adjustment based on your performance, with a calibration phase for new topics
- Progress saved across sessions under a username, no password required
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

Create a `.streamlit/secrets.toml` file in the project folder with your API key:

```toml
ANTHROPIC_API_KEY = "your-key-here"
```

Run the app:

```bash
streamlit run app.py
```

## Usage

Enter a username on the login screen (any name works, it's just used to keep your progress separate, no account or password needed).

Pick a course from the sidebar. You can either choose a specific topic or let the app automatically pick whichever topic you're currently weakest on.

Choose a question type, or leave it on "Mixed" for a random mix each time. Generate a question, answer it, and submit for instant grading and an explanation.

Your rating and progress are saved automatically after every question and will still be there the next time you log in with the same username.

## Deployment

To deploy on Streamlit Community Cloud: push this repository to GitHub, go to [share.streamlit.io](https://share.streamlit.io), create a new app pointing at this repo with `app.py` as the entry point, and add your `ANTHROPIC_API_KEY` under Advanced Settings > Secrets before deploying.
