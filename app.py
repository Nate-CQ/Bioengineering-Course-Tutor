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

from claude_client import generate_question, grade_short_answer, explain_concept
from course_data import COURSES, QUESTION_TYPES
from mastery_engine import MasteryEngine

st.set_page_config(page_title="Course Tutor", page_icon="🧬", layout="wide")


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "engines" not in st.session_state:
    st.session_state.engines = {
        key: MasteryEngine(course["topics"]) for key, course in COURSES.items()
    }
if "current_question" not in st.session_state:
    st.session_state.current_question = None
if "graded" not in st.session_state:
    st.session_state.graded = None


def reset_question():
    st.session_state.current_question = None
    st.session_state.graded = None


# ---------------------------------------------------------------------------
# Sidebar: course + topic + question type selection
# ---------------------------------------------------------------------------
st.sidebar.title("🧬 Course Tutor")
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
    # weakest topic = lowest rating, prioritizing topics still in calibration
    topic = min(
        course["topics"],
        key=lambda t: (not engine.get_state(t).calibrating, engine.get_state(t).rating),
    )
    st.sidebar.write(f"Next up: **{topic}**")

question_type_choice = st.sidebar.radio(
    "Question type",
    ["Mixed"] + list(QUESTION_TYPES.values()),
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
            q_type = random.choice(list(QUESTION_TYPES.keys()))
        else:
            q_type = [k for k, v in QUESTION_TYPES.items() if v == question_type_choice][0]

        with st.spinner("Writing your question..."):
            q = generate_question(course["name"], course["description"], topic, difficulty, q_type)
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
            st.rerun()

    elif q["type"] == "fill_in_blank":
        answer = st.text_input("Your answer")
        if st.button("Submit answer") and answer.strip():
            accepted = [q["correct_answer"]] + q.get("accepted_answers", [])
            normalized = [a.strip().lower() for a in accepted]
            score = 1.0 if answer.strip().lower() in normalized else 0.0
            st.session_state.graded = {
                "score": score,
                "feedback": q["explanation"],
                "correct_answer": q["correct_answer"],
                "student_answer": answer,
            }
            engine.update(topic, q["difficulty"], score)
            st.rerun()

    elif q["type"] == "short_answer":
        answer = st.text_area("Your answer", height=150)
        if st.button("Submit answer") and answer.strip():
            with st.spinner("Grading against the rubric..."):
                result = grade_short_answer(q["question"], q["rubric"], answer)
            st.session_state.graded = {
                "score": result["score"],
                "feedback": result["feedback"],
                "model_answer": q["explanation"],
                "student_answer": answer,
            }
            engine.update(topic, q["difficulty"], result["score"])
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
                explanation = explain_concept(course["name"], free_question)
            st.write(explanation)
