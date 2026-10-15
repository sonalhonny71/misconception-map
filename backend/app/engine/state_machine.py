"""
Diagnostic Engine - Core State Machine and Evidence Combination

This module implements the server-side state machine for the learning journey:
START → DIAGNOSTIC → (FOLLOWUP | CHECK_UNDERSTANDING) → COMBINE_EVIDENCE → 
  EXPLAIN_SUPPORTED_HYPOTHESIS | REPORT_UNCERTAINTY → TARGETED_PRACTICE → 
  FRESH_RETEST → UPDATE_PROGRESS → RESULTS

The engine is pure Python with no web or DB dependencies.
"""

import json
import random
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum
from uuid import UUID, uuid4

from app.engine.misconceptions import (
    MISCONCEPTIONS,
    EVIDENCE_PARAMS,
    hypothesis_status,
    confidence_wording,
    get_misconception,
)


class Phase(str, Enum):
    DIAGNOSTIC = "diagnostic"
    FOLLOWUP = "followup"
    CHECK_UNDERSTANDING = "check_understanding"
    PRACTICE = "practice"
    RETEST = "retest"
    RESULTS = "results"
    COMPLETED = "completed"


@dataclass
class ServedQuestion:
    """A question as served to the learner (with shuffled options)."""
    item_id: str  # logical item ID
    served_item_id: UUID  # DB ID of the ServedItem record
    prompt: str  # LaTeX
    options: List[Dict[str, Any]]  # [{"id": "opt-1", "text": "..."}]
    option_order: List[str]  # option IDs in display order
    correct_option_id: str
    explanation: str  # LaTeX
    misconception_id: Optional[str] = None
    discriminates: List[str] = field(default_factory=list)
    step_index: int = 0
    total_steps: int = 0
    phase: Phase = Phase.DIAGNOSTIC
    skill: str = ""


@dataclass
class AnswerResult:
    is_correct: bool
    chosen_option_id: Optional[str]
    misconception_id: Optional[str]
    explanation: str
    step_note: Optional[str]
    xp_awarded: int = 0


@dataclass
class EngineState:
    """In-memory representation of the journey state (mirrors DB)."""
    session_id: UUID
    learner_id: UUID
    level: int
    phase: Phase
    step_index: int
    current_skill: str
    served_items: List[ServedQuestion] = field(default_factory=list)
    responses: List[Dict[str, Any]] = field(default_factory=list)
    hypotheses: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # misconception_id -> {score, has_followup}
    xp_total: int = 0


