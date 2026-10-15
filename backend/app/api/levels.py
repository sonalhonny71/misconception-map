from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from app.db.session import get_db
from app.db.models import Learner, Session as SessionModel, Response, ResponseKind, Progress, SkillStatus
from app.schemas import LevelsOut, LevelSummary
from app.api.learners import get_current_learner

router = APIRouter()


LEVEL_INFO = [
    {"id": 1, "name": "Foundations", "title": "Arithmetic principles & integers", "desc": "Number lines, integer signs, and order of operations."},
    {"id": 2, "name": "Expressions", "title": "Expressions & like terms", "desc": "Substitution, grouping terms, and simplifying expressions."},
    {"id": 3, "name": "Algebra Essentials", "title": "Distributive property & inverses", "desc": "Expand brackets, handle negative multipliers, and use inverse operations."},
    {"id": 4, "name": "Equation Solver", "title": "Multi-step equations", "desc": "Solve equations with negative coefficients and variables on both sides."},
    {"id": 5, "name": "Challenge Lab", "title": "Real-world transfer & inequalities", "desc": "Apply algebra to rates, inequalities, and unfamiliar problems."},
]


SKILL_BY_LEVEL = {
    1: "arithmetic-integers",
    2: "expressions-like-terms",
    3: "distributive-inverse",
    4: "multi-step-equations",
    5: "transfer-inequalities",
}


@router.get("/levels", response_model=LevelsOut)
async def get_levels(learner: Learner = Depends(get_current_learner), db: Session = Depends(get_db)):
    """Get all levels with per-learner status."""
    levels = []

    for level_info in LEVEL_INFO:
        level_id = level_info["id"]
        skill = SKILL_BY_LEVEL[level_id]

        # Get progress for this skill
        progress = db.query(Progress).filter(
            Progress.learner_id == learner.id,
            Progress.skill == skill
        ).first()

        # Check if there's an active session for this level
        active_session = db.query(SessionModel).filter(
            SessionModel.learner_id == learner.id,
            SessionModel.level == level_id,
            SessionModel.status == SessionModel.Status.IN_PROGRESS
        ).first()

        if progress:
            status = progress.status
            last_retest_score = progress.last_retest_score
            last_retest_total = progress.last_retest_total
        else:
            status = SkillStatus.NOT_ASSESSED
            last_retest_score = None
            last_retest_total = None

        # Calculate progress percent based on status
        progress_map = {
            SkillStatus.NOT_ASSESSED: 0,
            SkillStatus.EVIDENCE_OF_DIFFICULTY: 15,
            SkillStatus.PRACTICING: 35,
            SkillStatus.ENCOURAGING_EVIDENCE: 70,
            SkillStatus.CONSISTENT_EVIDENCE: 100,
            SkillStatus.NEEDS_MORE_PRACTICE: 25,
        }
        progress_percent = progress_map.get(status, 0)

        levels.append(LevelSummary(
            id=level_id,
            name=level_info["name"],
            title=level_info["title"],
            description=level_info["desc"],
            status=status,
            progress_percent=progress_percent,
            last_retest_score=last_retest_score,
            last_retest_total=last_retest_total,
        ))

    return LevelsOut(levels=levels)