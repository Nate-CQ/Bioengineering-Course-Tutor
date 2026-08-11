"""
Anthropic API layer. Two jobs:

1. generate_question - writes a course-appropriate question at a target
   difficulty (multiple choice, fill-in-the-blank, short answer, or a
   long-form problem).
2. grade_short_answer - grades a free-text answer against a rubric, since
   short answers can't be checked with exact string matching the way
   multiple choice and fill-in-the-blank can.

Both use Anthropic's structured tool calling (forcing a specific tool
with a JSON schema) rather than asking Claude to hand-write JSON as
plain text. Freeform "please respond with only JSON" prompting breaks
whenever a generated explanation contains an unescaped quote or a stray
code fence, which happens often in technical writing full of units,
abbreviations, and quoted terms. Tool calling has the API itself
validate the output against the schema, so there's no text to parse and
no way for a stray character to produce invalid JSON.
"""

import os
import time

import anthropic

MODEL = "claude-sonnet-5"


def _get_api_key():
    """Read the API key from Streamlit secrets when running as a Streamlit
    app, falling back to a plain environment variable otherwise (useful for
    standalone scripts or non-Streamlit deployments)."""
    try:
        import streamlit as st
        if "ANTHROPIC_API_KEY" in st.secrets:
            return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        pass
    return os.environ.get("ANTHROPIC_API_KEY")


client = anthropic.Anthropic(api_key=_get_api_key())


# ---------------------------------------------------------------------------
# Tool schemas, one per question type, plus one for grading.
# ---------------------------------------------------------------------------
_QUESTION_TOOLS = {
    "multiple_choice": {
        "name": "submit_question",
        "description": "Submit the generated multiple choice question.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 4,
                    "maxItems": 4,
                    "description": "Exactly 4 answer choices.",
                },
                "correct_answer": {
                    "type": "string",
                    "description": "Must exactly match one of the strings in options.",
                },
                "explanation": {
                    "type": "string",
                    "description": "Full worked explanation of why the correct answer is right and the others are wrong.",
                },
            },
            "required": ["question", "options", "correct_answer", "explanation"],
        },
    },
    "fill_in_blank": {
        "name": "submit_question",
        "description": "Submit the generated fill-in-the-blank question.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Contains a blank shown as ____.",
                },
                "correct_answer": {"type": "string", "description": "The primary accepted answer."},
                "accepted_answers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Alternate phrasings or equivalent forms that should also be marked correct.",
                },
                "explanation": {"type": "string", "description": "Full worked explanation of the answer."},
            },
            "required": ["question", "correct_answer", "accepted_answers", "explanation"],
        },
    },
    "short_answer": {
        "name": "submit_question",
        "description": "Submit the generated short-answer question.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Requires a few sentences to answer well, testing conceptual understanding rather than calculation.",
                },
                "rubric": {"type": "string", "description": "3-5 specific criteria a grader should check for."},
                "explanation": {"type": "string", "description": "A full model answer."},
            },
            "required": ["question", "rubric", "explanation"],
        },
    },
    "problem": {
        "name": "submit_question",
        "description": "Submit the generated long-form, multi-step problem.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The full problem statement including any given values. Must require setting up an equation or model and carrying out at least 2-3 calculation or derivation steps to reach a specific final answer.",
                },
                "rubric": {
                    "type": "string",
                    "description": "3-5 specific criteria covering both correct setup/method and correct final answer, with partial credit for correct method but a wrong final number.",
                },
                "explanation": {
                    "type": "string",
                    "description": "The complete worked solution showing every step, not just the final answer.",
                },
            },
            "required": ["question", "rubric", "explanation"],
        },
    },
}

_GRADE_TOOL = {
    "name": "submit_grade",
    "description": "Submit the grade for a student's response.",
    "input_schema": {
        "type": "object",
        "properties": {
            "score": {
                "type": "number",
                "enum": [0.0, 0.5, 1.0],
                "description": "1.0 = fully meets the rubric, 0.5 = partially correct or incomplete, 0.0 = incorrect or missing the key ideas.",
            },
            "feedback": {
                "type": "string",
                "description": "2-4 sentences: what was right, what was missing or wrong, referencing the rubric.",
            },
        },
        "required": ["score", "feedback"],
    },
}


