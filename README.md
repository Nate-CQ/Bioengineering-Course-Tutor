# Course Tutor

A practice question generator, answer checker, and step-by-step explainer for
four bioengineering courses: Bioengineering Signals and Systems,
Principles of Human Physiology, Biomaterials, and Biological Data Science I
(Fundamentals of Biostatistics).

## What It Does

Pick a course and a topic (or let the tool pick the topic you're weakest on),
and it writes a fresh multiple-choice, fill-in-the-blank, or short-answer
question at a difficulty matched to your current skill level. Multiple choice
and fill-in-the-blank are graded instantly; short answers are graded by
Claude against a rubric, since free-text responses can't be checked with
exact string matching. A separate explainer tab takes any pasted problem set
question and walks through it step by step, without affecting your ratings.

## How It Was Built

### Mastery Tracking Engine

The core non-LLM component is a from-scratch Elo rating system
(`mastery_engine.py`), the same math used for chess ratings, applied to
topic mastery instead of players. Each subtopic starts at a rating of 1200.
Question difficulty tiers (easy, medium, hard, expert) are anchored to fixed
reference ratings 200 points apart. After each answer, the student's rating
moves toward or away from the question's difficulty rating based on whether
they got it right, using the standard Elo expected-score formula.

The first 10 questions on a topic run with a high K-factor (48) so the
rating converges quickly to the student's true level. After calibration,
the K-factor drops to 20 so a single lucky or unlucky answer doesn't swing
the rating too far. The engine also recommends the next question's
difficulty by picking the tier closest to the student's current rating,
keeping questions near the edge of their ability.

### Partial Credit for Short Answer

Multiple choice and fill-in-the-blank are graded by exact match against the
accepted answer(s). Short answers can't be graded that way, so those are
sent to Claude along with a rubric generated at question-writing time.
Claude returns a score of 1.0, 0.5, or 0.0 plus specific feedback, and that
score feeds into the same Elo update as any other question type.

### Question Taxonomy

Each course is broken into 9-12 granular subtopics (`course_data.py`),
researched from published university syllabi and standard textbook tables
of contents for each subject: Semmlow's *Circuits, Signals, and Systems for
Bioengineers* for signal processing, Ratner et al.'s *Biomaterials Science*
for biomaterials, and standard undergraduate human physiology and
biostatistics course structures. Granular topics keep generated questions
targeted at one specific concept (for example, "sampling and the sampling
theorem" rather than a broad catch-all like "signals"), which is what both
the mastery engine and the question generator use to stay on-syllabus.

### LLM Layer

The Claude API (`claude-sonnet-5`) is called for three things: writing
questions matched to a course, topic, and difficulty; grading short answers
against a rubric; and explaining pasted problem set questions step by step.

## Technical Stack

| Layer | Technology | Purpose |
|---|---|---|
| Mastery engine | Python | Elo rating system with calibration and partial credit |
| LLM layer | Anthropic Python SDK | Question generation, rubric grading, explanations |
| Web app | Streamlit | Course/topic selection, question flow, rating dashboard |
| Deployment | Streamlit Community Cloud | Free hosting with GitHub integration |

## Setup

```bash
pip install -r requirements.txt
```

Set your Anthropic API key as an environment variable, or in
`.streamlit/secrets.toml` for Streamlit Cloud deployment:

```toml
ANTHROPIC_API_KEY = "your-key-here"
```

Run locally:

```bash
streamlit run app.py
```

## Resume Bullet

Built a practice question generator and tutor for four bioengineering
courses (Signals and Systems, Physiology, Biomaterials, Biostatistics),
engineering a from-scratch Elo rating system with a calibrated ramp-up
phase to track topic mastery and adapt question difficulty; integrated the
Claude API to generate course-specific questions, grade short-answer
responses against rubrics with partial credit, and explain problem set
questions step by step; deployed as a Streamlit application.
