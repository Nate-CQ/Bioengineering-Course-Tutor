"""
Course Tutor: a practice question generator, answer checker, and explainer
for four bioengineering courses.

Architecture:
- course_data.py holds the subtopic taxonomy for each course, built from
  the actual syllabus.
- mastery_engine.py is a from-scratch Elo rating system (with a 10-question
  calibration phase per topic) that tracks how well the student knows each
  subtopic and picks the next question's difficulty accordingly.
- claude_client.py calls the Anthropic API to generate questions and to
  grade short-answer responses against a rubric, since those can't be
  checked with exact string matching.
"""

import streamlit as st

import db
from answer_matching import answers_match
from claude_client import generate_question, grade_short_answer, explain_concept
from course_data import COURSES, QUESTION_TYPES
from mastery_engine import MasteryEngine

st.set_page_config(page_title="Course Tutor", page_icon="🧬", layout="wide")


# ---------------------------------------------------------------------------
# Login: username + password (accounts are created automatically on first
# login with a new username), plus a required personal Anthropic API key.
# Each user's own key is used for their questions, so usage bills to their
# own Anthropic account rather than the app owner's.
# ---------------------------------------------------------------------------
if "username" not in st.session_state:
    st.title("🧬 Course Tutor")
    st.write(
        "Log in with a username and password. A new username automatically "
        "creates an account the first time you use it."
    )
    known = db.known_usernames()
    if known:
        st.caption("Existing users: " + ", ".join(known))

    name_input = st.text_input("Username")
    password_input = st.text_input("Password", type="password")
    api_key_input = st.text_input(
        "Your Anthropic API key",
        type="password",
        help="Get one at console.anthropic.com. Questions are generated using "
             "your own key, so usage is billed to your account, not shared. "
             "Your key is used only for this session and is never saved.",
    )

    if st.button("Continue", type="primary"):
        name = name_input.strip()
        if not name or not password_input or not api_key_input.strip():
            st.error("Username, password, and API key are all required.")
        elif db.user_exists(name):
            if db.verify_password(name, password_input):
                st.session_state.username = name
                st.session_state.api_key = api_key_input.strip()
                st.rerun()
            else:
                st.error("Incorrect password for that username.")
        else:
            db.create_user(name, password_input)
            st.session_state.username = name
            st.session_state.api_key = api_key_input.strip()
            st.rerun()
    st.stop()

username = st.session_state.username
api_key = st.session_state.api_key

# ---------------------------------------------------------------------------
# Session state: one MasteryEngine per course, loaded from the database
# once per login rather than reset on every refresh.
# ---------------------------------------------------------------------------
if "engines" not in st.session_state:
    engines = {}
    for key, course_info in COURSES.items():
        engine = MasteryEngine(course_info["topics"])
        engine.load(db.load_ratings(username, key))
        engines[key] = engine
    st.session_state.engines = engines
if "current_question" not in st.session_state:
    st.session_state.current_question = None
if "graded" not in st.session_state:
    st.session_state.graded = None
if "recent_contexts" not in st.session_state:
    st.session_state.recent_contexts = {}  # {course_key: [last few contexts used]}


def reset_question():
    st.session_state.current_question = None
    st.session_state.graded = None


def persist(course_key: str, topic: str, state) -> None:
    """Save one topic's updated state to the database immediately after
    an Elo update, so a refresh never loses progress."""
    db.save_rating(
        username, course_key, topic,
        rating=state.rating,
        questions_answered=state.questions_answered,
        history=[list(h) for h in state.history],
    )


# ---------------------------------------------------------------------------
# Sidebar: course + topic + question type selection
# ---------------------------------------------------------------------------
st.sidebar.title("🧬 Course Tutor")
st.sidebar.caption(f"Logged in as **{username}**")
if st.sidebar.button("Switch user"):
    del st.session_state["username"]
    del st.session_state["api_key"]
    del st.session_state["engines"]
    reset_question()
    st.rerun()

course_key = st.sidebar.selectbox(
    "Course",
    options=list(COURSES.keys()),
    format_func=lambda k: COURSES[k]["name"],
    on_change=reset_question,
)
course = COURSES[course_key]
engine = st.session_state.engines[course_key]

st.sidebar.caption(course["description"])

topic_mode = st.sidebar.radio(
    "Topic selection", ["Auto (weakest topic first)", "Choose a topic"], on_change=reset_question
)
if topic_mode == "Choose a topic":
    topic = st.sidebar.selectbox("Topic", course["topics"], on_change=reset_question)
else:
    # While a question is active (including right after grading, before
    # "Next question" is clicked), stay locked on that question's topic so
    # the rating shown matches the question you just answered. Only
    # recompute the weakest topic once you move on to a new question.
    if st.session_state.current_question is not None:
        topic = st.session_state.current_question["topic"]
    else:
        topic = min(
            course["topics"],
            key=lambda t: (not engine.get_state(t).calibrating, engine.get_state(t).rating),
        )
    st.sidebar.write(f"Next up: **{topic}**")

available_types = list(QUESTION_TYPES.values())
if not course["quantitative"]:
    available_types = [t for t in available_types if t != "Long-Form Problem"]

question_type_choice = st.sidebar.radio(
    "Question type",
    ["Mixed"] + available_types,
    on_change=reset_question,
)

st.sidebar.divider()
st.sidebar.subheader("Your ratings in this course")
for t in course["topics"]:
    s = engine.get_state(t)
    label = f"{t}"
    if s.calibrating:
        label += f" (calibrating, {s.calibration_remaining} left)"
    st.sidebar.progress(min(1.0, max(0.0, (s.rating - 600) / 1400)), text=f"{label}: {int(s.rating)} · {s.mastery_label}")

