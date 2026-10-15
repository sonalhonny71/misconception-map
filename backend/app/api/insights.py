from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
from uuid import UUID

from app.db.session import get_db
from app.db.models import Learner, Response, ResponseKind, Hypothesis, HypothesisStatus, Progress, SkillStatus, Session as SessionModel, SessionStatus, XPEvent, Achievement, Item
from app.schemas import InsightsOut, InsightHypothesis
from app.api.learners import get_current_learner
from app.engine.misconceptions import get_misconception, confidence_wording
from app.content.loader import get_content_loader

router = APIRouter()


@router.get("/insights", response_model=InsightsOut)
async def get_insights(learner: Learner = Depends(get_current_learner), db: Session = Depends(get_db)):
    """Get insights and hypotheses for the current learner."""
    # Get all hypotheses for this learner
    hypotheses_db = db.query(Hypothesis).filter(Hypothesis.learner_id == learner.id).all()

    hypotheses_out = []
    for h in hypotheses_db:
        misc = get_misconception(h.misconception_id)
        # Build evidence trail
        evidence_trail = _build_evidence_trail(db, learner.id, h.skill, h.misconception_id)

        hypotheses_out.append(InsightHypothesis(
            skill=h.skill,
            misconception_id=h.misconception_id,
            misconception_label=misc["label"],
            status=h.status,
            evidence_score=h.evidence_score / 2.0,  # Convert back from half-points
            evidence_trail=evidence_trail,
            wording=confidence_wording(h.status.value),
            step_explanation=misc["step"],
            why_it_matters=misc["why_it_matters"],
        ))

    # Recent evidence (last 5 responses)
    recent_responses = db.query(Response).filter(Response.learner_id == learner.id).order_by(Response.created_at.desc()).limit(5).all()
    recent_evidence = []
    for r in recent_responses:
        item = db.query(Item).filter(Item.id == r.item_id).first()
        if item:
            option_text = None
            if r.chosen_option_id:
                options = __import__('json').loads(item.options)
                for opt in options:
                    if opt["id"] == r.chosen_option_id:
                        option_text = opt["text"]
                        break

            recent_evidence.append({
                "question": item.prompt,
                "chosen_option": option_text or ("I'm not sure" if r.chosen_option_id is None else "unknown"),
                "is_correct": bool(r.is_correct),
                "misconception_suggested": r.misconception_id,
                "phase": r.kind.value,
                "date": r.created_at.isoformat(),
            })

    return InsightsOut(hypotheses=hypotheses_out, recent_evidence=recent_evidence)


def _build_evidence_trail(db: Session, learner_id: UUID, skill: str, misconception_id: str) -> List[Dict[str, Any]]:
    """Build evidence trail for a specific hypothesis."""
    responses = db.query(Response).filter(
        Response.learner_id == learner_id,
        Response.misconception_id == misconception_id
    ).order_by(Response.created_at).all()

    trail = []
    for r in responses:
        item = db.query(Item).filter(Item.id == r.item_id).first()
        if not item:
            continue

        option_text = None
        if r.chosen_option_id:
            import json
            options = json.loads(item.options)
            for opt in options:
                if opt["id"] == r.chosen_option_id:
                    option_text = opt["text"]
                    break

        trail.append({
            "question": item.prompt,
            "chosen_option": option_text or ("I'm not sure" if r.chosen_option_id is None else "unknown"),
            "is_correct": bool(r.is_correct),
            "phase": r.kind.value,
            "what_it_suggests": f"Consistent with {get_misconception(misconception_id)['label']}: {get_misconception(misconception_id)['description']}" if r.misconception_id else None,
        })
    return trail