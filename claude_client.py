"""
Anthropic API layer. Two jobs:

1. generate_question - writes a course-appropriate question at a target
   difficulty (multiple choice, fill-in-the-blank, or short answer).
2. grade_short_answer - grades a free-text answer against a rubric, since
   short answers can't be checked with exact string matching the way
   multiple choice and fill-in-the-blank can.

Both call the Anthropic API and expect JSON-only responses, which are
parsed defensively in case the model wraps the JSON in prose or code
fences.
"""

import json
import os
import re

import anthropic

MODEL = "claude-sonnet-5"

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def _extract_json(text: str) -> dict:
    """Pull a JSON object out of a model response, tolerating stray
    code fences or a short preamble."""
    text = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    else:
        brace_match = re.search(r"\{.*\}", text, re.DOTALL)
        if brace_match:
            text = brace_match.group(0)
    return json.loads(text)


def generate_question(course_name: str, course_description: str, topic: str,
                       difficulty: str, question_type: str) -> dict:
    """Generate one question for a given course, topic, difficulty, and
    question type. Returns a dict shaped for the requested type."""

    type_instructions = {
        "multiple_choice": (
            'Return JSON with keys: "question" (string), "options" (array of '
            '4 strings), "correct_answer" (string, must exactly match one of '
            'the options), "explanation" (string, a full worked explanation '
            'of why the correct answer is right and the others are wrong).'
        ),
        "fill_in_blank": (
            'Return JSON with keys: "question" (string, containing a blank '
            'shown as ____), "correct_answer" (string, the primary accepted '
            'answer), "accepted_answers" (array of strings, alternate phrasings '
            'or equivalent numeric forms that should also be marked correct), '
            '"explanation" (string, a full worked explanation of the answer).'
        ),
        "short_answer": (
            'Return JSON with keys: "question" (string, requiring a few '
            'sentences or a short derivation to answer well), "rubric" '
            '(string, 3-5 specific criteria a grader should check for), '
            '"explanation" (string, a full model answer).'
        ),
    }

    system = (
        f"You write exam-quality practice questions for the undergraduate "
        f"bioengineering course '{course_name}'. Course scope: {course_description}\n\n"
        f"Write one question on the subtopic '{topic}' at '{difficulty}' "
        f"difficulty. 'Easy' means a direct definition or single-step "
        f"application. 'Medium' means applying a concept to a new scenario. "
        f"'Hard' means multi-step reasoning or combining two concepts. "
        f"'Expert' means a subtle edge case or a problem requiring real "
        f"derivation.\n\n"
        f"{type_instructions[question_type]}\n\n"
        f"Respond with ONLY the JSON object. No preamble, no code fences, "
        f"no commentary."
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=1200,
        system=system,
        messages=[{"role": "user", "content": "Generate the question now."}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    data = _extract_json(text)
    data["type"] = question_type
    data["topic"] = topic
    data["difficulty"] = difficulty
    return data


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
    """Grade a short-answer response against a rubric.

    Returns {"score": 1.0 | 0.5 | 0.0, "feedback": str}
    1.0 = fully meets the rubric, 0.5 = partially correct or incomplete,
    0.0 = incorrect or missing the key ideas.
    """
    system = (
        "You are grading a bioengineering student's short-answer response. "
        "Grade strictly against the rubric provided, not against how "
        "well-written the answer is. Return JSON with keys: "
        '"score" (number, must be exactly 1.0, 0.5, or 0.0) and '
        '"feedback" (string, 2-4 sentences: what was right, what was '
        "missing or wrong, referencing the rubric). "
        "Respond with ONLY the JSON object."
    )
    user = (
        f"Question:\n{question}\n\nRubric:\n{rubric}\n\n"
        f"Student's answer:\n{student_answer}"
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=500,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(block.text for block in response.content if block.type == "text")
    return _extract_json(text)