# ---------------------------------------------------------------------------
# Main panel
# ---------------------------------------------------------------------------
st.title(course["name"])

state = engine.get_state(topic)
col1, col2, col3 = st.columns(3)
col1.metric("Current topic", topic)
col2.metric("Rating", int(state.rating), delta=state.mastery_label)
col3.metric("Questions answered", state.questions_answered)

if state.calibrating:
    st.info(
        f"Calibration phase: {state.calibration_remaining} question(s) left on "
        f"this topic. Ratings move faster right now to find your true level."
    )

st.divider()

# ---------------------------------------------------------------------------
# Generate a question
# ---------------------------------------------------------------------------
if st.session_state.current_question is None:
    if st.button("Generate question", type="primary"):
        difficulty = engine.recommend_difficulty(topic)
        if question_type_choice == "Mixed":
            import random
            possible_types = list(QUESTION_TYPES.keys())
            if not course["quantitative"]:
                possible_types.remove("problem")
            q_type = random.choice(possible_types)
        else:
            q_type = [k for k, v in QUESTION_TYPES.items() if v == question_type_choice][0]

        # Pick a context that hasn't been used in the last 3 questions for
        # this course, so generated questions don't all lean on the same
        # go-to example.
        context_hint = None
        contexts = course.get("example_contexts")
        if contexts:
            import random
            recent = st.session_state.recent_contexts.get(course_key, [])
            available = [c for c in contexts if c not in recent] or contexts
            context_hint = random.choice(available)
            recent = (recent + [context_hint])[-3:]
            st.session_state.recent_contexts[course_key] = recent

        with st.spinner("Writing your question..."):
            try:
                recent_questions = db.get_recent_questions(username, course_key, topic, limit=10)
                q = generate_question(course["name"], course["description"], topic, difficulty,
                                       q_type, context_hint, recent_questions, api_key)
            except RuntimeError as e:
                st.error(f"Couldn't generate a question: {e}")
                st.stop()
        db.save_question(username, course_key, topic, q["question"])
        st.session_state.current_question = q
        st.session_state.graded = None
        st.rerun()

# ---------------------------------------------------------------------------
# Show question + collect answer
# ---------------------------------------------------------------------------
q = st.session_state.current_question
if q is not None and st.session_state.graded is None:
    st.subheader(f"{QUESTION_TYPES[q['type']]} · {q['difficulty'].title()}")
    st.write(q["question"])

    if q["type"] == "multiple_choice":
        choice = st.radio("Choose an answer", q["options"], key="mc_choice")
        if st.button("Submit answer"):
            score = 1.0 if choice == q["correct_answer"] else 0.0
            st.session_state.graded = {
                "score": score,
                "feedback": q["explanation"],
                "correct_answer": q["correct_answer"],
                "student_answer": choice,
            }
            engine.update(topic, q["difficulty"], score)
            persist(course_key, topic, engine.get_state(topic))
            st.rerun()

    elif q["type"] == "fill_in_blank":
        answer = st.text_input("Your answer")
        if st.button("Submit answer") and answer.strip():
            accepted = [q["correct_answer"]] + q.get("accepted_answers", [])
            score = 1.0 if answers_match(answer, accepted) else 0.0
            st.session_state.graded = {
                "score": score,
                "feedback": q["explanation"],
                "correct_answer": q["correct_answer"],
                "student_answer": answer,
            }
            engine.update(topic, q["difficulty"], score)
            persist(course_key, topic, engine.get_state(topic))
            st.rerun()

    elif q["type"] in ("short_answer", "problem"):
        placeholder = (
            "Show your full work, including any equations or steps."
            if q["type"] == "problem"
            else None
        )
        answer = st.text_area("Your answer", height=250 if q["type"] == "problem" else 150,
                               placeholder=placeholder)
        if st.button("Submit answer") and answer.strip():
            with st.spinner("Grading against the rubric..."):
                try:
                    result = grade_short_answer(q["question"], q["rubric"], answer, api_key)
                except RuntimeError as e:
                    st.error(f"Couldn't grade that answer: {e}")
                    st.stop()
            st.session_state.graded = {
                "score": result["score"],
                "feedback": result["feedback"],
                "model_answer": q["explanation"],
                "student_answer": answer,
            }
            engine.update(topic, q["difficulty"], result["score"])
            persist(course_key, topic, engine.get_state(topic))
            st.rerun()

# ---------------------------------------------------------------------------
# Show grading result
# ---------------------------------------------------------------------------
if st.session_state.graded is not None:
    g = st.session_state.graded
    if g["score"] == 1.0:
        st.success("Correct")
    elif g["score"] == 0.5:
        st.warning("Partially correct")
    else:
        st.error("Incorrect")

    st.write(g["feedback"])
    if "model_answer" in g:
        with st.expander("Model answer"):
            st.write(g["model_answer"])
    elif "correct_answer" in g:
        st.caption(f"Correct answer: {g['correct_answer']}")

    new_state = engine.get_state(topic)
    st.caption(f"Rating updated to {int(new_state.rating)} ({new_state.mastery_label})")

    if st.button("Next question"):
        reset_question()
        st.rerun()

st.divider()

# ---------------------------------------------------------------------------
# Standalone explainer (paste a problem set question, no grading/rating impact)
# ---------------------------------------------------------------------------
with st.expander("Explain a concept or problem set question"):
    st.caption(
        "Paste a question from your notes or problem set and get a step-by-step "
        "explanation. This does not affect your ratings above."
    )
    free_question = st.text_area("Paste your question here", key="explainer_input")
    if st.button("Explain"):
        if free_question.strip():
            with st.spinner("Working through it..."):
                explanation = explain_concept(course["name"], free_question, api_key)
            st.write(explanation)