def _call_with_tool(system: str, user_message: str, tool: dict, max_tokens: int) -> dict:
    """Call the API forcing use of the given tool, and return its parsed
    input dict directly. The API validates the tool call against the
    schema server-side, so there is no freeform text to parse here."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        tools=[tool],
        tool_choice={"type": "tool", "name": tool["name"]},
        messages=[{"role": "user", "content": user_message}],
    )
    for block in response.content:
        if block.type == "tool_use":
            return dict(block.input)
    raise RuntimeError(f"No tool call in response (stop_reason={response.stop_reason})")


def generate_question(course_name: str, course_description: str, topic: str,
                       difficulty: str, question_type: str, context_hint: str = None,
                       recent_questions: list = None) -> dict:
    """Generate one question for a given course, topic, difficulty, and
    question type. Returns a dict shaped for the requested type.

    context_hint, if provided, steers which real-world example or
    scenario the question draws from, so repeated generations don't all
    default to the same go-to example (e.g. hip replacements for every
    biomaterials question).

    recent_questions, if provided, is a list of question texts already
    asked on this topic, which Claude is instructed not to repeat or
    trivially reword."""

    system = (
        f"You write exam-quality practice questions for the undergraduate "
        f"bioengineering course '{course_name}'. Course scope: {course_description}\n\n"
        f"Write one question on the subtopic '{topic}' at '{difficulty}' "
        f"difficulty. 'Easy' means a direct definition or single-step "
        f"application. 'Medium' means applying a concept to a new scenario. "
        f"'Hard' means multi-step reasoning or combining two concepts. "
        f"'Expert' means a subtle edge case or a problem requiring real "
        f"derivation.\n\n"
        f"Avoid defaulting to the single most stereotypical textbook "
        f"example for this topic. Vary the real-world scenario, "
        f"application, or patient/device context across questions.\n"
        + (f"For this question specifically, if a real-world scenario is "
           f"relevant, draw from: {context_hint}.\n" if context_hint else "")
        + (f"\nDo not repeat, closely rephrase, or trivially reword any of "
           f"these questions already asked on this exact topic. Write "
           f"something that tests a genuinely different angle, sub-concept, "
           f"or scenario:\n"
           + "\n".join(f"- {q}" for q in recent_questions) + "\n"
           if recent_questions else "")
    )

    max_tokens_by_type = {
        "multiple_choice": 1000,
        "fill_in_blank": 900,
        "short_answer": 1500,
        "problem": 2200,
    }
    tool = _QUESTION_TOOLS[question_type]

    last_error = None
    for attempt in range(3):
        token_budget = max_tokens_by_type[question_type] + (attempt * 800)
        try:
            data = _call_with_tool(system, "Generate the question now.", tool, token_budget)
            data["type"] = question_type
            data["topic"] = topic
            data["difficulty"] = difficulty
            return data
        except Exception as e:
            last_error = e
            time.sleep(1)

    raise RuntimeError(
        f"Claude couldn't produce a valid question after 3 attempts. "
        f"This is usually a transient API hiccup, try generating again. "
        f"(last error: {last_error})"
    )


def explain_concept(course_name: str, prompt_text: str) -> str:
    """Explain a pasted concept or problem set question step by step. Used
    by the standalone explainer, which does not touch the mastery engine."""
    system = (
        f"You are a patient, precise tutor for the undergraduate bioengineering "
        f"course '{course_name}'. The student will paste in a concept or a problem "
        f"set question. Explain it step by step in plain language, showing "
        f"any relevant equations and working through the logic a student "
        f"could follow and reuse on similar problems. Do not just state the "
        f"final answer without the reasoning."
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=1200,
        system=system,
        messages=[{"role": "user", "content": prompt_text}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def grade_short_answer(question: str, rubric: str, student_answer: str) -> dict:
    """Grade a short-answer or long-form-problem response against a rubric.

    Returns {"score": 1.0 | 0.5 | 0.0, "feedback": str}
    """
    system = (
        "You are grading a bioengineering student's response. Grade "
        "strictly against the rubric provided, not against how "
        "well-written the answer is."
    )
    user = (
        f"Question:\n{question}\n\nRubric:\n{rubric}\n\n"
        f"Student's answer:\n{student_answer}"
    )
    last_error = None
    for attempt in range(2):
        try:
            return _call_with_tool(system, user, _GRADE_TOOL, 500)
        except Exception as e:
            last_error = e
            time.sleep(1)
    raise RuntimeError(f"Claude couldn't grade this response. Try submitting again. (last error: {last_error})")