class DiagnosticEngine:
    """
    Pure Python diagnostic engine. No DB, no web framework.
    All methods are deterministic and testable.
    """

    def __init__(self, content_loader):
        self.content = content_loader

    def start_session(self, learner_id: UUID, level: int) -> EngineState:
        """Initialize a new diagnostic session for a level."""
        diagnostic_items = self.content.get_diagnostic_items(level)
        if not diagnostic_items:
            raise ValueError(f"No diagnostic items for level {level}")

        session_id = uuid4()
        skill = self.content.get_primary_skill(level)

        # Serve first diagnostic question
        first_item = diagnostic_items[0]
        served = self._serve_item(first_item, 0, len(diagnostic_items), Phase.DIAGNOSTIC, skill)

        return EngineState(
            session_id=session_id,
            learner_id=learner_id,
            level=level,
            phase=Phase.DIAGNOSTIC,
            step_index=0,
            current_skill=skill,
            served_items=[served],
        )

    def _serve_item(self, item: Dict, step_index: int, total_steps: int, phase: Phase, skill: str) -> ServedQuestion:
        """Shuffle options and create a served question."""
        # Handle both JSON string (from DB) and Python list (from YAML loader)
        options = item["options"]
        if isinstance(options, str):
            options = json.loads(options)
        option_ids = [opt["id"] for opt in options]
        random.shuffle(option_ids)

        # Reorder options to match shuffled order
        opt_map = {opt["id"]: opt for opt in options}
        shuffled_options = [{"id": oid, "text": opt_map[oid]["text"]} for oid in option_ids]

        served_id = uuid4()
        return ServedQuestion(
            item_id=item["item_id"],
            served_item_id=served_id,
            prompt=item["prompt"],
            options=shuffled_options,
            option_order=option_ids,
            correct_option_id=item["correct_option_id"],
            explanation=item["explanation"],
            misconception_id=self._get_distractor_misconception(item, option_ids),
            discriminates=json.loads(item["discriminates"]) if isinstance(item.get("discriminates"), str) else (item.get("discriminates") or []),
            step_index=step_index,
            total_steps=total_steps,
            phase=phase,
            skill=skill,
        )

    def _get_distractor_misconception(self, item: Dict, chosen_option_id: str) -> Optional[str]:
        """Get the misconception ID for a chosen option, if any."""
        options = item["options"]
        if isinstance(options, str):
            options = json.loads(options)
        for opt in options:
            if opt["id"] == chosen_option_id:
                return opt.get("misconception_id")
        return None

    def submit_answer(self, state: EngineState, served_item_id: UUID, chosen_option_id: Optional[str]) -> Tuple[AnswerResult, EngineState]:
        """
        Grade an answer and return feedback + updated state.
        Does not mutate state directly; returns new state.
        """
        # Find the served question
        served = next((s for s in state.served_items if s.served_item_id == served_item_id), None)
        if not served:
            raise ValueError("Served item not found")

        # Check if already answered (idempotency)
        existing = next((r for r in state.responses if r["served_item_id"] == str(served_item_id)), None)
        if existing:
            # Return cached result
            return AnswerResult(**existing["result"]), state

        is_correct = False
        misconception_id = None
        step_note = None

        if chosen_option_id is None:
            # "I'm not sure" - neutral evidence
            is_correct = False
            misconception_id = None
            step_note = None
        elif chosen_option_id == served.correct_option_id:
            is_correct = True
            misconception_id = None
            step_note = None
        else:
            is_correct = False
            misconception_id = self._get_distractor_misconception_from_served(served, chosen_option_id)
            if misconception_id:
                misc = get_misconception(misconception_id)
                step_note = misc["step"]

        # Build feedback
        explanation = served.explanation
        result = AnswerResult(
            is_correct=is_correct,
            chosen_option_id=chosen_option_id,
            misconception_id=misconception_id,
            explanation=explanation,
            step_note=step_note,
            xp_awarded=0,
        )

        # Record response
        response_record = {
            "served_item_id": str(served_item_id),
            "item_id": served.item_id,
            "chosen_option_id": chosen_option_id,
            "is_correct": is_correct,
            "misconception_id": misconception_id,
            "kind": served.phase.value,
            "phase": served.phase.value,
            "skill": served.skill,
            "result": result.__dict__,
        }

        # Update hypotheses based on this response
        new_hypotheses = self._update_hypotheses(state.hypotheses, response_record, served)

        # Determine next phase
        next_phase = self._determine_next_phase(state, response_record)

        # Create new state (immutable update)
        new_state = EngineState(
            session_id=state.session_id,
            learner_id=state.learner_id,
            level=state.level,
            phase=next_phase,
            step_index=state.step_index + 1 if next_phase == state.phase else 0,
            current_skill=state.current_skill,
            served_items=state.served_items.copy(),
            responses=state.responses + [response_record],
            hypotheses=new_hypotheses,
            xp_total=state.xp_total,
        )

        return result, new_state

    def _get_distractor_misconception_from_served(self, served: ServedQuestion, chosen_option_id: str) -> Optional[str]:
        """Find misconception ID for a chosen option from the served question's option order."""
        # We need to map back to the original item to get misconception_id
        # For now, we'll look it up from content - in practice this comes from the item
        item = self.content.get_item_by_id(served.item_id)
        if item:
            return self._get_distractor_misconception(item, chosen_option_id)
        return None

    def _update_hypotheses(self, hypotheses: Dict, response: Dict, served: ServedQuestion) -> Dict:
        """Update evidence scores based on a response."""
        new_hypotheses = {k: v.copy() for k, v in hypotheses.items()}
        params = EVIDENCE_PARAMS
        kind = response["kind"]
        misconception_id = response["misconception_id"]
        is_correct = response["is_correct"]

        if kind == "diagnostic" and misconception_id:
            # Diagnostic distractor matching hypothesis H: +1 (stored as +2)
            self._adjust_score(new_hypotheses, misconception_id, params["diagnostic_match"])
            # Other hypotheses get nothing from this response

        elif kind == "followup":
            # Follow-up discriminates between hypotheses
            discriminates = served.discriminates
            if misconception_id and misconception_id in discriminates:
                # Follow-up consistent with H: +2 (stored as +4)
                self._adjust_score(new_hypotheses, misconception_id, params["followup_consistent"])
                new_hypotheses[misconception_id]["has_followup"] = True
            elif is_correct and discriminates:
                # Follow-up correct → contradicts the discriminated hypotheses
                for hyp_id in discriminates:
                    if hyp_id in new_hypotheses:
                        self._adjust_score(new_hypotheses, hyp_id, params["followup_contradicts"])
            # "unsure" gives 0 to all

        elif kind in ("practice", "retest") and misconception_id:
            # Practice/retest errors: +0.5 (stored as +1)
            self._adjust_score(new_hypotheses, misconception_id, params["practice_error"])

        # Recalculate status for all hypotheses
        for hyp_id, hyp_data in new_hypotheses.items():
            runner_up = max([h["score"] for h in new_hypotheses.values() if h != hyp_data], default=0)
            hyp_data["status"] = hypothesis_status(
                hyp_data["score"],
                runner_up,
                hyp_data.get("has_followup", False)
            )

        return new_hypotheses

    def _adjust_score(self, hypotheses: Dict, misconception_id: str, delta: int):
        if misconception_id not in hypotheses:
            hypotheses[misconception_id] = {"score": 0, "has_followup": False, "status": "insufficient"}
        hypotheses[misconception_id]["score"] += delta

    def _determine_next_phase(self, state: EngineState, response: Dict) -> Phase:
        """Determine the next phase based on current phase and response."""
        current = state.phase

        if current == Phase.DIAGNOSTIC:
            if state.step_index + 1 < state.served_items[-1].total_steps:
                return Phase.DIAGNOSTIC  # More diagnostic questions
            # Diagnostic complete - check for potential misconceptions
            if self._has_potential_misconception(state):
                return Phase.FOLLOWUP
            else:
                return Phase.CHECK_UNDERSTANDING

        elif current == Phase.FOLLOWUP:
            if state.step_index + 1 < state.served_items[-1].total_steps:
                return Phase.FOLLOWUP
            return Phase.PRACTICE  # After follow-up, go to practice

        elif current == Phase.CHECK_UNDERSTANDING:
            if state.step_index + 1 < state.served_items[-1].total_steps:
                return Phase.CHECK_UNDERSTANDING
            return Phase.PRACTICE

        elif current == Phase.PRACTICE:
            if state.step_index + 1 < 3:  # 3 practice questions
                return Phase.PRACTICE
            return Phase.RETEST

        elif current == Phase.RETEST:
            if state.step_index + 1 < 3:  # 3 retest questions
                return Phase.RETEST
            return Phase.RESULTS

        elif current == Phase.RESULTS:
            return Phase.COMPLETED

        return Phase.COMPLETED

    def _has_potential_misconception(self, state: EngineState) -> bool:
        """Check if diagnostic responses suggest any misconception."""
        for r in state.responses:
            if r["kind"] == "diagnostic" and r["misconception_id"] and r["misconception_id"] != "ARITHMETIC_SLIP":
                return True
        return False

    def get_next_question(self, state: EngineState) -> Optional[ServedQuestion]:
        """Get the next question for the current phase (does not update state)."""
        # This method is for inspection only. The API layer should call advance_to_next_question.
        if state.phase == Phase.DIAGNOSTIC:
            items = self.content.get_diagnostic_items(state.level)
            if state.step_index < len(items):
                item = items[state.step_index]
                return self._serve_item(item, state.step_index, len(items), Phase.DIAGNOSTIC, state.current_skill)

        elif state.phase == Phase.FOLLOWUP:
            top_hyp = self._get_top_hypothesis(state.hypotheses)
            if top_hyp:
                followup_items = self.content.get_followup_items(state.level, top_hyp)
                if state.step_index < len(followup_items):
                    item = followup_items[state.step_index]
                    return self._serve_item(item, state.step_index, len(followup_items), Phase.FOLLOWUP, state.current_skill)

        elif state.phase == Phase.CHECK_UNDERSTANDING:
            check_items = self.content.get_check_items(state.level)
            if state.step_index < len(check_items):
                item = check_items[state.step_index]
                return self._serve_item(item, state.step_index, len(check_items), Phase.CHECK_UNDERSTANDING, state.current_skill)

        elif state.phase == Phase.PRACTICE:
            top_hyp = self._get_top_hypothesis(state.hypotheses)
            # Only items from *other* phases count as "seen", so the list of practice
            # questions stays the same while the learner moves through the phase.
            earlier_responses = [r for r in state.responses if r["kind"] != "practice"]
            practice_items = self.content.get_practice_items(state.level, top_hyp, earlier_responses)
            if state.step_index < len(practice_items):
                item = practice_items[state.step_index]
                return self._serve_item(item, state.step_index, min(3, len(practice_items)), Phase.PRACTICE, state.current_skill)

        elif state.phase == Phase.RETEST:
            seen_item_ids = {r["item_id"] for r in state.responses if r["kind"] != "retest"}
            retest_items = self.content.get_retest_items(state.level, state.current_skill, seen_item_ids)
            if state.step_index < len(retest_items):
                item = retest_items[state.step_index]
                return self._serve_item(item, state.step_index, min(3, len(retest_items)), Phase.RETEST, state.current_skill)

        return None

    def advance_to_next_question(self, state: EngineState) -> Tuple[Optional[ServedQuestion], EngineState]:
        """Get the next question and return updated state with the question added to served_items."""
        question = self.get_next_question(state)
        if not question:
            return None, state
        
        new_state = EngineState(
            session_id=state.session_id,
            learner_id=state.learner_id,
            level=state.level,
            phase=state.phase,
            step_index=state.step_index,
            current_skill=state.current_skill,
            served_items=state.served_items + [question],
            responses=state.responses,
            hypotheses=state.hypotheses,
            xp_total=state.xp_total,
        )
        return question, new_state

    def _get_top_hypothesis(self, hypotheses: Dict) -> Optional[str]:
        """Get the misconception ID with highest evidence score."""
        if not hypotheses:
            return None
        # Filter to those with score > 0
        candidates = {k: v for k, v in hypotheses.items() if v["score"] > 0}
        if not candidates:
            return None
        return max(candidates.items(), key=lambda x: x[1]["score"])[0]

    def get_explanation(self, state: EngineState) -> Dict[str, Any]:
        """Generate the final explanation with evidence trail."""
        top_hyp_id = self._get_top_hypothesis(state.hypotheses)

        if not top_hyp_id or top_hyp_id not in state.hypotheses:
            return {
                "hypothesis_id": None,
                "hypothesis_label": None,
                "status": "insufficient",
                "wording": "We don't have enough evidence yet to say why.",
                "step_explanation": None,
                "why_it_matters": None,
                "evidence_trail": self._build_evidence_trail(state),
            }

        hyp = state.hypotheses[top_hyp_id]
        misc = get_misconception(top_hyp_id)
        runner_up_score = max([h["score"] for h in state.hypotheses.values() if h != hyp], default=0)

        status = hypothesis_status(hyp["score"], runner_up_score, hyp.get("has_followup", False))
        wording = confidence_wording(status)

        return {
            "hypothesis_id": top_hyp_id,
            "hypothesis_label": misc["label"],
            "status": status,
            "wording": wording,
            "step_explanation": misc["step"],
            "why_it_matters": misc["why_it_matters"],
            "evidence_trail": self._build_evidence_trail(state),
        }

    def _build_evidence_trail(self, state: EngineState) -> List[Dict[str, Any]]:
        """Build a traceable evidence trail from responses."""
        trail = []
        for r in state.responses:
            item = self.content.get_item_by_id(r["item_id"])
            if not item:
                continue

            option_text = None
            if r["chosen_option_id"]:
                options = item["options"]
                if isinstance(options, str):
                    options = json.loads(options)
                for opt in options:
                    if opt["id"] == r["chosen_option_id"]:
                        option_text = opt["text"]
                        break

            trail.append({
                "question": item.get("prompt", item.get("q", "")),
                "chosen_option": option_text or ("I'm not sure" if r["chosen_option_id"] is None else "unknown"),
                "is_correct": r["is_correct"],
                "misconception_suggested": r["misconception_id"],
                "phase": r["phase"],
                "what_it_suggests": self._interpret_response(r, item) if r["misconception_id"] else None,
            })
        return trail

    def _interpret_response(self, response: Dict, item: Dict) -> Optional[str]:
        """Generate a human-readable interpretation of what a response suggests."""
        misconception_id = response["misconception_id"]
        if not misconception_id or misconception_id == "ARITHMETIC_SLIP":
            return None
        misc = get_misconception(misconception_id)
        return f"Consistent with {misc['label'].lower()}: {misc['description']}"

    def compute_progress(self, state: EngineState) -> Dict[str, Any]:
        """Compute progress metrics after retest."""
        diagnostic_responses = [r for r in state.responses if r["kind"] == "diagnostic"]
        retest_responses = [r for r in state.responses if r["kind"] == "retest"]

        diagnostic_correct = sum(1 for r in diagnostic_responses if r["is_correct"])
        diagnostic_total = len(diagnostic_responses)
        retest_correct = sum(1 for r in retest_responses if r["is_correct"])
        retest_total = len(retest_responses)

        # Determine status
        if retest_total == 0:
            status = "not_assessed"
        elif retest_correct >= 2:
            # Check if this is a second retest (would need session history)
            status = "encouraging_evidence"
        else:
            status = "needs_more_practice"

        return {
            "diagnostic_score": diagnostic_correct,
            "diagnostic_total": diagnostic_total,
            "retest_score": retest_correct,
            "retest_total": retest_total,
            "status": status,
            "improvement": retest_correct - diagnostic_correct if diagnostic_total > 0 else None,
        }