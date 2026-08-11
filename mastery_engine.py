"""
Elo-based mastery tracking engine.

Tracks a per-topic skill rating for the student using an Elo rating system
(the same math used for chess ratings, applied here to topic mastery).
Each topic gets a 10-question calibration phase where ratings move quickly
to find the student's true level, then settles into slower, more stable
updates so mastery doesn't swing wildly from a single lucky or unlucky
answer.

Supports partial credit so short-answer questions (graded by Claude on a
rubric) update ratings the same way multiple-choice and fill-in-the-blank
questions do.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# Reference ratings for each difficulty tier. A question's "opponent rating"
# in the Elo sense. Spaced 200 points apart, matching standard Elo practice
# where a 200-point gap implies roughly a 76% win probability for the
# stronger side.
DIFFICULTY_RATINGS: Dict[str, int] = {
    "easy": 1000,
    "medium": 1200,
    "hard": 1400,
    "expert": 1600,
}

DEFAULT_RATING = 1200
CALIBRATION_QUESTIONS = 10
K_CALIBRATION = 48   # large K while we're still figuring out the student's level
K_STANDARD = 20      # smaller K once the rating has stabilized


@dataclass
class TopicState:
    rating: float = DEFAULT_RATING
    questions_answered: int = 0
    # (difficulty, score, resulting_rating) per answered question, oldest first
    history: List[Tuple[str, float, float]] = field(default_factory=list)

    @property
    def calibrating(self) -> bool:
        return self.questions_answered < CALIBRATION_QUESTIONS

    @property
    def calibration_remaining(self) -> int:
        return max(0, CALIBRATION_QUESTIONS - self.questions_answered)

    @property
    def mastery_label(self) -> str:
        if self.rating < 1100:
            return "Building foundation"
        if self.rating < 1300:
            return "Developing"
        if self.rating < 1500:
            return "Proficient"
        return "Advanced"


class MasteryEngine:
    """Elo rating system with a calibration phase and partial-credit support."""

    def __init__(self, topics: List[str]):
        self.topics: Dict[str, TopicState] = {t: TopicState() for t in topics}

    def get_state(self, topic: str) -> TopicState:
        if topic not in self.topics:
            self.topics[topic] = TopicState()
        return self.topics[topic]

    def load(self, saved: Dict[str, dict]) -> None:
        """Populate topic states from previously saved data, e.g. rows
        loaded from the database on login. Safe to call with a partial
        dict; any topic not present just keeps its default state."""
        for topic, data in saved.items():
            state = self.get_state(topic)
            state.rating = data["rating"]
            state.questions_answered = data["questions_answered"]
            state.history = [tuple(h) for h in data["history"]]

    def recommend_difficulty(self, topic: str) -> str:
        """Pick the difficulty tier whose reference rating is closest to the
        student's current rating on this topic, so new questions land near
        the edge of their ability rather than being too easy or too hard."""
        rating = self.get_state(topic).rating
        return min(DIFFICULTY_RATINGS, key=lambda d: abs(DIFFICULTY_RATINGS[d] - rating))

    def update(self, topic: str, difficulty: str, score: float) -> TopicState:
        """Update a topic's rating after a question is answered.

        score: 1.0 for fully correct, 0.5 for a partially correct short
        answer (per Claude's rubric grading), 0.0 for incorrect.
        """
        state = self.get_state(topic)
        opponent_rating = DIFFICULTY_RATINGS[difficulty]
        expected = 1 / (1 + 10 ** ((opponent_rating - state.rating) / 400))
        k = K_CALIBRATION if state.calibrating else K_STANDARD
        state.rating += k * (score - expected)
        state.rating = max(600, min(2000, state.rating))
        state.questions_answered += 1
        state.history.append((difficulty, score, state.rating))
        return state
